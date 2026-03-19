param(
    [switch]$Clean,
    [switch]$SkipBuild,
    [switch]$SkipUpdaterSmokeTest
)

$ErrorActionPreference = "Stop"
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$version = python -c "from desktop.version import __version__; print(__version__)"
$mainExe = Join-Path $projectRoot "dist\CrownLedgerLocal\CrownLedgerLocal.exe"
$updaterExe = Join-Path $projectRoot "dist\CrownLedgerLocal\CrownLedgerUpdater.exe"
$releaseZip = Join-Path $projectRoot "dist\release\CrownLedgerLocal-$version-windows-x64.zip"
$buildScript = Join-Path $projectRoot "tools\build_local_app.ps1"

Write-Output "Running unit tests..."
pytest tests\domain tests\app -q -s
if ($LASTEXITCODE -ne 0) {
    throw "Unit tests failed."
}

Write-Output "Running compile check..."
python -m compileall app bot desktop domain
if ($LASTEXITCODE -ne 0) {
    throw "Compile check failed."
}

if (-not $SkipBuild) {
    Write-Output "Building desktop package..."
    if ($Clean) {
        & $buildScript -Clean
    }
    else {
        & $buildScript
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Desktop build failed."
    }
}

foreach ($path in @($mainExe, $updaterExe, $releaseZip)) {
    if (-not (Test-Path $path)) {
        throw "Expected artifact not found: $path"
    }
}

if (-not $SkipUpdaterSmokeTest) {
    Write-Output "Running updater smoke test..."
    $tempRoot = Join-Path $env:TEMP ("crownledger-updater-smoke-" + [guid]::NewGuid().ToString("N"))
    $sourceDir = Join-Path $tempRoot "source"
    $targetDir = Join-Path $tempRoot "target"
    $markerDir = Join-Path $tempRoot "marker"
    $markerPath = Join-Path $markerDir "launched.txt"
    $launcherPath = Join-Path $tempRoot "launcher.py"

    New-Item -ItemType Directory -Path $sourceDir -Force | Out-Null
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    New-Item -ItemType Directory -Path $markerDir -Force | Out-Null

    Set-Content -Path (Join-Path $sourceDir "payload.txt") -Value "fresh" -Encoding Ascii
    Set-Content -Path (Join-Path $targetDir "stale.txt") -Value "stale" -Encoding Ascii

    @"
from pathlib import Path

Path(r"$markerPath").write_text("ok", encoding="utf-8")
"@ | Set-Content -Path $launcherPath -Encoding Ascii

    $pythonExe = (Get-Command python).Source
    $env:VERIFY_UPDATER_EXE = $updaterExe
    $env:VERIFY_UPDATER_SOURCE = $sourceDir
    $env:VERIFY_UPDATER_TARGET = $targetDir
    $env:VERIFY_UPDATER_LAUNCHER = $launcherPath
    $env:VERIFY_UPDATER_PYTHON = $pythonExe
    $env:VERIFY_UPDATER_MARKER = $markerPath

    try {
        @'
from pathlib import Path
import os
import subprocess
import sys
import time

updater = Path(os.environ["VERIFY_UPDATER_EXE"])
source = Path(os.environ["VERIFY_UPDATER_SOURCE"])
target = Path(os.environ["VERIFY_UPDATER_TARGET"])
launcher = Path(os.environ["VERIFY_UPDATER_LAUNCHER"])
python_exe = os.environ["VERIFY_UPDATER_PYTHON"]
marker = Path(os.environ["VERIFY_UPDATER_MARKER"])

result = subprocess.run(
    [
        str(updater),
        "--source-dir", str(source),
        "--target-dir", str(target),
        "--launch-path", str(launcher),
        "--python-exe", python_exe,
        "--wait-seconds", "0.1",
    ],
    capture_output=True,
    text=True,
)

if result.returncode != 0:
    sys.stderr.write(result.stdout)
    sys.stderr.write(result.stderr)
    raise SystemExit(result.returncode)

for _ in range(40):
    if marker.exists():
        break
    time.sleep(0.25)

if not marker.exists():
    raise SystemExit("Updater smoke test did not relaunch the target script.")

if not (target / "payload.txt").exists():
    raise SystemExit("Updater smoke test did not copy the payload file.")

if (target / "stale.txt").exists():
    raise SystemExit("Updater smoke test did not remove stale files.")
'@ | python -

        if ($LASTEXITCODE -ne 0) {
            throw "Updater smoke test failed."
        }
    }
    finally {
        Remove-Item Env:VERIFY_UPDATER_EXE -ErrorAction SilentlyContinue
        Remove-Item Env:VERIFY_UPDATER_SOURCE -ErrorAction SilentlyContinue
        Remove-Item Env:VERIFY_UPDATER_TARGET -ErrorAction SilentlyContinue
        Remove-Item Env:VERIFY_UPDATER_LAUNCHER -ErrorAction SilentlyContinue
        Remove-Item Env:VERIFY_UPDATER_PYTHON -ErrorAction SilentlyContinue
        Remove-Item Env:VERIFY_UPDATER_MARKER -ErrorAction SilentlyContinue

        if (Test-Path $tempRoot) {
            Remove-Item $tempRoot -Recurse -Force
        }
    }
}

Write-Output "Desktop release verification passed."
