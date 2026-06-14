param(
    [Parameter(Mandatory = $true)]
    [string]$Wav,
    [string]$OutDir = "",
    [string]$ContainerName = "",
    [string]$Language = "zh",
    [string]$PlatformRoot = ""
)

# Slice + FunASR inside engine container (needs ffmpeg-python, funasr, numpy — not platform venv)
$ErrorActionPreference = "Stop"
$RepoRoot = if ($PlatformRoot) { (Resolve-Path $PlatformRoot).Path } else { Split-Path $PSScriptRoot -Parent }
$Mount = "/workspace/GPT"
$EngineInDocker = "/workspace/GPT-SoVITS"

function Import-DotEnv([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        $k, $v = $_ -split '=', 2
        if ($k) { Set-Item -Path "Env:$($k.Trim())" -Value $v.Trim().Trim('"') }
    }
}

Import-DotEnv (Join-Path $RepoRoot ".env")

function Get-RunningEngineContainer([string]$Preferred = "") {
    $byPort = docker ps --filter "publish=9874" --format "{{.Names}}" 2>$null | Select-Object -First 1
    if ($byPort) {
        return $byPort.ToString().Trim()
    }
    if ($Preferred) {
        $byName = docker ps --filter "name=^/$([regex]::Escape($Preferred))$" --format "{{.Names}}" 2>$null |
            Select-Object -First 1
        if ($byName) {
            return $byName.ToString().Trim()
        }
        Write-Warning "ENGINE_TRAIN_DOCKER=$Preferred is not running (stale .env). Start the engine container."
    }
    return $null
}

if (-not $ContainerName) {
    $ContainerName = Get-RunningEngineContainer -Preferred $env:ENGINE_TRAIN_DOCKER
}
else {
    $ContainerName = Get-RunningEngineContainer -Preferred $ContainerName
}
if (-not $ContainerName) {
    Write-Error @"
Engine container not running.

  1. Start engine (keep terminal open): .\scripts\engine_run_with_platform_mount.ps1
  2. Update .env: .\scripts\engine_print_env.ps1
  3. Re-run: .\scripts\prepare_train_dataset.ps1 -Wav `"$Wav`"
"@
}

$wavResolved = (Resolve-Path $Wav).Path
if (-not $OutDir) {
    $OutDir = Join-Path $RepoRoot "data\train_dataset_test"
}
$outResolved = $OutDir
if (-not (Test-Path $outResolved)) {
    New-Item -ItemType Directory -Force -Path $outResolved | Out-Null
}
$outResolved = (Resolve-Path $outResolved).Path

function Get-ContainerPath([string]$HostPath, [string]$Root, [string]$ContainerPrefix) {
    $h = (Resolve-Path $HostPath).Path.TrimEnd('\')
    $r = (Resolve-Path $Root).Path.TrimEnd('\')
    if ($h.Length -lt $r.Length) { return $null }
    if ($h.Substring(0, $r.Length).ToLower() -ne $r.ToLower()) { return $null }
    $rel = $h.Substring($r.Length).TrimStart('\', '/')
    return "$ContainerPrefix/$($rel -replace '\\', '/')"
}

$wavInContainer = Get-ContainerPath $wavResolved $RepoRoot $Mount
if (-not $wavInContainer) {
    $staging = Join-Path $RepoRoot "data\staging"
    New-Item -ItemType Directory -Force -Path $staging | Out-Null
    $staged = Join-Path $staging (Split-Path $wavResolved -Leaf)
    Write-Host "Wav outside platform mount - copying to $staged"
    Copy-Item -Force $wavResolved $staged
    $wavResolved = $staged
    $wavInContainer = Get-ContainerPath $wavResolved $RepoRoot $Mount
}

$outInContainer = Get-ContainerPath $outResolved $RepoRoot $Mount
if (-not $outInContainer) {
    Write-Error "OutDir must be under $RepoRoot (container mount $Mount). Got: $outResolved"
}

Write-Host "Container: $ContainerName"
Write-Host "Wav:       $wavInContainer"
Write-Host "Out:       $outInContainer"
Write-Host ""

$cmd = @(
    "python /workspace/GPT/infra/engine/scripts/prepare_train_dataset.py",
    "--engine-root $EngineInDocker",
    "--wav `"$wavInContainer`"",
    "--out-dir `"$outInContainer`"",
    "--language $Language"
) -join " "

docker exec $ContainerName bash -lc $cmd
if ($LASTEXITCODE -ne 0) {
    Write-Error "prepare_train_dataset failed (exit $LASTEXITCODE)"
}

Write-Host ""
Write-Host "Done. Check:"
Write-Host "  $outResolved\train.list"
Write-Host "  $outResolved\segments\"
