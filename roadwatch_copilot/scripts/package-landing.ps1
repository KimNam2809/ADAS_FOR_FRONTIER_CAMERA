param([switch]$PublicMediaApproved)
$ErrorActionPreference = "Stop"
$LandingRoot = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $LandingRoot 'frontend/dist-landing'
if (-not (Test-Path (Join-Path $Dist 'index.html'))) { throw 'Build landing first.' }
if (-not $PublicMediaApproved) {
    throw 'Public packaging requires explicit rights/privacy approval for every asset and public document. Local preview remains available.'
}
# Build context contains only compiled static assets, never .env/model/data.
Copy-Item -LiteralPath (Join-Path $LandingRoot 'deploy/gcp/landing/Dockerfile') -Destination $Dist -Force
Copy-Item -LiteralPath (Join-Path $LandingRoot 'deploy/gcp/landing/nginx.conf') -Destination $Dist -Force
Write-Host "Prepared static-only context: $Dist"
Write-Host 'No cloud deployment, billing, IAM or DNS change performed.'
