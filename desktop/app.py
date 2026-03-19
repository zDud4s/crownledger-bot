from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from desktop.version import APP_NAME, __version__
from desktop.window import CrownLedgerMainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    return app


def run(argv: list[str] | None = None) -> int:
    app = create_application(argv)
    window = CrownLedgerMainWindow()
    window.show()
    return app.exec()
