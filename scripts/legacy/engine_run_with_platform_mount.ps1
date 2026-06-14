param(
    [string]$PlatformRoot = "C:\Users\panta\Desktop\GPT",
    [string]$SovitsRoot = "C:\Users\panta\Desktop\GPT-SOVITS\GPT-SoVITS",
    [string]$Service = "GPT-SoVITS-CU128-Lite",
    [switch]$Force
)

# Start engine container with platform repo mounted at /workspace/GPT (Option B)
$ErrorActionPreference = "Stop"

$PlatformRoot = (Resolve-Path $PlatformRoot).Path
$SovitsRoot = (Resolve-Path $SovitsRoot).Path
$MountFile = Join-Path $PlatformRoot "infra\engine\docker-compose.platform-mount.yaml"

if (-not (Test-Path $MountFile)) {
    Write-Error "Missing $MountFile"
}
if (-not (Test-Path (Join-Path $SovitsRoot "docker-compose.yaml"))) {
    Write-Error "Upstream compose not found: $SovitsRoot"
}

$platformMount = ($PlatformRoot -replace '\\', '/')
$env:PLATFORM_MOUNT = $platformMount

$existing = docker ps --filter "publish=9874" --format "{{.Names}}" | Select-Object -First 1
if ($existing -and -not $Force) {
    Write-Host "Engine container ALREADY RUNNING: $existing"
    Write-Host "Do NOT start a second compose run (port 9874 conflict)."
    Write-Host ""
    Write-Host "  docker exec -it $existing bash"
    Write-Host "  .\scripts\engine_api_v2.ps1 -Action status"
    Write-Host "  .\scripts\engine_docker_cleanup.ps1 -StopStale"
    Write-Host ""
    Write-Error "Aborting. Pass -Force only after: docker stop $existing"
    exit 1
}

Write-Host "ENGINE_ROOT (in container): /workspace/GPT-SoVITS"
Write-Host "PLATFORM_MOUNT (in container): /workspace/GPT"
Write-Host "Service: $Service"
Write-Host ""
Write-Host "Starting container... (Ctrl+C to detach; open another terminal for spike)"
Write-Host ""

Push-Location $SovitsRoot
try {
    docker compose `
        -f docker-compose.yaml `
        -f $MountFile `
        run --service-ports --remove-orphans $Service
}
finally {
    Pop-Location
}
