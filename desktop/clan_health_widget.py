from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import load_local_settings, save_local_settings
from app.input_normalizers import normalize_clan_tag
from app.presenters.clan_health_presenter import ClanHealthViewModel, present_clan_health
from app.services.clan_service import fetch_players_with_battles
from app.use_cases.clan_health import compute_clan_health
from desktop.components import LoadingSpinner, ScoreBar, TierBadge
from desktop.theme import (
    AMBER_DIM,
    AMBER_RISK,
    BG_SURFACE,
    BORDER_DARK,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_MONO,
    GOLD_BRIGHT,
    GOLD_MID,
    GREEN_ACTIVE,
    GREEN_DIM,
    RED_DIM,
    RED_INACTIVE,
    ROW_HEIGHT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

# Tier row tints — subtle dark backgrounds
_ROW_TINTS = {
    "inactive": QColor(RED_DIM),
    "at_risk":  QColor(AMBER_DIM),
    "active":   QColor(GREEN_DIM),
}

# Trend glyph → foreground colour
_TREND_COLORS = {
    "↗": GREEN_ACTIVE,
    "→": TEXT_MUTED,
    "↘": RED_INACTIVE,
    "·": TEXT_MUTED,
}


def _form_row(label_text: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(130)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    return row


class _ClanHealthWorker(QObject):
    finished = Signal(object)

    def __init__(self, clan_tag: str, show_active: bool) -> None:
        super().__init__()
        self.clan_tag = clan_tag
        self.show_active = show_active

    def run(self) -> None:
        try:
            players = fetch_players_with_battles(self.clan_tag)
            if not players:
                self.finished.emit(("empty", self.clan_tag))
                return
            report = compute_clan_health(self.clan_tag, players)
            view_model = present_clan_health(report, self.show_active)
            self.finished.emit(("success", view_model))
        except Exception as exc:
            self.finished.emit(("error", str(exc)))


class ClanHealthWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker_thread: QThread | None = None
        self._worker: _ClanHealthWorker | None = None
        self._build_ui()
        self._load_defaults()

    # ── UI construction ───────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 16)
        root.setSpacing(12)

        # Title
        title = QLabel("Clan Health")
        title_font = QFont(FONT_DISPLAY, 18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {GOLD_BRIGHT};")
        root.addWidget(title)

        # Subtitle / description
        subtitle = QLabel("Identify inactive members and at-risk players across your clan.")
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        root.addWidget(subtitle)

        # ── Controls row ──────────────────────────────────────────────────
        controls = QHBoxLayout()
        controls.setSpacing(16)

        self.clan_tag_input = QLineEdit()
        self.clan_tag_input.setPlaceholderText("#CLANTAG")
        self.clan_tag_input.returnPressed.connect(self.run_analysis)

        self.show_active_checkbox = QCheckBox("Include active players")
        self.show_active_checkbox.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        self.run_button = QPushButton("Analyze Clan")
        self.run_button.clicked.connect(self.run_analysis)

        controls.addLayout(_form_row("Clan tag", self.clan_tag_input))
        controls.addWidget(self.show_active_checkbox)
        controls.addStretch(1)
        controls.addWidget(self.run_button)
        root.addLayout(controls)

        # ── Summary + spinner row ─────────────────────────────────────────
        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        self.summary_label = QLabel("Enter a clan tag to analyse clan health.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.summary_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px;"
            f"padding: 6px 10px;"
            f"background-color: {BG_SURFACE};"
            f"border: 1px solid {BORDER_DARK};"
            f"border-left: 3px solid {GOLD_MID};"
            f"border-radius: 3px;"
        )

        self.spinner = LoadingSpinner(size=24, parent=self)

        status_row.addWidget(self.summary_label, 1)
        status_row.addWidget(self.spinner)
        root.addLayout(status_row)

        # ── Legend row ────────────────────────────────────────────────────
        legend = QHBoxLayout()
        legend.setSpacing(20)
        for tier_key, label, colour in [
            ("active",   "Active",   GREEN_ACTIVE),
            ("at_risk",  "At Risk",  AMBER_RISK),
            ("inactive", "Inactive", RED_INACTIVE),
        ]:
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {colour}; font-size: 11px;")
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
            legend.addWidget(dot)
            legend.addWidget(lbl)
        legend.addStretch(1)
        root.addLayout(legend)

        # ── Table ─────────────────────────────────────────────────────────
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "TIER", "NAME", "TAG", "SCORE", "UTILITY", "LAST BATTLE", "7D", "TREND",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.table.horizontalHeader().setStretchLastSection(False)

        # Column widths
        self.table.setColumnWidth(0, 110)  # Tier badge
        self.table.setColumnWidth(1, 140)  # Name
        self.table.setColumnWidth(2, 120)  # Tag
        self.table.setColumnWidth(3, 130)  # Score bar
        self.table.setColumnWidth(4, 130)  # Utility bar
        self.table.setColumnWidth(5, 100)  # Last battle
        self.table.setColumnWidth(6, 50)   # 7d
        self.table.setColumnWidth(7, 60)   # Trend

        root.addWidget(self.table, 1)

    def _load_defaults(self) -> None:
        settings = load_local_settings()
        if settings.default_clan_tag:
            self.clan_tag_input.setText(settings.default_clan_tag)

    # ── Analysis trigger ──────────────────────────────────────────────────
    def run_analysis(self) -> None:
        try:
            clan_tag = normalize_clan_tag(self.clan_tag_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid clan tag", str(exc))
            return

        self.run_button.setEnabled(False)
        self.run_button.setText("Loading…")
        self.summary_label.setText(f"Loading clan health for {clan_tag}…")
        self.spinner.start()
        self.table.setRowCount(0)

        thread = QThread(self)
        worker = _ClanHealthWorker(clan_tag, self.show_active_checkbox.isChecked())
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_result)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_worker)

        self._worker_thread = thread
        self._worker = worker
        thread.start()

    # ── Result handling ───────────────────────────────────────────────────
    def _handle_result(self, payload: object) -> None:
        self.run_button.setEnabled(True)
        self.run_button.setText("Analyze Clan")
        self.spinner.stop()
        status, data = payload

        if status == "success":
            self._render_result(data)
            return
        if status == "empty":
            self.summary_label.setText(f"No members found for {data}.")
            return
        self.summary_label.setText(f"Failed to load clan health: {data}")

    def _render_result(self, vm: ClanHealthViewModel) -> None:
        summary = (
            f"<b>{vm.clan_tag}</b>  ·  {vm.total_members} members  ·  "
            f"Inactive: <span style='color:{RED_INACTIVE}'><b>{vm.inactive_count}</b></span>  ·  "
            f"At Risk: <span style='color:{AMBER_RISK}'><b>{vm.at_risk_count}</b></span>  ·  "
            f"Active: <span style='color:{GREEN_ACTIVE}'><b>{vm.active_count}</b></span>"
        )
        self.summary_label.setText(summary)
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)

        self.table.setRowCount(len(vm.rows))
        score_bars: list[ScoreBar] = []

        mono_font = QFont(FONT_MONO, 11)
        body_font = QFont(FONT_BODY, 13)

        for i, row in enumerate(vm.rows):
            self.table.setRowHeight(i, ROW_HEIGHT)
            tint = _ROW_TINTS.get(row.tier_key, QColor(BG_SURFACE))

            # Col 0 — Tier badge (widget)
            badge = TierBadge(row.tier_key)
            badge.setAutoFillBackground(False)
            self._center_cell_widget(i, 0, badge)

            # Col 1 — Name
            name_item = QTableWidgetItem(row.name)
            name_item.setBackground(tint)
            name_item.setFont(body_font)
            self.table.setItem(i, 1, name_item)

            # Col 2 — Tag (monospace, full tag as tooltip)
            tag_item = QTableWidgetItem(row.tag)
            tag_item.setBackground(tint)
            tag_item.setFont(mono_font)
            tag_item.setForeground(QColor(GOLD_MID))
            tag_item.setToolTip(row.tag)
            self.table.setItem(i, 2, tag_item)

            # Col 3 — Score bar (animated)
            try:
                score_val = float(row.score_text)
            except ValueError:
                score_val = 0.0
            score_bar = ScoreBar(0.0)
            score_bars.append(score_bar)
            self._center_cell_widget(i, 3, score_bar)

            # Col 4 — Utility bar (animated)
            try:
                util_val = float(row.utility_text)
            except ValueError:
                util_val = 0.0
            util_bar = ScoreBar(0.0)
            score_bars.append(util_bar)
            self._center_cell_widget(i, 4, util_bar)

            # Store values for staggered animation
            score_bar._target = score_val
            util_bar._target = util_val

            # Col 5 — Last battle
            last_item = QTableWidgetItem(row.days_since_last_any_text)
            last_item.setBackground(tint)
            last_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 5, last_item)

            # Col 6 — Battles 7d
            b7d_item = QTableWidgetItem(row.raw_7d_text)
            b7d_item.setBackground(tint)
            b7d_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 6, b7d_item)

            # Col 7 — Trend (coloured glyph)
            trend_item = QTableWidgetItem(row.trend_text)
            trend_item.setBackground(tint)
            trend_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            trend_col = _TREND_COLORS.get(row.trend_text, TEXT_MUTED)
            trend_item.setForeground(QColor(trend_col))
            trend_font = QFont(FONT_BODY, 14)
            trend_item.setFont(trend_font)
            self.table.setItem(i, 7, trend_item)

        # ── Fade in the table, then stagger-animate score bars ────────────
        self._fade_in_table()
        self._stagger_score_bars(score_bars)
        self._persist_default_clan_tag(vm.clan_tag)

    def _center_cell_widget(self, row: int, col: int, widget: QWidget) -> None:
        """Wrap a widget in a centred container for cleaner cell alignment."""
        container = QWidget()
        container.setAutoFillBackground(False)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget)
        self.table.setCellWidget(row, col, container)

    def _fade_in_table(self) -> None:
        # QGraphicsOpacityEffect conflicts with cell widgets that have custom
        # painters (ScoreBar, TierBadge), so we skip the fade here.
        pass

    def _stagger_score_bars(self, bars: list[ScoreBar]) -> None:
        """Animate all score bars, staggered by 30 ms each."""
        from PySide6.QtCore import QTimer
        for idx, bar in enumerate(bars):
            target = getattr(bar, "_target", 0.0)
            QTimer.singleShot(idx * 30, lambda b=bar, t=target: b.animate_to(t))

    def _persist_default_clan_tag(self, clan_tag: str) -> None:
        settings = load_local_settings()
        if settings.default_clan_tag == clan_tag:
            return
        settings.default_clan_tag = clan_tag
        save_local_settings(settings)

    def _clear_worker(self) -> None:
        self._worker_thread = None
        self._worker = None
