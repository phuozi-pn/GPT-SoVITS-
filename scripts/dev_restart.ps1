param(
    [switch]$SkipEngine,
    [switch]$Background
)

# Full local dev restart: stop platform -> PG/Redis -> platform -> api_v2
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

Write-Host "========== 1/4 Stop platform =========="
& (Join-Path $PSScriptRoot "platform_stop.ps1")

Write-Host ""
Write-Host "========== 2/4 Free API port =========="
$envFile = Join-Path $RepoRoot ".env"
$port = 8001
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^STORAGE_PUBLIC_BASE_URL=http://[^:]+:(\d+)/') {
            $port = [int]$Matches[1]
            break
        }
    }
}
Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "  Freed port $port (PID $($_.OwningProcess))"
    }

Write-Host ""
Write-Host "========== 3/4 Docker PG + Redis =========="
Push-Location (Join-Path $RepoRoot "infra\docker")
docker compose -f docker-compose.dev.yml up -d
Pop-Location
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========== 4/4 Start platform =========="
$startParams = @{}
if ($Background) { $startParams.Background = $true }
if ($SkipEngine) { $startParams.NoEngineApi = $true }
& (Join-Path $PSScriptRoot "platform_start.ps1") @startParams

Write-Host ""
Write-Host "========== Engine (9880 synth only) =========="
Write-Host "  Start upstream GPT-SoVITS Docker, then:"
Write-Host "  .\scripts\engine_api_v2.ps1 -Action start"

Write-Host ""
Write-Host "========== Wait for API =========="
$deadline = (Get-Date).AddSeconds(20)
$apiOk = $false
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest "http://127.0.0.1:$port/health" -TimeoutSec 2 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $apiOk = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if ($apiOk) {
    Write-Host "  API health OK -> http://127.0.0.1:$port/health"
} else {
    Write-Host "  API not ready — try: Get-Content .runtime\logs\api.err.log -Tail 30"
    Write-Host "  Or: .\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port $port"
}

Write-Host ""
Write-Host "========== Status =========="
& (Join-Path $PSScriptRoot "platform_status.ps1") 2>$null

Write-Host ""
Write-Host "Next:"
Write-Host "  Cloud train: docs\architecture\2026-06-10-云端GPU训练指南.md"
Write-Host "  Local synth: .\scripts\engine_api_v2.ps1 -Action status"
