from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

from app.config import get_app_data_dir


_VERSION_RE = re.compile(r"^(?P<core>\d+(?:\.\d+){0,2})(?P<suffix>.*)$")


@dataclass(frozen=True)
class UpdateCheckResult:
    status: str
    current_version: str
    latest_version: str | None = None
    download_url: str | None = None
    release_url: str | None = None
    message: str = ""


@dataclass(frozen=True)
class StagedUpdate:
    version: str
    archive_path: Path
    extract_dir: Path
    app_dir: Path


def normalize_version_text(value: str) -> str:
    normalized = value.strip()
    for prefix in ("refs/tags/desktop-v", "desktop-v", "refs/tags/v", "v"):
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return normalized


def version_key(value: str) -> tuple[tuple[int, int, int], int]:
    normalized = normalize_version_text(value)
    match = _VERSION_RE.match(normalized)
    if not match:
        raise ValueError(f"Invalid version: {value}")

    parts = [int(part) for part in match.group("core").split(".")]
    while len(parts) < 3:
        parts.append(0)

    suffix = match.group("suffix").strip().lower()
    stability_rank = 0 if suffix else 1
    return (parts[0], parts[1], parts[2]), stability_rank


def is_newer_version(latest_version: str, current_version: str) -> bool:
    return version_key(latest_version) > version_key(current_version)


def _release_api_url(repository: str, release_channel: str) -> str:
    repo = repository.strip().strip("/")
    if release_channel == "beta":
        return f"https://api.github.com/repos/{repo}/releases"
    return f"https://api.github.com/repos/{repo}/releases/latest"


def _pick_release(payload: dict | list, release_channel: str) -> dict:
    if release_channel == "beta":
        if not isinstance(payload, list) or not payload:
            raise ValueError("No releases found.")
        return payload[0]

    if not isinstance(payload, dict):
        raise ValueError("Unexpected release payload.")
    return payload


def check_for_update(
    current_version: str,
    repository: str,
    release_channel: str = "stable",
    timeout_s: int = 10,
) -> UpdateCheckResult:
    if not repository.strip():
        return UpdateCheckResult(
            status="not_configured",
            current_version=current_version,
            message="GitHub repository is not configured.",
        )

    url = _release_api_url(repository, release_channel)

    try:
        response = requests.get(
            url,
            timeout=timeout_s,
            headers={"Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        release = _pick_release(response.json(), release_channel)
    except requests.RequestException as exc:
        return UpdateCheckResult(
            status="error",
            current_version=current_version,
            message=f"Failed to check for updates: {exc}",
        )
    except ValueError as exc:
        return UpdateCheckResult(
            status="error",
            current_version=current_version,
            message=str(exc),
        )

    latest_version = release.get("tag_name", "")
    assets = release.get("assets") or []
    zip_assets = [
        asset for asset in assets if str(asset.get("name", "")).lower().endswith(".zip")
    ]
    download_url = zip_assets[0].get("browser_download_url") if zip_assets else None

    if not latest_version:
        return UpdateCheckResult(
            status="error",
            current_version=current_version,
            message="Release payload did not include tag_name.",
        )

    if is_newer_version(latest_version, current_version):
        return UpdateCheckResult(
            status="update_available",
            current_version=current_version,
            latest_version=latest_version,
            download_url=download_url,
            release_url=release.get("html_url"),
            message=f"Update available: {latest_version}",
        )

    return UpdateCheckResult(
        status="up_to_date",
        current_version=current_version,
        latest_version=latest_version,
        release_url=release.get("html_url"),
        message="App is up to date.",
    )


def _updates_root(base_dir: str | Path | None = None) -> Path:
    root = get_app_data_dir(base_dir=base_dir) / "updates"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _staging_dir_for(version: str, base_dir: str | Path | None = None) -> Path:
    normalized = normalize_version_text(version).replace(".", "_")
    staging_dir = _updates_root(base_dir=base_dir) / normalized
    staging_dir.mkdir(parents=True, exist_ok=True)
    return staging_dir


def _resolve_extracted_app_dir(extract_dir: Path) -> Path:
    entries = [entry for entry in extract_dir.iterdir()]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return extract_dir


def stage_update_from_release(
    download_url: str,
    version: str,
    timeout_s: int = 60,
    base_dir: str | Path | None = None,
) -> StagedUpdate:
    if not download_url:
        raise ValueError("Release does not contain a downloadable zip asset.")

    staging_dir = _staging_dir_for(version, base_dir=base_dir)
    archive_path = staging_dir / "release.zip"
    extract_dir = staging_dir / "extracted"

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with requests.get(download_url, stream=True, timeout=timeout_s) as response:
        response.raise_for_status()
        with archive_path.open("wb") as archive_file:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if chunk:
                    archive_file.write(chunk)

    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extract_dir)

    app_dir = _resolve_extracted_app_dir(extract_dir)
    return StagedUpdate(
        version=normalize_version_text(version),
        archive_path=archive_path,
        extract_dir=extract_dir,
        app_dir=app_dir,
    )
