from __future__ import annotations

import sys

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect

from desktop.assets import AssetManager
from desktop.theme import APP_QSS
from desktop.version import APP_NAME, __version__
from desktop.window import CrownLedgerMainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setStyleSheet(APP_QSS)
    # Ensure game asset directories exist for future image drops
    AssetManager.ensure_dirs()
    return app


def run(argv: list[str] | None = None) -> int:
    app = create_application(argv)

    from desktop.playwright_setup import PlaywrightSetupDialog, chromium_is_ready
    if not chromium_is_ready():
        PlaywrightSetupDialog().exec()

    window = CrownLedgerMainWindow()
    window.show()

    # Window fade-in on launch
    effect = QGraphicsOpacityEffect(window)
    window.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity", window)
    anim.setDuration(350)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.start()

    return app.exec()
