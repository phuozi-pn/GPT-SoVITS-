param(
    [Parameter(Mandatory = $true)]
    [string]$Url,
    [string]$OutDir = "",
    [string]$CookiesFile = "",
    [int]$ClipSeconds = 10
)

# Download Bilibili audio to WAV for local TTS tests.
# Bilibili often blocks yt-dlp without cookies (HTTP 412). Export cookies.txt from browser first.
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path $PSScriptRoot -Parent
if (-not $OutDir) {
    $OutDir = Join-Path $RepoRoot "infra\engine\samples"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

python -m pip install -q yt-dlp 2>$null | Out-Null

$outTemplate = Join-Path $OutDir "bilibili_%(id)s.%(ext)s"
$ytArgs = @("-x", "--audio-format", "wav", "-o", $outTemplate, $Url)
if ($CookiesFile) {
    if (-not (Test-Path -LiteralPath $CookiesFile)) {
        Write-Error "Cookies file not found: $CookiesFile"
    }
    $ytArgs = @("--cookies", $CookiesFile) + $ytArgs
}

Write-Host "Downloading audio..."
python -m yt_dlp @ytArgs

$wav = Get-ChildItem -Path $OutDir -Filter "bilibili_*.wav" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $wav) {
    Write-Host ""
    Write-Host "Download failed (common: Bilibili HTTP 412)."
    Write-Host "1. Install browser extension: Get cookies.txt LOCALLY"
    Write-Host "2. Open the Bilibili video while logged in, export cookies to e.g. cookies.txt"
    Write-Host "3. Re-run:"
    Write-Host "   .\scripts\download_bilibili_audio.ps1 -Url '$Url' -CookiesFile .\cookies.txt"
    exit 1
}

if ($ClipSeconds -gt 0) {
    $clipPath = Join-Path $OutDir ($wav.BaseName + "_clip${ClipSeconds}s.wav")
    if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
        ffmpeg -y -i $wav.FullName -t $ClipSeconds -ac 1 -ar 32000 $clipPath 2>$null
        Write-Host "Full: $($wav.FullName)"
        Write-Host "Clip (${ClipSeconds}s, for TTS ref): $clipPath"
    } else {
        Write-Host "Saved (install ffmpeg to auto-clip): $($wav.FullName)"
    }
} else {
    Write-Host "Saved: $($wav.FullName)"
}
