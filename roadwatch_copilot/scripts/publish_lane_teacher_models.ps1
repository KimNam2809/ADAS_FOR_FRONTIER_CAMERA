$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$tokenLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^KAGGLE_API_TOKEN=' } | Select-Object -First 1
if (-not $tokenLine) { throw "KAGGLE_API_TOKEN chưa có trong roadwatch/.env." }
$tokenValue = ($tokenLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
if (-not $tokenValue) { throw "KAGGLE_API_TOKEN đang rỗng." }
$env:KAGGLE_API_TOKEN = $tokenValue

$model = Join-Path $projectRoot "models\ufldv2_culane_res18_320x1600.onnx"
if (-not (Test-Path -LiteralPath $model)) { throw "Thiếu UFLDv2 ONNX: $model" }
$stage = Join-Path $projectRoot ".cache\kaggle_lane_teacher_models_v1"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot "kaggle\lane_teacher_models\dataset-metadata.json") -Destination (Join-Path $stage "dataset-metadata.json") -Force
$target = Join-Path $stage "ufldv2_culane_res18_320x1600.onnx"
if (-not (Test-Path -LiteralPath $target)) {
    New-Item -ItemType HardLink -Path $target -Target $model | Out-Null
}

$kaggle = Join-Path $projectRoot ".venv\Scripts\kaggle.exe"
if (-not (Test-Path -LiteralPath $kaggle)) { throw "Không tìm thấy Kaggle CLI: $kaggle" }
& $kaggle datasets create -p $stage -r zip -q
if ($LASTEXITCODE -ne 0) { throw "Kaggle dataset create thất bại: $LASTEXITCODE" }
