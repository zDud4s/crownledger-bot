from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from desktop.theme import (
    BG_SURFACE,
    FONT_BODY,
    FONT_DISPLAY,
    GOLD_BRIGHT,
    GOLD_MID,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def chromium_is_ready() -> bool:
    """Return True if the Playwright Chromium browser binary exists on disk."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


def _install_chromium() -> bool:
    """
    Run `playwright install chromium` via Playwright's bundled Node driver.
    Works in both dev and PyInstaller frozen builds.
    Returns True on success.
    """
    try:
        from playwright._impl._driver import compute_driver_executable

        node_exe, cli_js = compute_driver_executable()
        result = subprocess.run(
            [str(node_exe), str(cli_js), "install", "chromium"],
            capture_output=True,
            timeout=300,  # 5 minutes max
        )
        return result.returncode == 0
    except Exception:
        return False


class _InstallWorker(QThread):
    done = Signal(bool)  # True = success

    def run(self) -> None:
        self.done.emit(_install_chromium())


class PlaywrightSetupDialog(QDialog):
    """
    Shown on first launch when the Chromium browser is not installed.
    Runs the install in a background thread and closes when done.
    If install fails, shows a skip button so the app can still open.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("First-time Setup")
        self.setFixedSize(420, 160)
        self.setStyleSheet(f"background: {BG_SURFACE}; color: {TEXT_PRIMARY};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel("Installing browser component")
        title.setFont(QFont(FONT_DISPLAY, 13))
        title.setStyleSheet(f"color: {GOLD_BRIGHT};")
        layout.addWidget(title)

        self._status = QLabel("Downloading Chromium (~150 MB), please wait…")
        self._status.setFont(QFont(FONT_BODY, 9))
        self._status.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)  # indeterminate
        self._bar.setFixedHeight(6)
        self._bar.setTextVisible(False)
        self._bar.setStyleSheet(
            f"QProgressBar {{ border: none; background: #1E2245; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background: {GOLD_MID}; border-radius: 3px; }}"
        )
        layout.addWidget(self._bar)

        self._skip_btn = QPushButton("Skip (war history will be unavailable)")
        self._skip_btn.setFont(QFont(FONT_BODY, 9))
        self._skip_btn.hide()
        self._skip_btn.clicked.connect(self.accept)
        layout.addWidget(self._skip_btn)

        # Block closing via the X button while installing
        self.setWindowFlag(self.windowFlags().__class__.WindowCloseButtonHint, False)

        self._worker = _InstallWorker(self)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success: bool) -> None:
        self._bar.setRange(0, 1)
        self._bar.setValue(1)
        if success:
            self._status.setText("Browser installed successfully.")
            self.accept()
        else:
            self._status.setText(
                "Installation failed. War history will be unavailable this session."
            )
            self._skip_btn.show()
            self.setWindowFlag(
                self.windowFlags().__class__.WindowCloseButtonHint, True
            )
