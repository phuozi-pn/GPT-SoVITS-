# Stop platform API + workers started by platform_start.ps1
$ErrorActionPreference = "SilentlyContinue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PidFile = Join-Path $RepoRoot ".runtime\platform.json"

if (-not (Test-Path $PidFile)) {
    Write-Host "No .runtime\platform.json — nothing to stop."
    exit 0
}

$saved = Get-Content $PidFile -Raw | ConvertFrom-Json
foreach ($name in @("api", "train", "infer", "batch")) {
    $id = $saved.$name
    if ($id) {
        Stop-Process -Id $id -Force
        Write-Host "Stopped $name (PID $id)"
    }
}
Remove-Item $PidFile -Force
Write-Host "Done."
