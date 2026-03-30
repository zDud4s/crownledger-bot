"""CrownLedger Local — Design Tokens & Application Stylesheet.

All visual constants live here. Import tokens into components;
apply APP_QSS once via QApplication.setStyleSheet().

Image assets are intentionally not referenced here — see assets.py.
"""
from __future__ import annotations

# ── Colours ───────────────────────────────────────────────────────────────────

# Backgrounds
BG_DEEP      = "#08091A"
BG_SURFACE   = "#0F1228"
BG_SURFACE_2 = "#171B34"
BG_SURFACE_3 = "#1E2240"

# Borders
BORDER_DARK        = "#1E2245"
BORDER_GOLD        = "#3D3010"
BORDER_GOLD_BRIGHT = "#C9A227"

# Gold system (primary brand — Clash Royale gold)
GOLD_BRIGHT = "#F0C040"
GOLD_MID    = "#C9A227"
GOLD_DIM    = "#8A6B1A"
GOLD_MUTED  = "#3D3010"

# Status
GREEN_ACTIVE = "#2ECC71"
GREEN_DIM    = "#122B1F"
AMBER_RISK   = "#F39C12"
AMBER_DIM    = "#2D1E08"
RED_INACTIVE = "#E74C3C"
RED_DIM      = "#2A100E"

# Accent
BLUE_ACCENT = "#4A6FF5"

# Text
TEXT_PRIMARY   = "#E8D5A3"
TEXT_SECONDARY = "#9A8A6A"
TEXT_MUTED     = "#5A5040"
TEXT_WHITE     = "#F5F0E8"

# ── Fonts ─────────────────────────────────────────────────────────────────────
# System fonts, no download required. Swap for Cinzel/Nunito later
# via QFontDatabase.addApplicationFont() in app.py.

FONT_DISPLAY = "Palatino Linotype"  # → Cinzel (medieval serif)
FONT_BODY    = "Segoe UI"
FONT_MONO    = "Consolas"

# ── Sizing ────────────────────────────────────────────────────────────────────
ROW_HEIGHT      = 36
HEADER_HEIGHT   = 58
SCORE_BAR_H     = 26
TIER_BADGE_W    = 78
TIER_BADGE_H    = 22
CARD_RADIUS     = 12
INPUT_RADIUS    = 8
BUTTON_RADIUS   = 8

# ── Tier config (used by TierBadge) ──────────────────────────────────────────
TIER_CONFIGS: dict[str, tuple[str, str, str]] = {
    # (text_colour, bg_colour, label)
    "inactive": (RED_INACTIVE,  RED_DIM,   "INACTIVE"),
    "at_risk":  (AMBER_RISK,   AMBER_DIM,  "AT RISK"),
    "active":   (GREEN_ACTIVE, GREEN_DIM,  "ACTIVE"),
    "Strong":   (GREEN_ACTIVE, GREEN_DIM,  "STRONG"),
    "Solid":    (AMBER_RISK,   AMBER_DIM,  "SOLID"),
    "Low":      (RED_INACTIVE,  RED_DIM,   "LOW"),
}

# ── Candidate verdict config ──────────────────────────────────────────────────
def candidate_verdict(score: float) -> tuple[str, str]:
    """Returns (label, colour) for a candidate score."""
    if score >= 0.75:
        return "EXCELLENT CANDIDATE", GREEN_ACTIVE
    if score >= 0.55:
        return "GOOD OPTION", GOLD_BRIGHT
    if score >= 0.35:
        return "CONSIDER", AMBER_RISK
    return "NOT RECOMMENDED", RED_INACTIVE

# ── Score bar colour ──────────────────────────────────────────────────────────
def score_colour(value: float) -> str:
    if value >= 0.75:
        return GREEN_ACTIVE
    if value >= 0.50:
        return AMBER_RISK
    return RED_INACTIVE

# ── Application QSS ───────────────────────────────────────────────────────────
# Qt QSS is a subset of CSS. Unsupported: transitions, box-shadow, calc(),
# CSS variables, letter-spacing, text-transform, :nth-child().

