param(
    [switch]$StopAll,
    [switch]$StopStale
)

# List GPT-SoVITS engine containers; optional stop duplicates / stale run containers.
$ErrorActionPreference = "Stop"

$rows = docker ps -a --filter "ancestor=xxxxrt666/gpt-sovits:latest-cu128-lite" --format "{{.ID}}`t{{.Names}}`t{{.Status}}`t{{.Ports}}"
if (-not $rows) {
    $rows = docker ps -a --format "{{.ID}}`t{{.Names}}`t{{.Status}}`t{{.Ports}}" | Where-Object { $_ -match "gpt-sovits|GPT-SoVITS" }
}

Write-Host "GPT-SoVITS engine containers:"
Write-Host ""
if (-not $rows) {
    Write-Host "  (none found)"
    exit 0
}

$active = docker ps --filter "publish=9874" --format "{{.Names}}" | Select-Object -First 1
foreach ($line in $rows) {
    $parts = $line -split "`t", 4
    $mark = if ($parts[1] -eq $active) { " <- ACTIVE (ports 9874/9880)" } else { "" }
    Write-Host "$($parts[1])  $($parts[2])$mark"
    Write-Host "  $($parts[3])"
    Write-Host ""
}

Write-Host "Rules:"
Write-Host "  - Only ONE engine container should publish 9874/9880."
Write-Host "  - docker compose run creates a NEW container each time; stop old ones first."
Write-Host "  - api_v2 'address already in use' = process already running INSIDE the active container."
Write-Host ""

if ($active) {
    Write-Host "Reuse active container:  docker exec -it $active bash"
    Write-Host "Start api_v2 safely:       .\scripts\engine_api_v2.ps1 -Action start"
} else {
    Write-Host "No RUNNING engine container (nothing on port 9874)."
    Write-Host "Start a new one:"
    Write-Host "  cd C:\Users\panta\Desktop\GPT"
    Write-Host "  .\scripts\engine_run_with_platform_mount.ps1"
    Write-Host "Then in another terminal:"
    Write-Host "  .\scripts\engine_api_v2.ps1 -Action start"
    Write-Host "  .\scripts\engine_api_v2.ps1 -Action synthesize"
}
Write-Host ""

if ($StopAll) {
    foreach ($line in $rows) {
        $id = ($line -split "`t")[0]
        docker stop $id | Out-Null
        Write-Host "Stopped $id"
    }
    exit 0
}

if ($StopStale) {
    foreach ($line in $rows) {
        $parts = $line -split "`t", 4
        if ($parts[1] -ne $active -and $parts[2] -match "^Up") {
            docker stop $parts[0] | Out-Null
            Write-Host "Stopped stale: $($parts[1])"
        }
    }
}
