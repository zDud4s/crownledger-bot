"""Loading spinner widget.

Renders 12 dots arranged in a clock-face pattern, fading from dim to bright
in the direction of rotation — the classic "chase" spinner effect, in gold.

Usage::

    spinner = LoadingSpinner(size=36, parent=self)
    spinner.start()   # show and begin rotating
    # ... async work ...
    spinner.stop()    # hide
"""
from __future__ import annotations

import math

from PySide6.QtCore import QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

from desktop.theme import GOLD_BRIGHT, GOLD_MID

_DOTS    = 12
_FPS     = 33          # ~30 fps rotation
_DEG_STEP = 8          # degrees per tick


class LoadingSpinner(QWidget):
    """Rotating gold spinner.

    Parameters
    ----------
    size : int
        Fixed widget size in pixels (square).
    parent : QWidget | None
        Optional parent.
    """

    def __init__(self, size: int = 36, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle: float = 0.0
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.hide()

        self._timer = QTimer(self)
        self._timer.setInterval(_FPS)
        self._timer.timeout.connect(self._tick)

    # ── Public API ────────────────────────────────────────────────────────
    def start(self) -> None:
        """Show spinner and begin animation."""
        self._angle = 0.0
        self.show()
        self._timer.start()

    def stop(self) -> None:
        """Stop animation and hide."""
        self._timer.stop()
        self.hide()

    # ── Internal ──────────────────────────────────────────────────────────
    def _tick(self) -> None:
        self._angle = (self._angle + _DEG_STEP) % 360
        self.update()

    # ── Painting ──────────────────────────────────────────────────────────
    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        orbit_r = min(w, h) / 2.0 - 5

        for i in range(_DOTS):
            # Angle offset per dot
            angle_rad = math.radians(i * (360 / _DOTS) + self._angle)
            dx = orbit_r * math.cos(angle_rad)
            dy = orbit_r * math.sin(angle_rad)

            # Alpha increases towards the "head" (last dot, index = _DOTS-1)
            alpha = int(255 * (i + 1) / _DOTS)

            # Dot size grows towards the head
            dot_r = 1.5 + (i / (_DOTS - 1)) * 2.5

            base_color = QColor(GOLD_BRIGHT if i >= _DOTS - 2 else GOLD_MID)
            base_color.setAlpha(alpha)
            painter.setBrush(base_color)
            painter.drawEllipse(
                QRectF(cx + dx - dot_r, cy + dy - dot_r, dot_r * 2, dot_r * 2)
            )

        painter.end()
