# Start Vue dev server (proxy API on port from .env, default 8001).
param(
    [int]$ApiPort = 0
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$WebDir = Join-Path $RepoRoot "apps\web"

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

Import-DotEnv (Join-Path $RepoRoot ".env")
if ($ApiPort -le 0) {
    if ($env:STORAGE_PUBLIC_BASE_URL -match ':(\d+)/') {
        $ApiPort = [int]$Matches[1]
    } else {
        $ApiPort = 8001
    }
}

$healthUrl = "http://127.0.0.1:$ApiPort/health"
try {
    $r = Invoke-WebRequest $healthUrl -TimeoutSec 3 -UseBasicParsing
    if ($r.StatusCode -ne 200) {
        Write-Warning "API returned HTTP $($r.StatusCode). Start platform first: .\scripts\platform_start.ps1"
    }
} catch {
    Write-Host ""
    Write-Error @"
API is not reachable at $healthUrl

Fix:
  1. Start Docker Desktop (PostgreSQL + Redis)
  2. cd $RepoRoot
  3. .\scripts\platform_stop.ps1
  4. .\scripts\platform_start.ps1
  5. Then run web_dev.ps1 again
"@
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm not found. Install Node.js 20+ or use WSL."
}

Push-Location $WebDir
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing web dependencies (first run)..."
        npm install
    }
    Write-Host ""
    Write-Host "Web dev server: http://127.0.0.1:5173"
    Write-Host "API proxy target: http://127.0.0.1:$ApiPort"
    Write-Host "Ensure platform is running: .\scripts\platform_start.ps1"
    Write-Host ""
    npm run dev
} finally {
    Pop-Location
}
