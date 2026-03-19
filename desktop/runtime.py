from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

from app.config import get_app_data_dir


UPDATER_EXE_NAME = "CrownLedgerUpdater.exe"
MAIN_EXE_NAME = "CrownLedgerLocal.exe"


def is_frozen_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def application_dir() -> Path:
    if is_frozen_app():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def current_executable_path() -> Path:
    if is_frozen_app():
        return Path(sys.executable).resolve()
    return Path(sys.executable).resolve()


def updater_path() -> Path:
    if is_frozen_app():
        return application_dir() / UPDATER_EXE_NAME
    return Path(__file__).resolve().parent / "updater.py"


def can_apply_inplace_update() -> bool:
    return is_frozen_app() and updater_path().exists()


def updater_runtime_dir() -> Path:
    path = get_app_data_dir() / "runtime-updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def launch_staged_update(staged_app_dir: str | Path) -> None:
    staged_dir = Path(staged_app_dir).resolve()
    if not can_apply_inplace_update():
        raise RuntimeError("In-place updates are only supported from a packaged app build.")

    source_updater = updater_path()
    temp_updater = updater_runtime_dir() / f"CrownLedgerUpdater-{int(time.time())}.exe"
    shutil.copy2(source_updater, temp_updater)

    launch_path = application_dir() / MAIN_EXE_NAME
    command = [
        str(temp_updater),
        "--source-dir",
        str(staged_dir),
        "--target-dir",
        str(application_dir()),
        "--launch-path",
        str(launch_path),
    ]
    subprocess.Popen(command, close_fds=True)
