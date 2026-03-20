"""Styled card widget — replaces QGroupBox in the Scout tab.

Layout
------
┌ gold accent bar (3 px) ┬─────────────────────────────────────┐
│                         │  TITLE                               │
│                         │ ───────────────────────────────────  │
│                         │  [content — added via body_layout]   │
└─────────────────────────┴─────────────────────────────────────┘

Usage::

    card = StatCard("Activity")
    score_bar = ScoreBar()
    score_bar.animate_to(0.82)
    card.body_layout.addWidget(score_bar)
    card.body_layout.addWidget(QLabel("Last battle: 1d"))
"""
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from desktop.theme import (
    BG_SURFACE,
    BORDER_DARK,
    CARD_RADIUS,
    FONT_BODY,
    FONT_DISPLAY,
    GOLD_DIM,
    GOLD_MID,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

_ACCENT_W = 3   # gold left-bar width in pixels


class StatCard(QFrame):
    """Dark card with gold left accent and bold section title.

    Attributes
    ----------
    body_layout : QVBoxLayout
        Add your content widgets here.
    title_label : QLabel
        The card heading (already styled).
    """

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title.upper()
        self.setMinimumHeight(110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        # ── Outer horizontal layout ────────────────────────────────────────
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Gold accent bar
        accent = QWidget()
        accent.setFixedWidth(_ACCENT_W)
        accent.setObjectName("accentBar")
        accent.setStyleSheet(f"background-color: {GOLD_MID}; border-radius: 2px;")
        outer.addWidget(accent)

        # ── Content area ───────────────────────────────────────────────────
        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content_vbox = QVBoxLayout(content_widget)
        content_vbox.setContentsMargins(14, 10, 14, 12)
        content_vbox.setSpacing(6)

        # Title row
        self.title_label = QLabel(self._title)
        title_font = QFont(FONT_DISPLAY, 11)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {GOLD_DIM};")
        content_vbox.addWidget(self.title_label)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {BORDER_DARK}; border: none;")
        content_vbox.addWidget(sep)

        # Body area — callers populate this
        self.body_layout = QVBoxLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(5)
        content_vbox.addLayout(self.body_layout)

        outer.addWidget(content_widget, 1)

    def add_text(self, text: str) -> QLabel:
        """Convenience: add a plain text label to the body."""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        self.body_layout.addWidget(label)
        return label

    def add_muted(self, text: str) -> QLabel:
        """Convenience: add a muted (secondary) text label."""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        self.body_layout.addWidget(label)
        return label

    # ── Custom painting ────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = CARD_RADIUS
        rect = QRectF(0, 0, self.width(), self.height())

        # Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(BG_SURFACE))
        painter.drawRoundedRect(rect, r, r)

        # Border
        painter.setPen(QPen(QColor(BORDER_DARK), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), r, r)

        painter.end()
