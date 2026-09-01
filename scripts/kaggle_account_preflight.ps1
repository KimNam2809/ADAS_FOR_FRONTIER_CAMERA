param(
    [ValidateSet("1", "2")]
    [string]$Account = "2",
    [string[]]$PrivateDataset = @(
        "lekimnam/roadwatch-target-domain-videos-v1",
        "lekimnam/roadwatch-lane-teacher-models-v1"
    )
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"
$kaggle = Join-Path $projectRoot ".venv\Scripts\kaggle.exe"
$tokenName = "KAGGLE_API_TOKEN_ACCOUNT_$Account"

if (-not (Test-Path -LiteralPath $envPath)) { throw "Không tìm thấy roadwatch/.env" }
if (-not (Test-Path -LiteralPath $kaggle)) { throw "Không tìm thấy Kaggle CLI: $kaggle" }

$tokenLine = Get-Content -LiteralPath $envPath |
    Where-Object { $_ -match ("^" + [regex]::Escape($tokenName) + "=") } |
    Select-Object -First 1
if (-not $tokenLine) { throw "Thiếu $tokenName trong roadwatch/.env" }
$tokenValue = ($tokenLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
if (-not $tokenValue) { throw "$tokenName đang rỗng" }
$env:KAGGLE_API_TOKEN = $tokenValue

$quota = @(& $kaggle quota 2>&1)
$quotaExit = $LASTEXITCODE
$kernels = @(& $kaggle kernels list --mine --page-size 5 2>&1)
$kernelsExit = $LASTEXITCODE
$datasets = @(& $kaggle datasets list --mine --page-size 5 2>&1)
$datasetsExit = $LASTEXITCODE
$privateAccess = foreach ($slug in $PrivateDataset) {
    $out = @(& $kaggle datasets files $slug --page-size 5 2>&1)
    $exit = $LASTEXITCODE
    [ordered]@{
        slug = $slug
        status = if ($exit -eq 0) { "ACCESS_OK" } else { "ACCESS_FAIL" }
        exit_code = $exit
        check = "datasets files"
    }
}
$privateAccessOk = @($privateAccess | Where-Object { $_.status -eq "ACCESS_OK" }).Count -eq $PrivateDataset.Count

$report = [ordered]@{
    status = if ($quotaExit -eq 0 -and $kernelsExit -eq 0 -and $datasetsExit -eq 0 -and $privateAccessOk) { "READY" } elseif ($quotaExit -eq 0 -and $kernelsExit -eq 0 -and $datasetsExit -eq 0) { "AUTH_PASS_PRIVATE_ACCESS_PENDING" } else { "AUTH_OR_READONLY_CHECK_FAILED" }
    account = $Account
    token_variable = $tokenName
    quota_exit = $quotaExit
    kernels_list_exit = $kernelsExit
    datasets_list_exit = $datasetsExit
    private_dataset_access = @($privateAccess)
    secret_logged = $false
    mutation_performed = $false
    note = "This preflight uses datasets files for read access; datasets status is not used because it may require owner-level status permission. No kernel is submitted and no GPU is used."
}
$reportPath = Join-Path $projectRoot ("reports\kaggle_account_{0}_preflight.json" -f $Account)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $reportPath) | Out-Null
$report | ConvertTo-Json | Set-Content -LiteralPath $reportPath -Encoding UTF8
$report | ConvertTo-Json
