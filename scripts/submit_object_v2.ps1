$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$tokenLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^KAGGLE_API_TOKEN=' } | Select-Object -First 1
if (-not $tokenLine) {
    throw "KAGGLE_API_TOKEN chưa có trong roadwatch/.env. API key cũ không còn được Kaggle chấp nhận."
}
$tokenValue = ($tokenLine -split '=', 2)[1].Trim()
if (
    ($tokenValue.StartsWith('"') -and $tokenValue.EndsWith('"')) -or
    ($tokenValue.StartsWith("'") -and $tokenValue.EndsWith("'"))
) {
    $tokenValue = $tokenValue.Substring(1, $tokenValue.Length - 2)
}
$env:KAGGLE_API_TOKEN = $tokenValue
if (-not $env:KAGGLE_API_TOKEN) {
    throw "KAGGLE_API_TOKEN đang rỗng."
}

$kaggle = Join-Path $projectRoot ".venv\Scripts\kaggle.exe"
& $kaggle kernels push -p (Join-Path $projectRoot "kaggle\train_object_v2")
if ($LASTEXITCODE -ne 0) {
    throw "Kaggle push thất bại với exit code $LASTEXITCODE"
}
& $kaggle kernels status lekimnam/roadwatch-object-detector-v2-target-domain
