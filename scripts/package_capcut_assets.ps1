param()
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$PackageRoot = Join-Path $ProjectRoot "output/RoadWatch_CapCut_v1_$Stamp"
if (Test-Path -LiteralPath $PackageRoot) { throw 'Package already exists; retry in a new second.' }
$null = New-Item -ItemType Directory -Path $PackageRoot
$Sources = @(
    @('A01','frontend/landing-public/media/dense.mp4','video/A01_dense_source.mp4'),
    @('A02','frontend/landing-public/media/day.mp4','video/A02_day_source.mp4'),
    @('A03','frontend/landing-public/media/night.mp4','video/A03_night_source.mp4'),
    @('A04','frontend/landing-public/media/rain.mp4','video/A04_rain_source.mp4'),
    @('A05','frontend/landing-public/media/dense-replay.mp4','video/A05_dense_replay.mp4'),
    @('A06','frontend/landing-public/media/day-replay.mp4','video/A06_day_replay.mp4'),
    @('A07','frontend/landing-public/media/night-replay.mp4','video/A07_night_replay.mp4'),
    @('A08','frontend/landing-public/media/rain-replay.mp4','video/A08_rain_replay.mp4'),
    @('A09','data/assets/logo.png','images/A09_RoadWatch_logo.png'),
    @('A10','frontend/landing-public/media/driver-capture.png','images/A10_Driver_HUD.png'),
    @('A11','frontend/landing-public/media/engineer-capture.png','images/A11_Engineer_Console.png'),
    @('A12','frontend/landing-public/media/collision.wav','audio/A12_Piper_collision.wav'),
    @('A13','frontend/landing-public/media/motorcycle.wav','audio/A13_Piper_motorcycle.wav'),
    @('A14','frontend/landing-public/media/speed.wav','audio/A14_Piper_speed.wav'),
    @('A15','frontend/landing-public/media/replays.json','evidence/A15_replay_events.json'),
    @('A16','frontend/landing-public/media/benchmark.json','evidence/A16_runtime_benchmark.json'),
    @('A17','docs/ROADWATCH_TECHNICAL_REPORT.md','evidence/A17_technical_report.md')
)
$Manifest = foreach ($Row in $Sources) {
    $Source = Join-Path $ProjectRoot $Row[1]
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "Missing source: $($Row[1])" }
    $Target = Join-Path $PackageRoot $Row[2]
    $null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target)
    Copy-Item -LiteralPath $Source -Destination $Target
    $SourceHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
    $TargetHash = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
    if ($SourceHash -ne $TargetHash) { throw "Copy mismatch: $($Row[0])" }
    [pscustomobject]@{id=$Row[0];file=$Row[2];source=$Row[1];bytes=(Get-Item -LiteralPath $Target).Length;sha256=$TargetHash;public_release='PENDING_OWNER_REVIEW'}
}
foreach ($Name in @('00_CAPCUT_MASTER_PROMPT.md','01_SCRIPT.md','02_ASSETS.md','03_VISUAL_STYLE.md')) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "docs/capcut_v1/$Name") -Destination $PackageRoot
}
$Manifest | Export-Csv -LiteralPath (Join-Path $PackageRoot 'manifest.csv') -NoTypeInformation -Encoding UTF8
Add-Type -AssemblyName System.IO.Compression.FileSystem
$ZipPath = "$PackageRoot.zip"
[System.IO.Compression.ZipFile]::CreateFromDirectory($PackageRoot, $ZipPath)
$Archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
try {
    if ($Archive.Entries.Count -ne 22) { throw "Unexpected archive entry count: $($Archive.Entries.Count)" }
    foreach ($Asset in $Manifest) {
        $Entry = $Archive.Entries | Where-Object { $_.FullName.Replace('\','/') -eq $Asset.file } | Select-Object -First 1
        if (-not $Entry -or $Entry.Length -ne $Asset.bytes) { throw "Archive mismatch: $($Asset.id)" }
        $Stream = $Entry.Open()
        $Hasher = [System.Security.Cryptography.SHA256]::Create()
        try {
            $ArchivedHash = [BitConverter]::ToString($Hasher.ComputeHash($Stream)).Replace('-','')
            if ($ArchivedHash -ne $Asset.sha256) { throw "Archive hash mismatch: $($Asset.id)" }
        } finally { $Stream.Dispose(); $Hasher.Dispose() }
    }
} finally { $Archive.Dispose() }
[pscustomobject]@{folder=$PackageRoot;zip=$ZipPath;assets=$Manifest.Count;archive_entries=22;bytes=(Get-Item -LiteralPath $ZipPath).Length;status='LOCAL_PACKAGE_VERIFIED';uploaded=$false}
