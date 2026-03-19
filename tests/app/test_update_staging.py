from __future__ import annotations

import io
import zipfile

from app.update_service import stage_update_from_release


class _FakeStreamingResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size: int = 1024):
        for start in range(0, len(self.payload), chunk_size):
            yield self.payload[start : start + chunk_size]


def test_stage_update_from_release_extracts_archive(monkeypatch, tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("CrownLedgerLocal.exe", "exe-bytes")
        archive.writestr("_internal/test.txt", "hello")
    payload = buffer.getvalue()

    monkeypatch.setattr(
        "app.update_service.requests.get",
        lambda *args, **kwargs: _FakeStreamingResponse(payload),
    )

    staged = stage_update_from_release(
        download_url="https://example.invalid/update.zip",
        version="desktop-v0.2.0",
        base_dir=tmp_path,
    )

    assert staged.version == "0.2.0"
    assert staged.archive_path.exists()
    assert (staged.app_dir / "CrownLedgerLocal.exe").exists()
    assert (staged.app_dir / "_internal" / "test.txt").exists()
