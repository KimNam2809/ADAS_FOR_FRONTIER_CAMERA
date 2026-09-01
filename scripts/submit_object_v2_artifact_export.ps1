$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$tokenLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^KAGGLE_API_TOKEN=' } | Select-Object -First 1
if (-not $tokenLine) {
    throw "KAGGLE_API_TOKEN chưa có trong roadwatch/.env."
}
$tokenValue = ($tokenLine -split '=', 2)[1].Trim()
if (
    ($tokenValue.StartsWith('"') -and $tokenValue.EndsWith('"')) -or
    ($tokenValue.StartsWith("'") -and $tokenValue.EndsWith("'"))
) {
    $tokenValue = $tokenValue.Substring(1, $tokenValue.Length - 2)
}
$env:KAGGLE_API_TOKEN = $tokenValue

$kaggle = Join-Path $projectRoot ".venv\Scripts\kaggle.exe"
& $kaggle kernels push -p (Join-Path $projectRoot "kaggle\export_object_v2_artifacts")
if ($LASTEXITCODE -ne 0) {
    throw "Kaggle artifact-export push thất bại với exit code $LASTEXITCODE"
}
& $kaggle kernels status lekimnam/roadwatch-object-v2-artifact-export
