from __future__ import annotations

from app.config import (
    LocalSettings,
    load_local_settings,
    load_local_settings_result,
    resolve_clash_api_token,
    save_local_settings,
)


def test_load_local_settings_returns_defaults_when_missing(tmp_path):
    settings = load_local_settings(base_dir=tmp_path)

    assert settings == LocalSettings()


def test_save_and_load_local_settings_round_trip(tmp_path):
    original = LocalSettings(
        clash_api_token="secret-token",
        default_clan_tag="#ABC123",
        last_used_player_tag="#PLAYER123",
        war_history_enabled=False,
        release_channel="beta",
        github_repo="owner/repo",
    )

    save_local_settings(original, base_dir=tmp_path)
    loaded = load_local_settings(base_dir=tmp_path)

    assert loaded == original


def test_resolve_clash_api_token_prefers_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("CLASH_API_TOKEN", "env-token")
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert resolve_clash_api_token() == "env-token"


def test_resolve_clash_api_token_uses_local_settings(monkeypatch, tmp_path):
    monkeypatch.delenv("CLASH_API_TOKEN", raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    save_local_settings(LocalSettings(clash_api_token="desktop-token"))

    assert resolve_clash_api_token() == "desktop-token"


def test_load_local_settings_result_falls_back_when_json_is_invalid(tmp_path):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{invalid-json", encoding="utf-8")

    result = load_local_settings_result(base_dir=tmp_path)

    assert result.settings == LocalSettings()
    assert result.error is not None
