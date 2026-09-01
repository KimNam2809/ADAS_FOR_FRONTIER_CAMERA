param(
    [string]$Image = "roadwatch:arm64-cloud",
    [switch]$Push,
    [string]$RegistryImage = ""
)

$ErrorActionPreference = "Stop"
$target = if ($Push) { $RegistryImage } else { $Image }
if ($Push -and [string]::IsNullOrWhiteSpace($RegistryImage)) {
    throw "-RegistryImage is required with -Push"
}
$arguments = @(
    "buildx", "build", "--platform", "linux/arm64",
    "-f", "Dockerfile.arm64-cloud", "-t", $target
)
$arguments += if ($Push) { "--push" } else { "--load" }
$arguments += "."
& docker @arguments
if ($LASTEXITCODE -ne 0) { throw "ARM64 image build failed" }
