param(
    [string]$Tag = "",
    [string]$ImageName = "voice-platform"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ManifestPath = Join-Path $RepoRoot ".runtime\releases.json"
$ComposeDir = Join-Path $RepoRoot "infra\docker"
$ReleaseEnv = Join-Path $ComposeDir ".env.release"

if (-not $Tag) {
    if (-not (Test-Path $ManifestPath)) {
        Write-Error "No releases.json — run .\scripts\platform_build_image.ps1 first"
    }
    $manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
    $Tag = $manifest.releases[0].tag
}

$fullImage = "${ImageName}:${Tag}"
Write-Host "Deploying $fullImage ..."

@"
PLATFORM_IMAGE=$fullImage
PLATFORM_IMAGE_TAG=$Tag
API_PORT=8001
"@ | Set-Content -Path $ReleaseEnv -Encoding UTF8

Push-Location $ComposeDir
try {
    docker compose -f docker-compose.dev.yml -f docker-compose.platform.yml --env-file .env.release up -d api infer-worker train-worker batch-worker
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

Write-Host "Deployed $fullImage (PLATFORM_RELEASE_VERSION=$Tag)"
