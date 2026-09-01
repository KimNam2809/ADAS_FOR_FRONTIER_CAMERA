param(
    [string]$DatasetRoot = "roadwatch/.cache/sign-candidates/maitam/full/archive",
    [string]$OutputRoot = "roadwatch/.cache/sign-candidates/maitam/speed-audit",
    [int]$SheetSamples = 80,
    [int]$TileSize = 144
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$dataset = (Resolve-Path -LiteralPath $DatasetRoot).Path
$imagesDir = Join-Path $dataset "images"
$labelsDir = Join-Path $dataset "labels"
$classesPath = Join-Path $dataset "classes.txt"
if (-not (Test-Path -LiteralPath $imagesDir) -or
    -not (Test-Path -LiteralPath $labelsDir) -or
    -not (Test-Path -LiteralPath $classesPath)) {
    throw "VNTS dataset is incomplete at $dataset"
}

$output = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputRoot))
[System.IO.Directory]::CreateDirectory($output) | Out-Null

$classes = Get-Content -LiteralPath $classesPath
$speedByClass = @{}
for ($classId = 0; $classId -lt $classes.Count; $classId++) {
    if ($classes[$classId] -match '^P\.127\*(\d+)$') {
        $speedByClass[$classId] = [int]$Matches[1]
    }
}
if ($speedByClass.Count -eq 0) {
    throw "No P.127 numeric speed classes found in $classesPath"
}

$splitByStem = @{}
foreach ($splitName in @("train", "test")) {
    $splitFile = Join-Path $dataset ("split_dataset/{0}_files.txt" -f $splitName)
    if (-not (Test-Path -LiteralPath $splitFile)) { continue }
    foreach ($entry in Get-Content -LiteralPath $splitFile) {
        if ([string]::IsNullOrWhiteSpace($entry)) { continue }
        $splitByStem[[System.IO.Path]::GetFileNameWithoutExtension($entry.Trim())] = $splitName
    }
}

$records = [System.Collections.Generic.List[object]]::new()
foreach ($labelPath in Get-ChildItem -LiteralPath $labelsDir -Filter "*.txt" -File | Sort-Object Name) {
    $stem = $labelPath.BaseName
    $imagePath = Join-Path $imagesDir ($stem + ".jpg")
    if (-not (Test-Path -LiteralPath $imagePath)) { continue }
    $lines = Get-Content -LiteralPath $labelPath.FullName
    $wanted = @($lines | Where-Object {
        if ([string]::IsNullOrWhiteSpace($_)) { return $false }
        $parts = $_ -split '\s+'
        return $parts.Count -ge 5 -and $speedByClass.ContainsKey([int]$parts[0])
    })
    if ($wanted.Count -eq 0) { continue }

    $image = [System.Drawing.Image]::FromFile($imagePath)
    try {
        for ($boxIndex = 0; $boxIndex -lt $wanted.Count; $boxIndex++) {
            $parts = $wanted[$boxIndex] -split '\s+'
            $classId = [int]$parts[0]
            $speed = $speedByClass[$classId]
            $cx = [double]$parts[1] * $image.Width
            $cy = [double]$parts[2] * $image.Height
            $bw = [double]$parts[3] * $image.Width
            $bh = [double]$parts[4] * $image.Height
            $pad = 0.12
            $left = [Math]::Max(0, [int][Math]::Floor($cx - ($bw * (0.5 + $pad))))
            $top = [Math]::Max(0, [int][Math]::Floor($cy - ($bh * (0.5 + $pad))))
            $right = [Math]::Min($image.Width, [int][Math]::Ceiling($cx + ($bw * (0.5 + $pad))))
            $bottom = [Math]::Min($image.Height, [int][Math]::Ceiling($cy + ($bh * (0.5 + $pad))))
            if ($right -le $left -or $bottom -le $top) { continue }

            $split = if ($splitByStem.ContainsKey($stem)) { $splitByStem[$stem] } else { "unspecified" }
            $targetDir = Join-Path $output ("crops/{0}/{1}" -f $split, $speed)
            [System.IO.Directory]::CreateDirectory($targetDir) | Out-Null
            $targetPath = Join-Path $targetDir ("{0}_{1}.jpg" -f $stem, $boxIndex)
            $bitmap = New-Object System.Drawing.Bitmap ($right - $left), ($bottom - $top)
            try {
                $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                try {
                    $graphics.DrawImage(
                        $image,
                        [System.Drawing.Rectangle]::new(0, 0, $bitmap.Width, $bitmap.Height),
                        [System.Drawing.Rectangle]::new($left, $top, $right - $left, $bottom - $top),
                        [System.Drawing.GraphicsUnit]::Pixel
                    )
                } finally {
                    $graphics.Dispose()
                }
                $bitmap.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Jpeg)
            } finally {
                $bitmap.Dispose()
            }
            $records.Add([PSCustomObject]@{
                split = $split
                speed = $speed
                source = $imagePath
                crop = $targetPath
                width = $right - $left
                height = $bottom - $top
            })
        }
    } finally {
        $image.Dispose()
    }
}

