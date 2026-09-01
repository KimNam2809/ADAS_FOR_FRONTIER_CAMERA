$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$kernelPath = Join-Path $projectRoot "kaggle\train_object_v3_full"
$kaggle = Join-Path $projectRoot ".venv\Scripts\kaggle.exe"
$kernelId = "lekimnam/roadwatch-object-detector-v3-full-fine-tune"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Không tìm thấy roadwatch/.env."
}
if (-not (Test-Path -LiteralPath $kaggle)) {
    throw "Không tìm thấy Kaggle CLI: $kaggle"
}
if (-not (Test-Path -LiteralPath (Join-Path $kernelPath "kernel-metadata.json"))) {
    throw "Thiếu kernel-metadata.json của Object V3 full."
}

$tokenLine = Get-Content -LiteralPath $envPath |
    Where-Object { $_ -match '^KAGGLE_API_TOKEN_ACCOUNT_1=' } |
    Select-Object -First 1
if (-not $tokenLine) {
    throw "KAGGLE_API_TOKEN_ACCOUNT_1 chưa có trong roadwatch/.env."
}
$tokenValue = ($tokenLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
if (-not $tokenValue) {
    throw "KAGGLE_API_TOKEN_ACCOUNT_1 đang rỗng."
}
$env:KAGGLE_API_TOKEN = $tokenValue

Write-Host "Submitting RoadWatch Object V3 full fine-tune (Kaggle GPU, 80 epochs max)..."
& $kaggle kernels push -p $kernelPath
if ($LASTEXITCODE -ne 0) {
    throw "Kaggle push thất bại với exit code $LASTEXITCODE"
}
& $kaggle kernels status $kernelId
if ($LASTEXITCODE -ne 0) {
    throw "Không đọc được trạng thái Object V3 full với exit code $LASTEXITCODE"
}
