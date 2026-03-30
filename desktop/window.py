from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from desktop.clan_health_widget import ClanHealthWidget
from desktop.player_scout_widget import PlayerScoutWidget
from desktop.settings_widget import SettingsWidget
from desktop.theme import (
    BG_DEEP,
    BG_SURFACE,
    BORDER_DARK,
    FONT_BODY,
    FONT_DISPLAY,
    GOLD_BRIGHT,
    GOLD_DIM,
    GOLD_MID,
    TEXT_MUTED,
)
from desktop.version import APP_NAME, __version__
from desktop.war_rank_widget import WarRankWidget


class _HeaderBar(QWidget):
    """Dark header strip with crown glyph, app name and version."""

    _HEIGHT = 56

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self._HEIGHT)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(10)

        # Crown glyph
        crown = QLabel("♛")
        crown_font = QFont("Segoe UI Symbol", 22)
        crown.setFont(crown_font)
        crown.setStyleSheet(f"color: {GOLD_MID};")
        layout.addWidget(crown)

        # App name
        name_label = QLabel(APP_NAME.upper())
        name_font = QFont(FONT_DISPLAY, 17)
        name_font.setBold(True)
        name_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.5)
        name_label.setFont(name_font)
        name_label.setStyleSheet(f"color: {GOLD_BRIGHT};")
        layout.addWidget(name_label)

        layout.addStretch(1)

        # Version badge
        ver_label = QLabel(f"v{__version__}")
        ver_font = QFont(FONT_BODY, 10)
        ver_label.setFont(ver_font)
        ver_label.setStyleSheet(f"color: {TEXT_MUTED};")
        layout.addWidget(ver_label)

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        w, h = self.width(), self.height()

        # Gradient background: surface on left, fading to deep on right
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(BG_SURFACE))
        grad.setColorAt(0.5, QColor(BG_SURFACE))
        grad.setColorAt(1.0, QColor(BG_DEEP))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawRect(0, 0, w, h)

        # Subtle gold bottom border
        painter.setPen(QPen(QColor(BORDER_DARK), 1.0))
        painter.drawLine(0, h - 1, w, h - 1)

        painter.end()


class _AnimatedTabBar(QTabBar):
    """QTabBar with a sliding gold indicator that animates between tabs."""

    _INDICATOR_H = 3
    _INDICATOR_MARGIN = 10

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._indicator = QWidget(self)
        self._indicator.setFixedHeight(self._INDICATOR_H)
        self._indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._indicator.setStyleSheet(
            f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 {GOLD_DIM}, stop:0.5 {GOLD_BRIGHT}, stop:1 {GOLD_MID});"
            f" border-radius: 1px;"
        )
        self._indicator.raise_()
        self._indicator.hide()

        self._anim = QPropertyAnimation(self._indicator, b"geometry")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.currentChanged.connect(self._slide_to)

    def _target_rect(self, index: int) -> QRect:
        rect = self.tabRect(index)
        m = self._INDICATOR_MARGIN
        return QRect(
            rect.x() + m,
            self.height() - self._INDICATOR_H,
            max(1, rect.width() - 2 * m),
            self._INDICATOR_H,
        )

    def _slide_to(self, index: int) -> None:
        if index < 0:
            return
        target = self._target_rect(index)
        if not self._indicator.isVisible():
            self._indicator.setGeometry(target)
            self._indicator.show()
            return
        self._anim.stop()
        self._anim.setStartValue(self._indicator.geometry())
        self._anim.setEndValue(target)
        self._anim.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        idx = self.currentIndex()
        if idx >= 0:
            self._indicator.setGeometry(self._target_rect(idx))
            self._indicator.show()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        idx = self.currentIndex()
        if idx >= 0:
            self._indicator.setGeometry(self._target_rect(idx))


class CrownLedgerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  {__version__}")
        self.resize(1100, 740)
        self.setMinimumSize(800, 560)
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Root container ─────────────────────────────────────────────────
        root_widget = QWidget()
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header bar ─────────────────────────────────────────────────────
        root_layout.addWidget(_HeaderBar())

        # ── Tab widget ─────────────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setDocumentMode(True)   # removes extra frame around tab bar
        tabs.setTabBar(_AnimatedTabBar())

        tabs.addTab(ClanHealthWidget(), "  Clan Health  ")
        tabs.addTab(WarRankWidget(),    "  War Rank  ")
        tabs.addTab(PlayerScoutWidget(), "  Scout  ")
        tabs.addTab(SettingsWidget(),   "  Settings  ")

        # Trigger initial indicator placement after tabs are added
        from PySide6.QtCore import QTimer
        tab_bar = tabs.tabBar()
        QTimer.singleShot(0, lambda: tab_bar._slide_to(tabs.currentIndex()))

        root_layout.addWidget(tabs, 1)

        self.setCentralWidget(root_widget)
        self.statusBar().showMessage(
            f"{APP_NAME}  {__version__}   |   desktop shell ready"
        )
