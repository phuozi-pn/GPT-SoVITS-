param(
    [string]$ContainerName = "",
    [string]$JobId = "manual-spike-001",
    [ValidateSet("all", "gpt", "sovits")]
    [string]$FromStep = "all"
)

# Run fine-tune spike inside engine container (Option B, /workspace/GPT mounted)
$ErrorActionPreference = "Stop"

if (-not $ContainerName) {
    $ContainerName = (
        docker ps --filter "publish=9874" --format "{{.Names}}" | Select-Object -First 1
    )
}
if (-not $ContainerName) {
    Write-Error "No engine container on port 9874. Start with: scripts\engine_run_with_platform_mount.ps1"
}

Write-Host "Container: $ContainerName"
Write-Host "Job ID: $JobId"
if ($FromStep -ne "all") {
    Write-Host "Resume from step: $FromStep"
}
Write-Host ""

docker exec $ContainerName bash /workspace/GPT/infra/engine/prepare_spike_samples.sh
if ($LASTEXITCODE -ne 0) {
    Write-Error "Sample preparation failed. Is /workspace/GPT mounted?"
}

Write-Host ""
if ($FromStep -eq "all") {
    Write-Host "Tip: GPT already done? Resume SoVITS only: .\scripts\spike_train_in_container.ps1 -FromStep sovits"
}
Write-Host "Starting spike train (4+4 epochs). In another terminal watch VRAM:"
Write-Host "  docker exec $ContainerName nvidia-smi"
Write-Host ""

docker exec -it $ContainerName bash -lc "export JOB_ID=$JobId; export SPIKE_FROM_STEP=$FromStep; bash /workspace/GPT/infra/engine/docker-spike-train.sh"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Spike train failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Result inside container: /tmp/spike_train_${JobId}.json"
Write-Host "Copy to host:"
Write-Host "  docker cp ${ContainerName}:/tmp/spike_train_${JobId}.json ."
