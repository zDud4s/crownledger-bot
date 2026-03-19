param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$version = python -c "from desktop.version import __version__; print(__version__)"
$releaseDir = Join-Path $projectRoot "dist\release"
$zipName = "CrownLedgerLocal-$version-windows-x64.zip"
$zipPath = Join-Path $releaseDir $zipName

if ($Clean) {
    if (Test-Path build\pyinstaller) {
        Remove-Item build\pyinstaller -Recurse -Force
    }
    if (Test-Path build\crownledger_local) {
        Remove-Item build\crownledger_local -Recurse -Force
    }
    if (Test-Path build\crownledger_updater) {
        Remove-Item build\crownledger_updater -Recurse -Force
    }
    if (Test-Path dist\CrownLedgerLocal) {
        Remove-Item dist\CrownLedgerLocal -Recurse -Force
    }
    if (Test-Path dist\CrownLedgerUpdater) {
        Remove-Item dist\CrownLedgerUpdater -Recurse -Force
    }
    if (Test-Path $zipPath) {
        Remove-Item $zipPath -Force
    }
}

python -m PyInstaller build\crownledger_local.spec --noconfirm --clean
python -m PyInstaller build\crownledger_updater.spec --noconfirm --clean

Copy-Item dist\CrownLedgerUpdater\CrownLedgerUpdater.exe dist\CrownLedgerLocal\CrownLedgerUpdater.exe -Force

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path dist\CrownLedgerLocal\* -DestinationPath $zipPath
Write-Output "Release package created: $zipPath"
