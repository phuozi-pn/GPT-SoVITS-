# Sync running GPT-SoVITS Docker container name (and engine paths) into repo .env
param(
    [switch]$Quiet,
    [string]$EnvPath = "",
    [string]$EngineRoot = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
if (-not $EnvPath) {
    $EnvPath = Join-Path $RepoRoot ".env"
}

function ConvertTo-SingleLine {
    param($Value)
    if ($null -eq $Value) { return "" }
    if ($Value -is [System.Array]) {
        return (($Value | ForEach-Object { "$_" }) -join "`n").Replace("`r", "").Trim()
    }
    return ("$Value").Replace("`r", "").Trim()
}

function Import-DotEnvFile {
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

function Get-RunningContainerByFilter {
    param([string]$Filter)
    $name = docker ps --filter $Filter --format "{{.Names}}" 2>$null | Select-Object -First 1
    if (-not $name) { return $null }
    return (ConvertTo-SingleLine $name)
}

function Test-ContainerRunning {
    param([string]$Name)
    if (-not $Name) { return $false }
    $id = docker ps -q --filter "name=$Name" 2>$null | Select-Object -First 1
    return [bool]$id
}

function Find-RunningEngineContainer {
    param([string]$PreferredName = "")

    if ($PreferredName -and (Test-ContainerRunning $PreferredName)) {
        return (Get-RunningContainerByFilter "name=$PreferredName")
    }

    $byPort = Get-RunningContainerByFilter "publish=9874"
    if ($byPort) { return $byPort }

    $all = docker ps --format "{{.Names}}" 2>$null
    if ($all) {
        $match = $all | Where-Object { $_ -match "GPT-SoVITS|gpt-sovits" } | Select-Object -First 1
        if ($match) { return (ConvertTo-SingleLine $match) }
    }

    return $null
}

function Set-DotEnvValue {
    param(
        [string]$Path,
        [string]$Key,
        [string]$Value
    )
    $lines = if (Test-Path $Path) { @(Get-Content -LiteralPath $Path) } else { @() }
    $found = $false
    $newLines = foreach ($line in $lines) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=") {
            $found = $true
            "$Key=$Value"
        } else {
            $line
        }
    }
    if (-not $found) {
        if ($newLines.Count -gt 0 -and $newLines[-1] -ne "") {
            $newLines += ""
        }
        $newLines += "$Key=$Value"
    }
    Set-Content -LiteralPath $Path -Value $newLines -Encoding utf8
}

function Sync-EngineEnv {
    param(
        [switch]$Quiet,
        [string]$EnvPath,
        [string]$EngineRoot
    )

    Import-DotEnvFile $EnvPath

    $container = Find-RunningEngineContainer -PreferredName $env:ENGINE_TRAIN_DOCKER
    if (-not $container) {
        $msg = @"
No running GPT-SoVITS container found.

Start engine first (keep terminal open):
  cd C:\Users\panta\Desktop\GPT-SOVITS\GPT-SoVITS
  docker compose run --service-ports --remove-orphans GPT-SoVITS-CU128-Lite
"@
        if ($Quiet) { Write-Error $msg }
        else { Write-Error $msg }
    }

    if (-not $EngineRoot) {
        $EngineRoot = $env:ENGINE_TRAIN_ROOT
    }
    if (-not $EngineRoot) {
        $default = "C:\Users\panta\Desktop\GPT-SOVITS\GPT-SoVITS"
        if (Test-Path $default) {
            $EngineRoot = $default
        }
    }
    if ($EngineRoot) {
        $EngineRoot = ($EngineRoot -replace '\\', '/').TrimEnd('/')
    }

    $updates = [ordered]@{
        ENGINE_TRAIN_DOCKER            = $container
        ENGINE_TTS_URL                 = "http://127.0.0.1:9880"
        ENGINE_TRAIN_ROOT_IN_DOCKER    = "/workspace/GPT-SoVITS"
        ENGINE_TRAIN_PLATFORM_MOUNT    = "/workspace/GPT"
    }
    if ($EngineRoot) {
        $updates["ENGINE_TRAIN_ROOT"] = $EngineRoot
    }

    $changed = @()
    foreach ($key in $updates.Keys) {
        $newVal = $updates[$key]
        $oldVal = (Get-Item -Path "env:$key" -ErrorAction SilentlyContinue).Value
        if ($oldVal -ne $newVal) {
            Set-DotEnvValue -Path $EnvPath -Key $key -Value $newVal
            $changed += [pscustomobject]@{ Key = $key; Old = $oldVal; New = $newVal }
        }
    }

    if (-not $Quiet) {
        if ($changed.Count -eq 0) {
            Write-Host "OK: .env already up to date (ENGINE_TRAIN_DOCKER=$container)"
        } else {
            Write-Host "Updated $EnvPath :"
            foreach ($c in $changed) {
                if ($c.Old) {
                    Write-Host "  $($c.Key): $($c.Old) -> $($c.New)"
                } else {
                    Write-Host "  $($c.Key): (new) $($c.New)"
                }
            }
        }
    } elseif ($changed.Count -gt 0) {
        Write-Host "engine_sync_env: updated ENGINE_TRAIN_DOCKER -> $container"
    }

    return $container
}

# Dot-sourced: only define functions. Invoked directly: run sync.
if ($MyInvocation.InvocationName -ne '.') {
    $null = Sync-EngineEnv -Quiet:$Quiet -EnvPath $EnvPath -EngineRoot $EngineRoot
}
