# 释放本地磁盘：删除可再生的依赖/缓存（不删源码与 .env）
# 用法:
#   .\scripts\clean_local_workspace.ps1           # 安全模式（保留 data/storage 用户素材）
#   .\scripts\clean_local_workspace.ps1 -Deep     # 额外删除 data/storage（约数 GB，慎用）
param(
    [switch]$Deep,
    [switch]$StopPlatform
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

function Remove-DirIfExists([string]$Rel) {
    $p = Join-Path $Root $Rel
    if (-not (Test-Path -LiteralPath $p)) { return 0 }
    $mb = [math]::Round((Get-ChildItem $p -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB, 1)
    Remove-Item -LiteralPath $p -Recurse -Force -EA SilentlyContinue
    Write-Host "removed $Rel (${mb} MB)"
    return $mb
}

if ($StopPlatform) {
    & (Join-Path $Root "scripts\platform_stop.ps1") | Out-Null
}

$freed = 0.0
foreach ($d in @(
    "apps\web\node_modules",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    "data\temp",
    "data\e2e_out"
)) {
    $freed += Remove-DirIfExists $d
}

Get-ChildItem $Root -Recurse -Directory -Filter "__pycache__" -EA SilentlyContinue |
    ForEach-Object {
        $mb = [math]::Round((Get-ChildItem $_.FullName -Recurse -File -EA SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB, 1)
        Remove-Item $_.FullName -Recurse -Force -EA SilentlyContinue
        $freed += $mb
    }

$logDir = Join-Path $Root ".runtime\logs"
if (Test-Path $logDir) {
    Get-ChildItem $logDir -File -EA SilentlyContinue | Remove-Item -Force -EA SilentlyContinue
    Write-Host "cleared .runtime\logs"
}

if ($Deep) {
    $freed += Remove-DirIfExists "data\storage"
    $freed += Remove-DirIfExists "data\train_raw"
}

Write-Host ""
Write-Host "Done. Approx freed: ${freed} MB"
Write-Host "Code is on GitHub; restore dev env with:"
Write-Host "  python -m venv .venv; .\.venv\Scripts\pip install -e .[dev,asr]"
Write-Host "  cd apps\web; npm ci"
