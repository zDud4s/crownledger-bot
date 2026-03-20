"""Tier badge pill widget.

Renders a small rounded-rectangle label whose colour reflects the tier:
  ClanHealth  →  "inactive" | "at_risk" | "active"
  WarRank     →  "Low"      | "Solid"   | "Strong"
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from desktop.theme import FONT_BODY, TEXT_MUTED, TIER_BADGE_H, TIER_BADGE_W, TIER_CONFIGS


class TierBadge(QWidget):
    """Small pill badge for activity or war tier."""

    def __init__(self, tier_key: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tier = tier_key
        self.setFixedSize(TIER_BADGE_W, TIER_BADGE_H)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setToolTip(tier_key)

    def set_tier(self, tier_key: str) -> None:
        self._tier = tier_key
        self.setToolTip(tier_key)
        self.update()

    # ── Painting ──────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:  # noqa: N802
        cfg = TIER_CONFIGS.get(self._tier)
        if cfg is None:
            return

        text_color, bg_color, label = cfg

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        m = 1.5
        rect = QRectF(m, m, w - 2 * m, h - 2 * m)
        radius = rect.height() / 2  # full pill

        # Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(bg_color))
        painter.drawRoundedRect(rect, radius, radius)

        # Border
        border = QColor(text_color)
        border.setAlpha(120)
        painter.setPen(QPen(border, 0.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.4, 0.4, -0.4, -0.4), radius, radius)

        # Text
        font = QFont(FONT_BODY, 8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(text_color))
        painter.drawText(rect.toRect(), Qt.AlignmentFlag.AlignCenter, label)

        painter.end()