APP_QSS = f"""
/* ── Base ───────────────────────────────────────────────────────────────── */
QMainWindow, QWidget {{
    background-color: {BG_DEEP};
    color: {TEXT_PRIMARY};
    font-family: "{FONT_BODY}";
    font-size: 13px;
}}

/* ── Tab Widget ─────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background-color: {BG_DEEP};
    border-top: 1px solid {BORDER_DARK};
}}

QTabBar {{
    background-color: {BG_DEEP};
}}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_MUTED};
    font-family: "{FONT_DISPLAY}";
    font-size: 13px;
    font-weight: bold;
    padding: 10px 24px;
    border: none;
    border-bottom: 3px solid transparent;
    min-width: 110px;
}}

QTabBar::tab:selected {{
    color: {GOLD_MID};
    background-color: {BG_SURFACE};
}}

QTabBar::tab:hover:!selected {{
    color: {TEXT_SECONDARY};
    background-color: {BG_SURFACE};
}}

/* ── Inputs ─────────────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_DARK};
    border-radius: {INPUT_RADIUS}px;
    color: {TEXT_PRIMARY};
    padding: 6px 10px;
    font-family: "{FONT_BODY}";
    font-size: 13px;
    selection-background-color: {GOLD_MUTED};
    selection-color: {GOLD_BRIGHT};
    min-height: 30px;
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {GOLD_MID};
    background-color: {BG_SURFACE_2};
}}

QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
    color: {TEXT_MUTED};
    background-color: {BG_SURFACE};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {BG_SURFACE_2};
    border: none;
    width: 20px;
    border-radius: 2px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {GOLD_MUTED};
}}

QSpinBox::up-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {GOLD_MID};
    width: 0;
    height: 0;
}}

QSpinBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {GOLD_MID};
    width: 0;
    height: 0;
}}

QComboBox::drop-down {{
    border: none;
    width: 28px;
    background-color: transparent;
}}

QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {GOLD_MID};
}}

QComboBox QAbstractItemView {{
    background-color: {BG_SURFACE_2};
    border: 1px solid {GOLD_MID};
    color: {TEXT_PRIMARY};
    selection-background-color: {GOLD_MUTED};
    selection-color: {GOLD_BRIGHT};
    padding: 4px;
    outline: none;
}}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #D4A82A, stop:1 #A8831C);
    color: {BG_DEEP};
    border: 1px solid {GOLD_BRIGHT};
    border-radius: {BUTTON_RADIUS}px;
    font-family: "{FONT_BODY}";
    font-size: 13px;
    font-weight: bold;
    padding: 8px 22px;
    min-width: 110px;
    min-height: 34px;
}}

QPushButton:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {GOLD_BRIGHT}, stop:1 {GOLD_MID});
    border: 1px solid {GOLD_BRIGHT};
}}

QPushButton:pressed {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #A8831C, stop:1 #8A6B15);
    padding-top: 10px;
    padding-bottom: 6px;
}}

QPushButton:disabled {{
    background-color: {BG_SURFACE_2};
    border: 1px solid {BORDER_DARK};
    color: {TEXT_MUTED};
}}

/* Secondary button variant — set objectName="btnSecondary" */
QPushButton#btnSecondary {{
    background-color: transparent;
    border: 1px solid {GOLD_DIM};
    color: {GOLD_MID};
}}

QPushButton#btnSecondary:hover {{
    background-color: {GOLD_MUTED};
    border: 1px solid {GOLD_MID};
    color: {GOLD_BRIGHT};
}}

QPushButton#btnSecondary:pressed {{
    background-color: {GOLD_MUTED};
    padding-top: 10px;
    padding-bottom: 6px;
}}

QPushButton#btnSecondary:disabled {{
    color: {TEXT_MUTED};
    border: 1px solid {BORDER_DARK};
}}

/* ── Tables ──────────────────────────────────────────────────────────────── */
QTableWidget {{
    background-color: {BG_DEEP};
    alternate-background-color: {BG_SURFACE};
    gridline-color: {BORDER_DARK};
    border: 1px solid {BORDER_DARK};
    border-radius: 10px;
    color: {TEXT_PRIMARY};
    font-size: 13px;
    selection-background-color: {BG_SURFACE_3};
    selection-color: {GOLD_BRIGHT};
    outline: none;
}}

QTableWidget::item {{
    padding: 4px 10px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {BG_SURFACE_3};
    color: {GOLD_BRIGHT};
}}

QHeaderView {{
    background-color: {BG_SURFACE};
    border: none;
}}

QHeaderView::section {{
    background-color: {BG_SURFACE};
    color: {GOLD_MID};
    font-family: "{FONT_BODY}";
    font-size: 11px;
    font-weight: bold;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid {GOLD_MUTED};
    border-right: 1px solid {BORDER_DARK};
}}

QHeaderView::section:last {{
    border-right: none;
}}

QHeaderView::section:hover {{
    background-color: {BG_SURFACE_2};
    color: {GOLD_MID};
}}

/* ── Scrollbars ──────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: {BG_DEEP};
    width: 8px;
    border: none;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {BORDER_DARK};
    border-radius: 4px;
    min-height: 24px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {GOLD_DIM};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    border: none;
}}

QScrollBar:horizontal {{
    background-color: {BG_DEEP};
    height: 8px;
    border: none;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {BORDER_DARK};
    border-radius: 4px;
    min-width: 24px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {GOLD_DIM};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    border: none;
}}

/* ── Checkbox ────────────────────────────────────────────────────────────── */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER_DARK};
    border-radius: 3px;
    background-color: {BG_SURFACE};
}}

QCheckBox::indicator:checked {{
    background-color: {GOLD_MID};
    border: 1px solid {GOLD_BRIGHT};
}}

QCheckBox::indicator:hover {{
    border: 1px solid {GOLD_MID};
}}

/* ── Labels ──────────────────────────────────────────────────────────────── */
QLabel {{
    color: {TEXT_PRIMARY};
    background-color: transparent;
}}

/* ── Status Bar ──────────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: #050610;
    color: {TEXT_MUTED};
    border-top: 1px solid {BORDER_DARK};
    font-size: 11px;
    padding: 2px 8px;
}}

QStatusBar::item {{
    border: none;
}}

/* ── Group Box (fallback for any remaining QGroupBox uses) ───────────────── */
QGroupBox {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_DARK};
    border-radius: {CARD_RADIUS}px;
    padding: 20px 14px 14px 14px;
    margin-top: 10px;
    font-family: "{FONT_DISPLAY}";
    font-size: 12px;
    font-weight: bold;
    color: {GOLD_MID};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 0px;
    color: {GOLD_MID};
    background-color: {BG_SURFACE};
    padding: 0 4px;
}}

/* ── Scroll Area ─────────────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ── Message / Dialog ────────────────────────────────────────────────────── */
QMessageBox {{
    background-color: {BG_SURFACE};
    color: {TEXT_PRIMARY};
}}

QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
}}

QDialog {{
    background-color: {BG_SURFACE};
}}

/* ── Tooltip ─────────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {BG_SURFACE_2};
    border: 1px solid {GOLD_MID};
    color: {TEXT_PRIMARY};
    padding: 5px 9px;
    font-size: 12px;
    border-radius: 8px;
}}
"""
