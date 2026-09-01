param([string]$DemoUrl = "", [switch]$PrepareMedia)
$ErrorActionPreference = "Stop"
$LandingRoot = Split-Path -Parent $PSScriptRoot
$PreviousDemoUrl = $env:VITE_DEMO_URL
Push-Location (Join-Path $LandingRoot "frontend")
try {
    $NodeExecutable = (Get-Command node -ErrorAction Stop).Source
    if ($PrepareMedia) {
        & (Join-Path $LandingRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'prepare_landing_assets.py')
        if ($LASTEXITCODE -ne 0) { throw 'Media preparation failed.' }
    }
    if (-not (Test-Path 'landing-public/media/audio.json')) { throw 'Missing media. Run build-landing.ps1 -PrepareMedia first.' }
    if ($DemoUrl) {
        $ParsedDemoUrl = [uri]$DemoUrl
        if ($ParsedDemoUrl.Scheme -notin @('http', 'https')) { throw 'DemoUrl must be HTTP(S).' }
        $env:VITE_DEMO_URL = $DemoUrl
    }
    & $NodeExecutable node_modules/typescript/bin/tsc -p tsconfig.app.json
    if ($LASTEXITCODE -ne 0) { throw 'Landing TypeScript check failed.' }
    & $NodeExecutable node_modules/vite/bin/vite.js build --config vite.landing.config.ts
    if ($LASTEXITCODE -ne 0) { throw 'Landing build failed.' }
    & $NodeExecutable node_modules/vite/bin/vite.js build --config vite.landing.ssr.config.ts
    if ($LASTEXITCODE -ne 0) { throw 'Landing SSR compilation failed.' }
    & $NodeExecutable prerender-landing.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Landing prerender failed.' }
    Write-Host 'Landing built in frontend/dist-landing. HMI dist-ui-v4 unchanged.'
} finally {
    $env:VITE_DEMO_URL = $PreviousDemoUrl
    Pop-Location
}