function New-ContactSheet {
    param(
        [object[]]$Items,
        [string]$TargetPath,
        [int]$MaxSamples,
        [int]$Tile
    )
    if ($Items.Count -eq 0) { return }
    $take = [Math]::Min($Items.Count, $MaxSamples)
    $selected = for ($index = 0; $index -lt $take; $index++) {
        $sourceIndex = [Math]::Min($Items.Count - 1, [int][Math]::Floor($index * $Items.Count / $take))
        $Items[$sourceIndex]
    }
    $columns = 10
    $rows = [int][Math]::Ceiling($take / $columns)
    $sheet = New-Object System.Drawing.Bitmap ($columns * $Tile), ($rows * ($Tile + 22))
    try {
        $graphics = [System.Drawing.Graphics]::FromImage($sheet)
        try {
            $graphics.Clear([System.Drawing.Color]::White)
            $font = New-Object System.Drawing.Font "Arial", 9
            try {
                for ($index = 0; $index -lt $selected.Count; $index++) {
                    $item = $selected[$index]
                    $x = ($index % $columns) * $Tile
                    $y = [Math]::Floor($index / $columns) * ($Tile + 22)
                    $crop = [System.Drawing.Image]::FromFile($item.crop)
                    try {
                        $scale = [Math]::Min($Tile / $crop.Width, $Tile / $crop.Height)
                        $drawWidth = [int]($crop.Width * $scale)
                        $drawHeight = [int]($crop.Height * $scale)
                        $drawX = $x + [int](($Tile - $drawWidth) / 2)
                        $drawY = $y + [int](($Tile - $drawHeight) / 2)
                        $graphics.DrawImage($crop, $drawX, $drawY, $drawWidth, $drawHeight)
                    } finally {
                        $crop.Dispose()
                    }
                    $label = [System.IO.Path]::GetFileNameWithoutExtension($item.crop)
                    if ($label.Length -gt 18) { $label = $label.Substring(0, 18) }
                    $graphics.DrawString($label, $font, [System.Drawing.Brushes]::Black, $x + 2, $y + $Tile + 2)
                }
            } finally {
                $font.Dispose()
            }
        } finally {
            $graphics.Dispose()
        }
        $sheet.Save($TargetPath, [System.Drawing.Imaging.ImageFormat]::Jpeg)
    } finally {
        $sheet.Dispose()
    }
}

$sheetsDir = Join-Path $output "contact-sheets"
[System.IO.Directory]::CreateDirectory($sheetsDir) | Out-Null
foreach ($group in $records | Group-Object split, speed) {
    $split = $group.Group[0].split
    $speed = $group.Group[0].speed
    $sheetPath = Join-Path $sheetsDir ("{0}_speed_{1}.jpg" -f $split, $speed)
    New-ContactSheet -Items @($group.Group | Sort-Object crop) -TargetPath $sheetPath -MaxSamples $SheetSamples -Tile $TileSize
}

$summary = @($records | Group-Object split, speed | ForEach-Object {
    [PSCustomObject]@{
        split = $_.Group[0].split
        speed = $_.Group[0].speed
        boxes = $_.Count
        unique_source_images = @($_.Group.source | Sort-Object -Unique).Count
    }
} | Sort-Object split, speed)
$report = [PSCustomObject]@{
    source = $dataset
    generated_at = (Get-Date).ToString("o")
    taxonomy = @($speedByClass.GetEnumerator() | Sort-Object Key | ForEach-Object {
        [PSCustomObject]@{ class_id = $_.Key; speed = $_.Value; label = $classes[$_.Key] }
    })
    summary = $summary
    total_boxes = $records.Count
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $output "audit-report.json") -Encoding utf8
$summary | Format-Table -AutoSize
Write-Output ("Audit report: {0}" -f (Join-Path $output "audit-report.json"))
