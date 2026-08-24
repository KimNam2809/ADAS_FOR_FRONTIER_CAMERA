$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$tokenLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^KAGGLE_API_TOKEN=' } | Select-Object -First 1
if (-not $tokenLine) { throw "KAGGLE_API_TOKEN chưa có trong roadwatch/.env." }
$tokenValue = ($tokenLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
if (-not $tokenValue) { throw "KAGGLE_API_TOKEN đang rỗng." }
$env:KAGGLE_API_TOKEN = $tokenValue

$kaggle = Join-Path $projectRoot ".venv\Scripts\kaggle.exe"
if (-not (Test-Path -LiteralPath $kaggle)) { throw "Không tìm thấy Kaggle CLI: $kaggle" }
& $kaggle kernels push -p (Join-Path $projectRoot "kaggle\lane_v2_quality_gate")
if ($LASTEXITCODE -ne 0) { throw "Kaggle kernel push thất bại: $LASTEXITCODE" }
& $kaggle kernels status lekimnam/roadwatch-lane-v2-target-quality-gate
