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

$videoNames = @(
    "dashcam_vietnam.mp4",
    "dashcam_vietnam_night.mp4",
    "dashcam_vietnam_rain+night.mp4",
    "dashcam_vietnam_traffic_multi.mp4",
    "test_video1.mp4",
    "test_video5.mp4",
    "video_test.mp4"
)
$stage = Join-Path $projectRoot ".cache\kaggle_target_videos_v1"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot "kaggle\target_videos_dataset\dataset-metadata.json") -Destination (Join-Path $stage "dataset-metadata.json") -Force

foreach ($name in $videoNames) {
    $source = Join-Path $projectRoot ("media\" + $name)
    $target = Join-Path $stage $name
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Thiếu video bắt buộc: $source"
    }
    if (-not (Test-Path -LiteralPath $target)) {
        New-Item -ItemType HardLink -Path $target -Target $source | Out-Null
    }
}

$kaggle = Join-Path $projectRoot ".venv\Scripts\kaggle.exe"
& $kaggle datasets create -p $stage -r zip -q
if ($LASTEXITCODE -ne 0) {
    throw "Kaggle dataset create thất bại với exit code $LASTEXITCODE"
}
