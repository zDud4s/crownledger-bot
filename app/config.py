from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path


APP_DIR_NAME = "CrownLedger"
SETTINGS_FILENAME = "settings.json"
DEFAULT_GITHUB_REPOSITORY = "zDud4s/crownledger-bot"


@dataclass
class LocalSettings:
    clash_api_token: str = ""
    default_clan_tag: str = ""
    last_used_player_tag: str = ""
    war_history_enabled: bool = True
    release_channel: str = "stable"
    github_repo: str = DEFAULT_GITHUB_REPOSITORY


@dataclass(frozen=True)
class LocalSettingsLoadResult:
    settings: LocalSettings
    error: str | None = None


def get_app_data_dir(base_dir: str | Path | None = None) -> Path:
    if base_dir is not None:
        path = Path(base_dir)
    elif os.name == "nt" and os.getenv("APPDATA"):
        path = Path(os.environ["APPDATA"]) / APP_DIR_NAME
    else:
        path = Path.home() / f".{APP_DIR_NAME.lower()}"

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_settings_path(base_dir: str | Path | None = None) -> Path:
    return get_app_data_dir(base_dir=base_dir) / SETTINGS_FILENAME


def load_local_settings_result(base_dir: str | Path | None = None) -> LocalSettingsLoadResult:
    settings_path = get_settings_path(base_dir=base_dir)
    if not settings_path.exists():
        return LocalSettingsLoadResult(settings=LocalSettings())

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return LocalSettingsLoadResult(
            settings=LocalSettings(),
            error=f"Failed to read settings from {settings_path}: {exc}",
        )

    if not isinstance(raw, dict):
        return LocalSettingsLoadResult(
            settings=LocalSettings(),
            error=f"Settings file {settings_path} does not contain a JSON object.",
        )

    defaults = LocalSettings()
    values = {}
    for field in fields(LocalSettings):
        value = raw.get(field.name, getattr(defaults, field.name))
        if field.name == "github_repo":
            value = str(value or "").strip() or DEFAULT_GITHUB_REPOSITORY
        values[field.name] = value
    return LocalSettingsLoadResult(settings=LocalSettings(**values))


def load_local_settings(base_dir: str | Path | None = None) -> LocalSettings:
    return load_local_settings_result(base_dir=base_dir).settings


def save_local_settings(
    settings: LocalSettings,
    base_dir: str | Path | None = None,
) -> Path:
    settings_path = get_settings_path(base_dir=base_dir)
    settings_path.write_text(
        json.dumps(asdict(settings), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return settings_path


def resolve_clash_api_token() -> str:
    token = os.getenv("CLASH_API_TOKEN", "").strip()
    if token:
        return token

    settings_result = load_local_settings_result()
    if settings_result.settings.clash_api_token.strip():
        return settings_result.settings.clash_api_token.strip()

    raise RuntimeError(
        "CLASH_API_TOKEN is not configured. Set the environment variable or save it in desktop settings."
    )
