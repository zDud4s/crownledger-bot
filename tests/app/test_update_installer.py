from __future__ import annotations

from app.update_installer import replace_directory_contents


def test_replace_directory_contents_overwrites_and_removes_stale_files(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()

    (source / "new.txt").write_text("new", encoding="utf-8")
    (target / "old.txt").write_text("old", encoding="utf-8")

    replace_directory_contents(source, target)

    assert (target / "new.txt").read_text(encoding="utf-8") == "new"
    assert not (target / "old.txt").exists()
