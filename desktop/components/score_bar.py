"""Animated score / progress bar widget.

Shows a 0.0–1.0 value as a filled horizontal bar with colour coding:
  ≥ 0.75  →  green
  ≥ 0.50  →  amber
  < 0.50  →  red

The bar animates from 0 → target value when animate_to() is called.
Use set_value() for an instant (no animation) update.
"""
from __future__ import annotations

import math

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from desktop.theme import (
    AMBER_RISK,
    BG_SURFACE_3,
    FONT_BODY,
    GREEN_ACTIVE,
    RED_INACTIVE,
    SCORE_BAR_H,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

_ANIM_DURATION_MS = 600


def _bar_color(value: float) -> QColor:
    if value >= 0.75:
        return QColor(GREEN_ACTIVE)
    if value >= 0.50:
        return QColor(AMBER_RISK)
    return QColor(RED_INACTIVE)


class ScoreBar(QWidget):
    """Animated horizontal score bar.

    Parameters
    ----------
    value:
        Initial target value (0.0–1.0). The bar displays at this value
        immediately without animation. Call animate_to() to trigger the
        fill animation.
    show_text:
        Whether to draw the numeric label inside the bar.
    parent:
        Optional parent widget.
    """

    def __init__(
        self,
        value: float = 0.0,
        *,
        show_text: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._fill: float = max(0.0, min(1.0, value))
        self._show_text = show_text

        self.setFixedHeight(SCORE_BAR_H)
        self.setMinimumWidth(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._anim = QPropertyAnimation(self, b"fill_value")
        self._anim.setDuration(_ANIM_DURATION_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ── Qt property (required for QPropertyAnimation) ─────────────────────
    def _get_fill(self) -> float:
        return self._fill

    def _set_fill(self, v: float) -> None:
        self._fill = max(0.0, min(1.0, v))
        self.update()

    fill_value = Property(float, _get_fill, _set_fill)

    # ── Public API ────────────────────────────────────────────────────────
    def set_value(self, value: float) -> None:
        """Set value instantly, no animation."""
        self._anim.stop()
        self._set_fill(value)

    def animate_to(self, target: float) -> None:
        """Animate from 0 → target."""
        target = max(0.0, min(1.0, target))
        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(target)
        self._anim.start()

    # ── Painting ──────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        m = 3          # margin
        r = 3.0        # corner radius
        bar_h = h - 2 * m

        track = QRectF(m, m, w - 2 * m, bar_h)

        # Background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(BG_SURFACE_3))
        painter.drawRoundedRect(track, r, r)

        # Filled portion
        fill_w = (w - 2 * m) * self._fill
        if fill_w > 1:
            fill_rect = QRectF(m, m, fill_w, bar_h)
            color = _bar_color(self._fill)

            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.0, color.darker(150))
            grad.setColorAt(0.6, color)
            grad.setColorAt(1.0, color.lighter(115))
            painter.setBrush(grad)
            painter.drawRoundedRect(fill_rect, r, r)

            # Subtle highlight streak
            if fill_w > 16:
                highlight = QColor(255, 255, 255, 22)
                painter.setBrush(highlight)
                painter.setPen(Qt.PenStyle.NoPen)
                streak = QRectF(m + 2, m + 1, fill_w - 4, bar_h * 0.45)
                painter.drawRoundedRect(streak, r, r)

        # Border
        painter.setPen(QPen(QColor(BG_SURFACE_3).lighter(130), 0.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(track.adjusted(0.4, 0.4, -0.4, -0.4), r, r)

        # Numeric label
        if self._show_text:
            if math.isnan(self._fill) or self._fill == 0.0 and not self._anim.state().value:
                txt_color = QColor(TEXT_MUTED)
            else:
                txt_color = QColor(TEXT_PRIMARY)

            font = QFont(FONT_BODY, 9)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(txt_color))
            painter.drawText(track.toRect(), Qt.AlignmentFlag.AlignCenter, f"{self._fill:.2f}")

        painter.end()
