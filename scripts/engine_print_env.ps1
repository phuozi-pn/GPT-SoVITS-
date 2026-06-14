# Print .env lines for real engine train/infer (copy into repo root .env)
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$SovitsRoot = "C:\Users\panta\Desktop\GPT-SOVITS\GPT-SoVITS"

$cn = docker ps --filter "publish=9874" --format "{{.Names}}" | Select-Object -First 1
if (-not $cn) {
    Write-Host "# Engine container NOT running. Start first:"
    Write-Host "#   .\scripts\engine_run_with_platform_mount.ps1"
    Write-Host ""
}

Write-Host "# --- paste into .env (repo root) ---"
Write-Host "TRAIN_MOCK=false"
Write-Host "ENGINE_MOCK=false"
Write-Host "ENGINE_TTS_URL=http://127.0.0.1:9880"
Write-Host "ENGINE_TRAIN_ROOT=$($SovitsRoot -replace '\\','/')"
if ($cn) {
    Write-Host "ENGINE_TRAIN_DOCKER=$cn"
} else {
    Write-Host "ENGINE_TRAIN_DOCKER=<container-name>"
}
Write-Host "ENGINE_TRAIN_ROOT_IN_DOCKER=/workspace/GPT-SoVITS"
Write-Host "ENGINE_TRAIN_PLATFORM_MOUNT=/workspace/GPT"
Write-Host "# -----------------------------------"
