param(
    [switch]$Lan,
    [switch]$NoAudio,
    [int]$Port = 8000
)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Thiếu .venv. Hãy chạy .\scripts\setup.ps1 trước."
}
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:YOLO_CONFIG_DIR = (Join-Path (Resolve-Path .).Path "data\ultralytics")
$LocalFrontend = Join-Path $ProjectRoot "frontend\dist-local"
if (Test-Path (Join-Path $LocalFrontend "index.html")) {
    $env:ROADWATCH_FRONTEND_DIST = $LocalFrontend
}
if ($NoAudio) { $env:ROADWATCH_DISABLE_AUDIO = "1" }
$HostAddress = if ($Lan) { "0.0.0.0" } else { "127.0.0.1" }
Write-Host "RoadWatch: http://localhost:$Port"
& ".\.venv\Scripts\python.exe" -m uvicorn roadwatch.api:app --host $HostAddress --port $Port
