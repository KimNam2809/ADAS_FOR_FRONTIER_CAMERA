$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Thiếu .venv" }
& ".\.venv\Scripts\python.exe" -m pytest
if ($LASTEXITCODE -ne 0) { throw "Backend tests failed with exit code $LASTEXITCODE" }
Push-Location frontend
try {
    $Node = Get-Command node.exe -ErrorAction Stop
    if (-not (Test-Path "node_modules\typescript\bin\tsc") -or -not (Test-Path "node_modules\vite\bin\vite.js")) {
        npm.cmd install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed with exit code $LASTEXITCODE" }
    }
    & $Node.Source ".\node_modules\typescript\bin\tsc" -b
    if ($LASTEXITCODE -ne 0) { throw "TypeScript build failed with exit code $LASTEXITCODE" }
    & $Node.Source ".\node_modules\vite\bin\vite.js" build
    if ($LASTEXITCODE -ne 0) { throw "Vite build failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}
