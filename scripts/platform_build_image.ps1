param(
    [string]$Tag = "",
    [string]$ImageName = "voice-platform"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeDir = Join-Path $RepoRoot ".runtime"
$ManifestPath = Join-Path $RuntimeDir "releases.json"

if (-not $Tag) {
    $Tag = Get-Date -Format "yyyyMMdd-HHmmss"
}

$fullImage = "${ImageName}:${Tag}"

Write-Host "Building $fullImage ..."
docker build -t $fullImage -t "${ImageName}:latest" -f (Join-Path $RepoRoot "infra\docker\Dockerfile.platform") $RepoRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
$entry = [ordered]@{
    tag        = $Tag
    image      = $fullImage
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    git_commit = (git -C $RepoRoot rev-parse --short HEAD 2>$null)
}

$releases = @()
if (Test-Path $ManifestPath) {
    try {
        $releases = @(Get-Content $ManifestPath -Raw | ConvertFrom-Json)
    } catch {
        $releases = @()
    }
}
$releases = @($entry) + @($releases | Select-Object -First 9)

@{ releases = $releases } | ConvertTo-Json -Depth 4 | Set-Content -Path $ManifestPath -Encoding UTF8

Write-Host "OK: $fullImage"
Write-Host "Manifest: $ManifestPath"
Write-Host ""
Write-Host "Release:"
Write-Host "  .\scripts\platform_release.ps1 -Tag $Tag"
