$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$checks = @(
    "models\yolo11n.pt",
    "models\yolop_lane_detection_640.onnx",
    "configs\finetune_object_v2.json",
    "configs\finetune_lane_v2.json",
    "kaggle\train_object_v3_pilot\kernel-metadata.json",
    "kaggle\train_object_v3_pilot\roadwatch_train_object_v3_pilot.py",
    ".venv\Scripts\kaggle.exe"
)

$missing = @($checks | Where-Object { -not (Test-Path -LiteralPath (Join-Path $projectRoot $_)) })
if ($missing.Count -gt 0) {
    throw "Thiếu artifact local: $($missing -join ', ')"
}

$envPath = Join-Path $projectRoot ".env"
if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Thiếu roadwatch/.env"
}
$names = @(Get-Content -LiteralPath $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=') { $matches[1].Trim() }
})
foreach ($tokenName in @("KAGGLE_API_TOKEN_ACCOUNT_1", "KAGGLE_API_TOKEN_ACCOUNT_2")) {
    if ($names -notcontains $tokenName) {
        throw "Thiếu $tokenName trong roadwatch/.env"
    }
}

$laneQueue = Join-Path $projectRoot "evaluation\rw10_lane_review_queue_v2.json"
$queue = Get-Content -LiteralPath $laneQueue -Raw | ConvertFrom-Json
$records = @($queue.records)
$verified = @($records | Where-Object { $_.review_status -eq "verified" }).Count

$metadata = Get-Content -LiteralPath (Join-Path $projectRoot "kaggle\train_object_v3_pilot\kernel-metadata.json") -Raw | ConvertFrom-Json
if ($metadata.enable_gpu -ne "true") { throw "Object V3 pilot chưa bật GPU" }
if ($metadata.dataset_sources.Count -lt 3) { throw "Object V3 pilot thiếu dataset source" }

$report = [PSCustomObject]@{
    status = "PASS"
    kaggle_account_1_token_present = $true
    kaggle_account_2_token_present = $true
    object_pilot_gpu = $metadata.enable_gpu
    object_pilot_dataset_sources = $metadata.dataset_sources.Count
    lane_queue_records = $records.Count
    lane_verified_frames = $verified
    lane_supervised_training_allowed = ($verified -ge 3000)
    local_training = $false
}
$reportPath = Join-Path $projectRoot "reports\finetune_preflight_20260827.json"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reportPath) | Out-Null
$report | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding UTF8
$report | ConvertTo-Json
