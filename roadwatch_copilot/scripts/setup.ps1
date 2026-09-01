param(
    [string]$PythonExe = "",
    [switch]$SkipFrontend,
    [switch]$SkipVoice,
    [switch]$SkipDriveAssets,
    [switch]$ForceDriveAssets
)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $PythonExe) {
    $ExistingVenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (Test-Path $ExistingVenvPython) {
        $PythonExe = (Resolve-Path $ExistingVenvPython).Path
    }
}
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

if (-not $SkipDriveAssets) {
    & ".\.venv\Scripts\python.exe" -m pip install -r requirements-assets.txt
    if ($LASTEXITCODE -ne 0) { throw "Không cài được gdown để tải Drive assets." }
    $DriveArgs = @("scripts/download_drive_assets.py")
    if ($ForceDriveAssets) { $DriveArgs += "--force" }
    & ".\.venv\Scripts\python.exe" @DriveArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Không bootstrap được model/media từ Google Drive. Có thể dùng -SkipDriveAssets và đặt assets thủ công theo README.md."
    }
} else {
    Write-Host "Drive assets: bỏ qua theo -SkipDriveAssets; dùng models/, media/ và voices/ thủ công."
}

# Piper declares onnxruntime CPU. Keep the DirectML provider last on Windows so
# YOLOP keeps the AMD provider while Piper uses the same Python API. Avoid an
# unnecessary network reinstall when the provider is already healthy.
& ".\.venv\Scripts\python.exe" -c "import onnxruntime as ort; raise SystemExit(0 if 'DmlExecutionProvider' in ort.get_available_providers() else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    & ".\.venv\Scripts\python.exe" -m pip install --force-reinstall --no-deps onnxruntime-directml
    if ($LASTEXITCODE -ne 0) { throw "Không cài/kiểm tra được onnxruntime-directml." }
} else {
    Write-Host "DirectML: đã sẵn sàng, bỏ qua reinstall."
}

if (-not $SkipFrontend) {
    Push-Location frontend
    if (-not (Test-Path "node_modules\vite\bin\vite.js") -or
        -not (Test-Path "node_modules\typescript\bin\tsc")) {
        npm.cmd install --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { throw "Không cài được frontend npm dependencies." }
    } else {
        Write-Host "Frontend dependencies: đã sẵn sàng, bỏ qua npm install."
    }
    $Node = Get-Command node.exe -ErrorAction Stop
    & $Node.Source ".\node_modules\typescript\bin\tsc" -b
    # Build the release bundle selected by scripts/start.ps1. The generic
    # frontend/dist output is not used by the pinned RoadWatch demo runtime.
    & $Node.Source ".\node_modules\vite\bin\vite.js" build --outDir dist-ui-v4
    Pop-Location
}

if (-not $SkipVoice) {
    New-Item -ItemType Directory -Force voices | Out-Null
    & ".\.venv\Scripts\python.exe" -m piper.download_voices vi_VN-vais1000-medium --data-dir voices
    $VoiceModel = Join-Path $ProjectRoot "voices\vi_VN-vais1000-medium.onnx"
    $VoiceConfig = Join-Path $ProjectRoot "voices\vi_VN-vais1000-medium.onnx.json"
    if (-not (Test-Path $VoiceModel) -or -not (Test-Path $VoiceConfig)) {
        throw "Piper voice chưa tải đủ. Cần có vi_VN-vais1000-medium.onnx và .onnx.json trong voices/."
    }
    $VoiceMetadata = Get-Content -LiteralPath $VoiceConfig -Raw | ConvertFrom-Json
    if ($VoiceMetadata.audio.sample_rate -ne 22050 -or
        $VoiceMetadata.audio.quality -ne "medium" -or
        $VoiceMetadata.espeak.voice -ne "vi" -or
        $VoiceMetadata.num_speakers -ne 1) {
        throw "Piper voice không đúng metadata vi_VN-vais1000-medium (language/sample-rate/quality/speaker)."
    }
    if ($null -ne $VoiceMetadata.speaker_id_map -and
        @($VoiceMetadata.speaker_id_map.PSObject.Properties).Count -gt 0) {
        throw "Piper voice vi_VN-vais1000-medium unexpectedly có speaker_id_map; không dùng voice khác."
    }
    $VoiceHash = (Get-FileHash -LiteralPath $VoiceModel -Algorithm SHA256).Hash.ToLowerInvariant()
    $ConfigHash = (Get-FileHash -LiteralPath $VoiceConfig -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "Piper voice: vi_VN-vais1000-medium | RoadWatch voice name: Trúc Ly"
    Write-Host "Piper metadata: vi_VN / 22050 Hz / medium / 1 speaker"
    Write-Host "Piper fingerprint: model=$VoiceHash config=$ConfigHash"
}
Write-Host "Traffic Context: enforce (demo primary; dùng -TrafficContextMode off để rollback policy)"
Write-Host "RoadWatch setup hoàn tất. Chạy .\scripts\start.ps1"
