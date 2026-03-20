"""CrownLedger Local — Asset Manager.

Single source of truth for all image/icon paths.

To swap a placeholder for a real game image:
  1. Drop the real file into  desktop/assets/game/<category>/
  2. Name it by the identifier used below (clan tag, player tag, etc.).
     AssetManager will automatically prefer the real image.

Placeholder SVGs are generated inline as bytes — no external files required
until the real game images are provided.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter

# ── Directory layout ──────────────────────────────────────────────────────────
_HERE      = Path(__file__).parent
ASSETS_DIR = _HERE / "assets"
GAME_DIR   = ASSETS_DIR / "game"
PH_DIR     = ASSETS_DIR / "placeholders"   # static placeholder files (optional)
FONTS_DIR  = ASSETS_DIR / "fonts"          # TTF files for QFontDatabase


# ── SVG placeholder templates ─────────────────────────────────────────────────
# These are rendered at runtime — no PNG files needed.

_CLAN_BADGE_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="8" fill="#0F1228"/>
  <rect x="1" y="1" width="62" height="62" rx="7" fill="none"
        stroke="#3D3010" stroke-width="1.5"/>
  <!-- Crown shape -->
  <polygon points="12,44 12,26 20,33 32,18 44,33 52,26 52,44"
           fill="none" stroke="#C9A227" stroke-width="2.5"
           stroke-linejoin="round"/>
  <rect x="10" y="44" width="44" height="6" rx="2"
        fill="#C9A227" opacity="0.85"/>
  <!-- Crown gems -->
  <circle cx="32" cy="21" r="3.5" fill="#F0C040"/>
  <circle cx="16" cy="31" r="2.5" fill="#C9A227"/>
  <circle cx="48" cy="31" r="2.5" fill="#C9A227"/>
</svg>"""

_PLAYER_AVATAR_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
  <rect width="48" height="48" rx="6" fill="#0F1228"/>
  <rect x="0.75" y="0.75" width="46.5" height="46.5" rx="5.5" fill="none"
        stroke="#1E2245" stroke-width="1.5"/>
  <!-- Helmet silhouette -->
  <ellipse cx="24" cy="18" rx="10" ry="11" fill="#1E2240"/>
  <path d="M14,28 Q14,38 24,40 Q34,38 34,28" fill="#1E2240"/>
  <rect x="18" y="27" width="12" height="5" rx="2" fill="#2A2E55"/>
  <!-- Face-plate bars -->
  <rect x="19" y="29" width="10" height="1.5" rx="0.75" fill="#C9A227" opacity="0.6"/>
  <rect x="19" y="32" width="10" height="1.5" rx="0.75" fill="#C9A227" opacity="0.6"/>
</svg>"""

_CARD_FRAME_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 72">
  <rect width="52" height="72" rx="6" fill="#0A0C1A"/>
  <rect x="1" y="1" width="50" height="70" rx="5" fill="none"
        stroke="#3D3010" stroke-width="2"/>
  <rect x="4" y="4" width="44" height="64" rx="4" fill="none"
        stroke="#1E2245" stroke-width="1"/>
  <!-- Crown mini watermark -->
  <polygon points="20,58 20,50 24,53 26,47 28,53 32,50 32,58"
           fill="none" stroke="#3D3010" stroke-width="1.5"
           stroke-linejoin="round"/>
</svg>"""


def _svg_to_pixmap(svg: str, w: int, h: int) -> QPixmap:
    """Render an SVG string to a QPixmap at the given size."""
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(w, h)
    pixmap.fill(0x00000000)  # transparent
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


# ── AssetManager ──────────────────────────────────────────────────────────────

class AssetManager:
    """Resolves image paths, preferring real game images over placeholders.

    Usage::

        pm = AssetManager.clan_badge("#2PP")   # QPixmap, 48x48
        scout_tab.badge_label.setPixmap(pm)

    Drop real game images into desktop/assets/game/:
        game/clans/<tag>.png        → clan badge
        game/players/<tag>.png      → player avatar
        game/cards/<card_id>.png    → card image

    Tags should be stored without the leading '#', lowercased.
    """

    # ── Clan badge ────────────────────────────────────────────────────────
    @classmethod
    def clan_badge(cls, clan_tag: str = "", size: int = 48) -> QPixmap:
        tag = clan_tag.lstrip("#").upper()
        real = GAME_DIR / "clans" / f"{tag}.png"
        if real.exists():
            pm = QPixmap(str(real))
            return pm.scaled(size, size)
        return _svg_to_pixmap(_CLAN_BADGE_SVG, size, size)

    # ── Player avatar ─────────────────────────────────────────────────────
    @classmethod
    def player_avatar(cls, player_tag: str = "", size: int = 48) -> QPixmap:
        tag = player_tag.lstrip("#").upper()
        real = GAME_DIR / "players" / f"{tag}.png"
        if real.exists():
            pm = QPixmap(str(real))
            return pm.scaled(size, size)
        return _svg_to_pixmap(_PLAYER_AVATAR_SVG, size, size)

    # ── Card frame ────────────────────────────────────────────────────────
    @classmethod
    def card_frame(cls, card_id: str = "", w: int = 52, h: int = 72) -> QPixmap:
        real = GAME_DIR / "cards" / f"{card_id}.png"
        if real.exists():
            pm = QPixmap(str(real))
            return pm.scaled(w, h)
        return _svg_to_pixmap(_CARD_FRAME_SVG, w, h)

    # ── Arena background ──────────────────────────────────────────────────
    @classmethod
    def arena_background(cls, arena_id: str = "") -> QPixmap | None:
        """Returns the arena background pixmap, or None if not available."""
        real = GAME_DIR / "arenas" / f"{arena_id}.png"
        if real.exists():
            return QPixmap(str(real))
        return None

    # ── Ensure game subdirectories exist ──────────────────────────────────
    @classmethod
    def ensure_dirs(cls) -> None:
        for sub in ("clans", "players", "cards", "arenas"):
            (GAME_DIR / sub).mkdir(parents=True, exist_ok=True)
