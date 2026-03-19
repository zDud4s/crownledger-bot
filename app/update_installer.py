from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path


def replace_directory_contents(source_dir: str | Path, target_dir: str | Path) -> None:
    source = Path(source_dir)
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    for child in target.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    for child in source.iterdir():
        destination = target / child.name
        if child.is_dir():
            shutil.copytree(child, destination)
        else:
            shutil.copy2(child, destination)


def wait_for_directory_update(source_dir: str | Path, target_dir: str | Path, retries: int = 20, delay_s: float = 1.0) -> None:
    last_error: Exception | None = None
    for _ in range(retries):
        try:
            replace_directory_contents(source_dir, target_dir)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(delay_s)

    if last_error is not None:
        raise last_error


def launch_updated_app(launch_path: str | Path, python_exe: str | Path | None = None) -> None:
    if python_exe is not None:
        subprocess.Popen([str(python_exe), str(launch_path)], close_fds=True)
    else:
        subprocess.Popen([str(launch_path)], close_fds=True)
