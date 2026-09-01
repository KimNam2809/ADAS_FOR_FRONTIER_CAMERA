param(
    [switch]$Lan,
    [switch]$NoAudio,
    [int]$Port = 8000,
    [ValidateSet("vnext", "legacy")]
    [string]$AlertCopyProfile = "vnext",
    [string]$FrontendDist = "",
    [ValidateSet("piper", "vieneu")]
    [string]$TtsProvider = "piper",
    [ValidateSet("browser", "server", "none")]
    [string]$AudioOwner = "browser",
    [ValidateSet("off", "shadow", "enforce")]
    [string]$TrafficContextMode = "enforce"
)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    throw "Thiếu .venv. Hãy chạy .\scripts\setup.ps1 trước."
}
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:YOLO_CONFIG_DIR = (Join-Path (Resolve-Path .).Path "data\ultralytics")
$env:ROADWATCH_ALERT_COPY_PROFILE = $AlertCopyProfile
# The demo release uses the new dense-traffic selective-audio policy by
# default. The explicit switch keeps off/shadow available for rollback and
# benchmark without requiring users to edit environment variables.
$env:ROADWATCH_TRAFFIC_CONTEXT_MODE = $TrafficContextMode
# Release demo is pinned to the offline Vietnamese Piper voice. VieNeu remains
# available only when explicitly selected for candidate/A-B testing.
$env:ROADWATCH_TTS_PROVIDER = $TtsProvider
$env:ROADWATCH_TTS_VOICE = "voices/vi_VN-vais1000-medium.onnx"
$env:ROADWATCH_TTS_VOICE_NAME = "Trúc Ly"
# The Web UI owns browser playback. Set this unconditionally so a stale value
# inherited from a previous PowerShell session cannot activate a second route.
# Native edge/AAOS launches can explicitly use -AudioOwner server.
$env:ROADWATCH_AUDIO_OUTPUT = $AudioOwner
$env:ROADWATCH_TTS_CACHE_NAMESPACE = "piper-v3"
if ($FrontendDist) {
    $RequestedFrontend = (Resolve-Path $FrontendDist -ErrorAction Stop).Path
    if (-not (Test-Path (Join-Path $RequestedFrontend "index.html"))) {
        throw "FrontendDist không có index.html: $RequestedFrontend"
    }
    $env:ROADWATCH_FRONTEND_DIST = $RequestedFrontend
} else {
    # Always resolve the current local UI bundle instead of inheriting a stale
    # ROADWATCH_FRONTEND_DIST from a previous server/benchmark session. The
    # explicit -FrontendDist switch remains the safe rollback escape hatch.
    $FrontendCandidates = @(
        (Join-Path $ProjectRoot "frontend\dist-ui-v4"),
        (Join-Path $ProjectRoot "frontend\dist-ui-v3"),
        (Join-Path $ProjectRoot "frontend\dist-ui-v2"),
        (Join-Path $ProjectRoot "frontend\dist"),
        (Join-Path $ProjectRoot "frontend\dist-local")
    )
    $env:ROADWATCH_FRONTEND_DIST = $null
    foreach ($Candidate in $FrontendCandidates) {
        if (Test-Path (Join-Path $Candidate "index.html")) {
            $env:ROADWATCH_FRONTEND_DIST = (Resolve-Path $Candidate).Path
            break
        }
    }
}
if ($env:ROADWATCH_FRONTEND_DIST) {
    Write-Host "RoadWatch frontend: $env:ROADWATCH_FRONTEND_DIST"
}
if ($NoAudio) {
    $env:ROADWATCH_DISABLE_AUDIO = "1"
    $env:ROADWATCH_AUDIO_OUTPUT = "none"
} else {
    # A previous benchmark may have exported ROADWATCH_DISABLE_AUDIO=1 in the
    # same PowerShell session. Normal Web startup must restore browser TTS;
    # benchmark scripts can still opt out explicitly for their own process.
    $env:ROADWATCH_DISABLE_AUDIO = "0"
    if (-not (Test-Path "voices\vi_VN-vais1000-medium.onnx") -or
        -not (Test-Path "voices\vi_VN-vais1000-medium.onnx.json")) {
        throw "Thiếu Piper voice Trúc Ly. Hãy chạy .\scripts\setup.ps1 trước khi start."
    }
}
$HostAddress = if ($Lan) { "0.0.0.0" } else { "127.0.0.1" }
Write-Host "RoadWatch TTS: $env:ROADWATCH_TTS_PROVIDER / $env:ROADWATCH_TTS_VOICE_NAME"
Write-Host "RoadWatch: http://localhost:$Port"
& ".\.venv\Scripts\python.exe" -m uvicorn roadwatch.api:app --host $HostAddress --port $Port
