param(
    [string]$PythonExe = "",
    [switch]$SkipFrontend,
    [switch]$SkipVoice
)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $PythonExe) {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCommand) { $PythonExe = $PythonCommand.Source }
    else {
        $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($PyLauncher) {
            $Candidate = & $PyLauncher.Source -3 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0) { $PythonExe = $Candidate }
        }
    }
}
if (-not $PythonExe -or -not (Test-Path $PythonExe)) {
    throw "Không tìm thấy Python 3.10-3.12. Chạy: .\scripts\setup.ps1 -PythonExe C:\duong-dan\python.exe"
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $PythonExe -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-dev.txt

# Piper declares onnxruntime CPU. Reinstall DirectML last on Windows so YOLOP
# keeps the AMD provider while Piper continues to use the same Python API.
& ".\.venv\Scripts\python.exe" -m pip install --force-reinstall --no-deps onnxruntime-directml

if (-not $SkipFrontend) {
    Push-Location frontend
    npm.cmd install
    npm.cmd run build
    Pop-Location
}

if (-not $SkipVoice) {
    New-Item -ItemType Directory -Force voices | Out-Null
    & ".\.venv\Scripts\python.exe" -m piper.download_voices vi_VN-vais1000-medium --data-dir voices
}
Write-Host "RoadWatch setup hoàn tất. Chạy .\scripts\start.ps1"

