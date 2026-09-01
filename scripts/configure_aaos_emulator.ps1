param(
    [string]$Serial = "",
    [int]$Port = 8000,
    [double]$Latitude = 10.7769,
    [double]$Longitude = 106.7009
)
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$localProperties = Join-Path $projectRoot "android\roadwatch-aaos\local.properties"
$sdkFromProperties = $null
if (Test-Path -LiteralPath $localProperties) {
    $sdkLine = Get-Content -LiteralPath $localProperties | Where-Object { $_ -match '^sdk\.dir=' } | Select-Object -First 1
    if ($sdkLine) {
        $sdkFromProperties = ($sdkLine -split '=', 2)[1].Trim().Replace('\:', ':').Replace('\\', '\')
    }
}
$adbCommand = Get-Command adb -ErrorAction SilentlyContinue
$adbCandidates = @(
    $(if ($adbCommand) { $adbCommand.Source }),
    $(if ($sdkFromProperties) { Join-Path $sdkFromProperties "platform-tools\adb.exe" }),
    $(if ($env:ANDROID_SDK_ROOT) { Join-Path $env:ANDROID_SDK_ROOT "platform-tools\adb.exe" }),
    $(if ($env:ANDROID_HOME) { Join-Path $env:ANDROID_HOME "platform-tools\adb.exe" }),
    $(Join-Path $env:LOCALAPPDATA "Android\Sdk\platform-tools\adb.exe")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
$adb = $adbCandidates | Select-Object -First 1
if (-not $adb) {
    throw "Không tìm thấy adb. Hãy cài Android SDK Platform-Tools hoặc thêm adb vào PATH."
}

& $adb start-server | Out-Null
if (-not $Serial) {
    $deviceLine = & $adb devices | Where-Object { $_ -match '^(emulator-\d+)\s+device$' } | Select-Object -First 1
    if (-not $deviceLine) {
        throw "Không tìm thấy AAOS emulator đang chạy. Hãy mở Automotive Virtual Device trước."
    }
    $Serial = ($deviceLine -split '\s+')[0]
}

& $adb -s $Serial reverse "tcp:$Port" "tcp:$Port"
if ($LASTEXITCODE -ne 0) {
    throw "Không thể tạo adb reverse cho $Serial."
}

# Android emulator expects longitude before latitude.
& $adb -s $Serial emu geo fix $Longitude $Latitude
if ($LASTEXITCODE -ne 0) {
    throw "Không thể đặt GPS giả lập cho $Serial."
}

Write-Host "AAOS emulator: $Serial"
Write-Host "RoadWatch tunnel: http://127.0.0.1:$Port -> Windows host port $Port"
Write-Host "Mock GPS: $Latitude, $Longitude (TP.HCM)"
