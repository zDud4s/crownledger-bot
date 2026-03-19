from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from desktop.clan_health_widget import ClanHealthWidget
from desktop.player_scout_widget import PlayerScoutWidget
from desktop.settings_widget import SettingsWidget
from desktop.war_rank_widget import WarRankWidget
from desktop.version import APP_NAME, __version__


def _build_placeholder_tab(title: str, subtitle: str) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(8)

    heading = QLabel(title)
    heading.setStyleSheet("font-size: 18px; font-weight: 600;")

    body = QLabel(subtitle)
    body.setWordWrap(True)
    body.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    layout.addWidget(heading)
    layout.addWidget(body)
    layout.addStretch(1)
    return container


class CrownLedgerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.resize(1080, 720)
        self._build_ui()

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(
            ClanHealthWidget(),
            "Clan Health",
        )
        tabs.addTab(
            WarRankWidget(),
            "War Rank",
        )
        tabs.addTab(
            PlayerScoutWidget(),
            "Scout",
        )
        tabs.addTab(
            SettingsWidget(),
            "Settings",
        )
        self.setCentralWidget(tabs)
        self.statusBar().showMessage(f"{APP_NAME} {__version__}  |  desktop shell ready")
