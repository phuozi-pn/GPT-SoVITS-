param(
    [ValidateSet("status", "start", "stop", "synthesize")]
    [string]$Action = "status",
    [string]$ContainerName = "",
    [string]$OutFile = "",
    [string]$PromptFile = "",
    [string]$TargetFile = "",
    [string]$RefHostPath = "",
    [string]$RefInContainer = "/workspace/GPT-SoVITS/samples/ref_zh_zero_shot.wav",
    [string]$GptWeights = "GPT_weights_v2Pro/platform_manualspike001-e4.ckpt",
    [string]$SovitsWeights = "SoVITS_weights_v2Pro/platform_manualspike001_e4_s100.pth"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "engine_sync_env.ps1")

function Import-DotEnv {
    param([string]$Path)
    Import-DotEnvFile $Path
}

Import-DotEnv (Join-Path $RepoRoot ".env")

if (-not $ContainerName -and $env:ENGINE_TRAIN_DOCKER) {
    $ContainerName = $env:ENGINE_TRAIN_DOCKER
}

if (-not $OutFile) {
    $OutFile = Join-Path $RepoRoot "finetuned_spike.wav"
}
if (-not $PromptFile) {
    $PromptFile = Join-Path $RepoRoot "infra\engine\samples\spike_tts_prompt.txt"
}
if (-not $TargetFile) {
    $TargetFile = Join-Path $RepoRoot "infra\engine\samples\spike_tts_target.txt"
}

function Get-EngineContainer {
    param(
        [string]$Name,
        [switch]$Required
    )

    $running = Find-RunningEngineContainer -PreferredName $Name
    if ($running) {
        return $running
    }

    if ($Required) {
        $hint = @"
No running GPT-SoVITS Docker container found.

1) Start engine (new terminal, keep it open):
   cd C:\Users\panta\Desktop\GPT-SOVITS\GPT-SoVITS
   docker compose run --service-ports --remove-orphans GPT-SoVITS-CU128-Lite

2) Sync .env automatically:
   cd C:\Users\panta\Desktop\GPT
   .\scripts\engine_sync_env.ps1

3) Start api_v2:
   .\scripts\engine_api_v2.ps1 -Action start
"@
        if ($Name) {
            Write-Error "Container '$Name' is not running (stale .env?).`n$hint"
        } else {
            Write-Error $hint
        }
    }
    return $null
}

function Get-Cn {
    param([switch]$Required)
    if (-not $script:EngineCn) {
        $script:EngineCn = Get-EngineContainer -Name $ContainerName -Required:$Required
    }
    return $script:EngineCn
}

$base = "http://127.0.0.1:9880"

