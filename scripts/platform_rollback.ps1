param(
    [int]$StepsBack = 1,
    [string]$ImageName = "voice-platform"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ManifestPath = Join-Path $RepoRoot ".runtime\releases.json"

if (-not (Test-Path $ManifestPath)) {
    Write-Error "No releases.json — nothing to roll back to"
}

$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$releases = @($manifest.releases)
if ($releases.Count -le $StepsBack) {
    Write-Error "Only $($releases.Count) release(s) recorded; cannot roll back $StepsBack step(s)"
}

$target = $releases[$StepsBack]
$tag = $target.tag
Write-Host "Rolling back to $tag ($($target.image)) ..."

& (Join-Path $PSScriptRoot "platform_release.ps1") -Tag $tag -ImageName $ImageName
Write-Host "Rollback complete."
