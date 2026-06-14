param(
    [int]$Port = 0,
    [switch]$Background,
    [switch]$SkipDocker,
    [switch]$NoEngineApi
)

# Start platform API + Train/Infer workers (one command).
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$RuntimeDir = Join-Path $RepoRoot ".runtime"
$PidFile = Join-Path $RuntimeDir "platform.json"
$LogDir = Join-Path $RuntimeDir "logs"

if (-not (Test-Path $Python)) {
    Write-Error "Missing venv: $Python — run: python -m venv .venv; pip install -e ."
}

function Import-DotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $idx = $line.IndexOf("=")
        if ($idx -lt 1) { return }
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim()
        Set-Item -Path "env:$key" -Value $val
    }
}

function Get-ApiPortFromEnv {
    if ($env:STORAGE_PUBLIC_BASE_URL -match ':(\d+)/') {
        return [int]$Matches[1]
    }
    return 8001
}

function Stop-ExistingPlatform {
    if (-not (Test-Path $PidFile)) { return }
    try {
        $saved = Get-Content $PidFile -Raw | ConvertFrom-Json
        foreach ($name in @("api", "train", "infer", "batch")) {
            $id = $saved.$name
            if ($id) {
                Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
            }
        }
    } catch { }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

Import-DotEnv (Join-Path $RepoRoot ".env")
if ($Port -le 0) { $Port = Get-ApiPortFromEnv }

if (-not $SkipDocker) {
    $composeDir = Join-Path $RepoRoot "infra\docker"
    Write-Host "Starting PostgreSQL + Redis..."
    Push-Location $composeDir
    try {
        docker compose -f docker-compose.dev.yml up -d 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Docker compose failed. Start Docker Desktop, then run platform_start.ps1 again."
        }
    } catch {
        Write-Warning "Docker not available. Start Docker Desktop before platform_start.ps1"
    } finally {
        Pop-Location
    }
}

Stop-ExistingPlatform
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
if ($Background) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

$env:API_BASE = "http://127.0.0.1:$Port"

function Start-PlatformProcess {
    param(
        [string]$Name,
        [string[]]$PythonArgs,
        [string]$Title
    )
    if ($Background) {
        $out = Join-Path $LogDir "$Name.log"
        $err = Join-Path $LogDir "$Name.err.log"
        $p = Start-Process -FilePath $Python -ArgumentList $PythonArgs `
            -WorkingDirectory $RepoRoot `
            -RedirectStandardOutput $out -RedirectStandardError $err `
            -PassThru -WindowStyle Hidden
        Write-Host "  $Title -> log: .runtime\logs\$Name.log"
        return $p.Id
    }
    $p = Start-Process -FilePath $Python -ArgumentList $PythonArgs `
        -WorkingDirectory $RepoRoot -PassThru
    Write-Host "  $Title -> console window (PID $($p.Id))"
    return $p.Id
}

Write-Host ""
Write-Host "Platform starting on port $Port ..."
Write-Host ""

$apiPid = Start-PlatformProcess -Name "api" -Title "GPT Platform API :$Port" -PythonArgs @(
    "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", "$Port"
)
Start-Sleep -Seconds 2
try {
    $health = Invoke-WebRequest "http://127.0.0.1:$Port/health" -TimeoutSec 5 -UseBasicParsing
    if ($health.StatusCode -ne 200) {
        Write-Warning "API health check failed (HTTP $($health.StatusCode)). See .runtime\logs\api.err.log"
    }
} catch {
    Write-Warning "API not responding on port $Port. Is Docker running? Check .runtime\logs\api.err.log"
}

$trainPid = Start-PlatformProcess -Name "train" -Title "GPT Train Worker" -PythonArgs @(
    "-m", "workers.train.runner"
)
$inferPid = Start-PlatformProcess -Name "infer" -Title "GPT Infer Worker" -PythonArgs @(
    "-m", "workers.infer.runner"
)
$batchPid = Start-PlatformProcess -Name "batch" -Title "GPT Batch Worker" -PythonArgs @(
    "-m", "workers.batch.runner"
)

@{
    api   = $apiPid
    train = $trainPid
    infer = $inferPid
    batch = $batchPid
    port  = $Port
    started_at = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content $PidFile -Encoding UTF8

if (-not $NoEngineApi) {
    $engineScript = Join-Path $RepoRoot "scripts\engine_api_v2.ps1"
    if (Test-Path $engineScript) {
        try {
            $status = & $engineScript -Action status 2>&1 | Out-String
            if ($status -match "HTTP.*docs -> OK") {
                Write-Host "Engine api_v2 already up (9880)"
            } else {
                Write-Host "Starting engine api_v2 (9880)..."
                & $engineScript -Action start | Out-Null
            }
        } catch {
            Write-Host "Engine api_v2 skip (start engine container first?)"
        }
    }
}

Write-Host ""
Write-Host "Ready:"
Write-Host "  Health   http://127.0.0.1:$Port/health"
Write-Host "  OpenAPI  http://127.0.0.1:$Port/api/v1/docs"
Write-Host "  Web UI   http://127.0.0.1:5173  (run .\scripts\web_dev.ps1 in another terminal)"
Write-Host "  Stop     .\scripts\platform_stop.ps1"
if ($Background) {
    Write-Host "  Logs     Get-Content .runtime\logs\api.log -Wait"
}
Write-Host ""