function Test-ApiV2Up {
    try {
        $r = Invoke-WebRequest -Uri "$base/docs" -TimeoutSec 5 -UseBasicParsing
        return $r.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Get-ApiV2Process {
    $cn = Get-Cn
    if (-not $cn) { return "" }
    $out = docker exec $cn bash -lc "pgrep -af 'api_v2.py' 2>/dev/null || true" 2>&1
    $text = ConvertTo-SingleLine $out
    if ($text -match "No such container|Error response from daemon") {
        return ""
    }
    return $text
}

function Write-StaleEnvWarning {
    if (-not $env:ENGINE_TRAIN_DOCKER) { return }
    if (Test-ContainerRunning $env:ENGINE_TRAIN_DOCKER) { return }
    Write-Host ""
    Write-Host "WARN: .env ENGINE_TRAIN_DOCKER is stale:" -ForegroundColor Yellow
    Write-Host "      $($env:ENGINE_TRAIN_DOCKER)"
    Write-Host "      Fix: .\scripts\engine_sync_env.ps1"
}

function Read-Utf8Text {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        Write-Error "Missing text file: $Path"
    }
    return (Get-Content -LiteralPath $Path -Raw -Encoding UTF8).Trim()
}

switch ($Action) {
    "status" {
        Write-StaleEnvWarning
        $cn = Get-Cn
        if (-not $cn) {
            Write-Host "Container: (not running)"
            Write-Host "  1. cd C:\Users\panta\Desktop\GPT-SOVITS\GPT-SoVITS"
            Write-Host "     docker compose run --service-ports --remove-orphans GPT-SoVITS-CU128-Lite"
            Write-Host "  2. .\scripts\engine_sync_env.ps1"
            Write-Host "  3. .\scripts\engine_api_v2.ps1 -Action start"
        } else {
            Write-Host "Container: $cn"
            if ($env:ENGINE_TRAIN_DOCKER -and $env:ENGINE_TRAIN_DOCKER -ne $cn) {
                Write-Host "  (.env stale — run .\scripts\engine_sync_env.ps1)"
            }
            Write-Host "api_v2 process:"
            $proc = Get-ApiV2Process
            if ($proc -and $proc -match "api_v2\.py") { Write-Host "  $proc" } else { Write-Host "  (not running)" }
        }
        if (Test-ApiV2Up) {
            Write-Host "HTTP $base/docs -> OK"
        } else {
            Write-Host "HTTP $base/docs -> down (start: .\scripts\engine_api_v2.ps1 -Action start)"
        }
    }
    "start" {
        try {
            Sync-EngineEnv -Quiet -EnvPath (Join-Path $RepoRoot ".env") | Out-Null
        } catch {
            Write-Error $_.Exception.Message
        }
        $script:EngineCn = $null
        Import-DotEnv (Join-Path $RepoRoot ".env")
        $ContainerName = $env:ENGINE_TRAIN_DOCKER

        $cn = Get-Cn -Required
        if (Test-ApiV2Up) {
            Write-Host "api_v2 already responding on $base - no second instance started."
            $proc = Get-ApiV2Process
            if ($proc -match "api_v2\.py") { Write-Host "  $proc" }
            exit 0
        }
        Write-Host "Starting api_v2 in $cn (first load ~1-2 min)..."
        docker exec -d $cn bash -lc "cd /workspace/GPT-SoVITS && pip install -q 'starlette<1.0.0' 2>/dev/null; exec python api_v2.py -a 0.0.0.0 -p 9880 -c GPT_SoVITS/configs/tts_infer_v2pro.yaml"
        $deadline = (Get-Date).AddMinutes(3)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 5
            if (Test-ApiV2Up) {
                Write-Host "Ready: $base/docs"
                exit 0
            }
            Write-Host "  waiting..."
        }
        Write-Error "api_v2 did not become ready within 3 minutes. Check: docker exec -it $cn bash -lc 'pgrep -af api_v2'"
    }
    "stop" {
        $cn = Get-Cn -Required
        docker exec $cn bash -lc "pkill -f 'api_v2.py' 2>/dev/null || true"
        Start-Sleep -Seconds 2
        Write-Host "Stopped api_v2 in $cn"
    }
    "synthesize" {
        if (-not (Test-ApiV2Up)) {
            Write-Host "api_v2 not up - starting..."
            & $PSCommandPath -Action start -ContainerName $ContainerName
        }
        $cn = Get-Cn -Required
        if ($RefHostPath) {
            if (-not (Test-Path -LiteralPath $RefHostPath)) {
                Write-Error "RefHostPath not found: $RefHostPath"
            }
            docker exec $cn bash -lc "mkdir -p /workspace/GPT-SoVITS/samples"
            docker cp $RefHostPath "${cn}:${RefInContainer}"
            Write-Host "Copied ref audio -> $RefInContainer"
        }
        (Invoke-WebRequest "$base/set_gpt_weights?weights_path=$GptWeights" -TimeoutSec 300 -UseBasicParsing).Content
        (Invoke-WebRequest "$base/set_sovits_weights?weights_path=$SovitsWeights" -TimeoutSec 300 -UseBasicParsing).Content
        $ref = [uri]::EscapeDataString($RefInContainer)
        $prompt = [uri]::EscapeDataString((Read-Utf8Text -Path $PromptFile))
        $text = [uri]::EscapeDataString((Read-Utf8Text -Path $TargetFile))
        $url = "$base/tts?text=$text&text_lang=zh&ref_audio_path=$ref&prompt_lang=zh&prompt_text=$prompt&text_split_method=cut5&batch_size=1&media_type=wav&streaming_mode=false"
        Invoke-WebRequest $url -TimeoutSec 300 -OutFile $OutFile -UseBasicParsing
        Write-Host "Saved: $OutFile ($((Get-Item $OutFile).Length) bytes)"
    }
}
