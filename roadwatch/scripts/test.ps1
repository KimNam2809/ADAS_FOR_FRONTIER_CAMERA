$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Thiếu .venv" }
& ".\.venv\Scripts\python.exe" -m pytest
Push-Location frontend
npm.cmd run build
Pop-Location

