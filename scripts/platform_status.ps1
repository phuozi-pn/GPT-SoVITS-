# Quick health check for local platform stack
$ErrorActionPreference = "SilentlyContinue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PidFile = Join-Path $RepoRoot ".runtime\platform.json"

function Get-ApiPort {
    $envFile = Join-Path $RepoRoot ".env"
    if (Test-Path $envFile) {
        foreach ($line in Get-Content $envFile) {
            if ($line -match '^STORAGE_PUBLIC_BASE_URL=http://[^:]+:(\d+)/') {
                return [int]$Matches[1]
            }
        }
    }
    return 8001
}

$port = Get-ApiPort
Write-Host "=== Platform ==="
if (Test-Path $PidFile) {
    $p = Get-Content $PidFile -Raw | ConvertFrom-Json
        foreach ($name in @("api", "train", "infer", "batch")) {
        $id = $p.$name
        $alive = $false
        if ($id) { $alive = $null -ne (Get-Process -Id $id -ErrorAction SilentlyContinue) }
        $pidStr = if ($id) { "$id" } else { "-" }
        $state = if ($alive) { "running" } else { "stopped" }
        Write-Host ("  {0,-6} PID {1,-8} {2}" -f $name, $pidStr, $state)
    }
} else {
    Write-Host "  (not started — run platform_start.ps1)"
}

try {
    $r = Invoke-WebRequest "http://127.0.0.1:$port/health" -TimeoutSec 3 -UseBasicParsing
    Write-Host "  API    http://127.0.0.1:$port/health -> $($r.StatusCode)"
} catch {
    Write-Host "  API    http://127.0.0.1:$port/health -> down"
}

Write-Host ""
Write-Host "=== Docker (PG + Redis) ==="
docker ps --filter "name=gpt-platform" --format "  {{.Names}}  {{.Status}}" 2>$null

Write-Host ""
Write-Host "=== Engine ==="
& (Join-Path $RepoRoot "scripts\engine_api_v2.ps1") -Action status 2>&1
