param([int]$Port = 4174, [string]$DemoUrl = "", [switch]$PrepareMedia, [switch]$NoBuild, [switch]$Legacy)
$ErrorActionPreference = "Stop"
$LandingRoot = Split-Path -Parent $PSScriptRoot
if (-not $NoBuild -and -not $Legacy) {
    & (Join-Path $PSScriptRoot 'build-landing.ps1') -DemoUrl $DemoUrl -PrepareMedia:$PrepareMedia
}
Push-Location (Join-Path $LandingRoot 'frontend')
try {
    $NodeExecutable = (Get-Command node -ErrorAction Stop).Source
    if ($Legacy) {
        Write-Host "Legacy preview: http://127.0.0.1:$Port/landing-legacy.html"
        & $NodeExecutable node_modules/vite/bin/vite.js --config vite.config.ts --port $Port --strictPort
    } else {
        if (-not (Test-Path 'dist-landing/index.html')) { throw 'Missing landing build.' }
        Write-Host "RoadWatch landing: http://127.0.0.1:$Port/"
        & $NodeExecutable node_modules/vite/bin/vite.js preview --config vite.landing.config.ts --port $Port --strictPort
    }
} finally { Pop-Location }
