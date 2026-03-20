from __future__ import annotations

from app.config import DEFAULT_GITHUB_REPOSITORY
from app.update_service import check_for_update, is_newer_version, version_key


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_version_key_treats_stable_as_newer_than_dev():
    assert version_key("0.1.0") > version_key("0.1.0-dev")


def test_is_newer_version_handles_desktop_tag_prefix():
    assert is_newer_version("desktop-v0.2.0", "0.1.0")


def test_check_for_update_uses_default_repository_when_repo_missing(monkeypatch):
    payload = {
        "tag_name": "desktop-v0.1.0",
        "html_url": f"https://github.com/{DEFAULT_GITHUB_REPOSITORY}/releases/tag/desktop-v0.1.0",
        "assets": [],
    }
    observed = {}

    def fake_get(url, *args, **kwargs):
        observed["url"] = url
        return _FakeResponse(payload)

    monkeypatch.setattr("app.update_service.requests.get", fake_get)

    result = check_for_update(current_version="0.1.0", repository="")

    assert result.status == "up_to_date"
    assert observed["url"].endswith(f"/repos/{DEFAULT_GITHUB_REPOSITORY}/releases/latest")


def test_check_for_update_detects_available_release(monkeypatch):
    payload = {
        "tag_name": "desktop-v0.2.0",
        "html_url": "https://github.com/example/repo/releases/tag/desktop-v0.2.0",
        "assets": [
            {
                "name": "CrownLedgerLocal-0.2.0-windows-x64.zip",
                "browser_download_url": "https://example.invalid/CrownLedgerLocal.zip",
            }
        ],
    }

    monkeypatch.setattr(
        "app.update_service.requests.get",
        lambda *args, **kwargs: _FakeResponse(payload),
    )

    result = check_for_update(
        current_version="0.1.0",
        repository="example/repo",
    )

    assert result.status == "update_available"
    assert result.latest_version == "desktop-v0.2.0"
    assert result.download_url == "https://example.invalid/CrownLedgerLocal.zip"
