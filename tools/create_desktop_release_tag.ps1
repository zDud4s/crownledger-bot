param(
    [switch]$Push,
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$version = python -c "from desktop.version import __version__, release_tag_for; print(__version__); print(release_tag_for())"
$lines = $version -split "`r?`n" | Where-Object { $_ -ne "" }
$appVersion = $lines[0]
$tagName = $lines[1]

if (-not $AllowDirty) {
    $status = git status --porcelain
    if ($status) {
        throw "Working tree is dirty. Commit or stash changes first, or rerun with -AllowDirty."
    }
}

$existing = git tag --list $tagName
if ($existing) {
    throw "Tag $tagName already exists."
}

git tag -a $tagName -m "Desktop release $appVersion"
Write-Output "Created tag: $tagName"

if ($Push) {
    git push origin $tagName
    Write-Output "Pushed tag to origin: $tagName"
} else {
    Write-Output "Tag created locally only."
    Write-Output "Push it with: git push origin $tagName"
}
