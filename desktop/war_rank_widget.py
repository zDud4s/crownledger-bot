from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.config import load_local_settings, save_local_settings
from app.input_normalizers import normalize_clan_tag
from app.presenters.war_rank_presenter import WarRankViewModel, present_war_rank
from app.use_cases.war_rank import rank_players_by_war_utility
from desktop.components import LoadingSpinner, ScoreBar, TierBadge
from desktop.theme import (
    AMBER_RISK,
    BG_SURFACE,
    BORDER_DARK,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_MONO,
    GOLD_BRIGHT,
    GOLD_DIM,
    GOLD_MID,
    GREEN_ACTIVE,
    RED_INACTIVE,
    ROW_HEIGHT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

# Rank number colour by position
_RANK_COLOURS = {1: GOLD_BRIGHT, 2: "#C0C0C0", 3: "#CD7F32"}


def _form_row(label_text: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(140)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    return row


class _WarRankWorker(QObject):
    finished = Signal(object)

    def __init__(self, clan_tag: str, wars: int) -> None:
        super().__init__()
        self.clan_tag = clan_tag
        self.wars = wars

    def run(self) -> None:
        try:
            players = rank_players_by_war_utility(self.clan_tag, self.wars)
            if not players:
                self.finished.emit(("empty", self.clan_tag))
                return
            view_model = present_war_rank(self.clan_tag, self.wars, players)
            self.finished.emit(("success", view_model))
        except Exception as exc:
            self.finished.emit(("error", str(exc)))


class WarRankWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker_thread: QThread | None = None
        self._worker: _WarRankWorker | None = None
        self._build_ui()
        self._load_defaults()

    # ── UI construction ───────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 16)
        root.setSpacing(12)

        # Title
        title = QLabel("War Rank")
        title_font = QFont(FONT_DISPLAY, 18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {GOLD_BRIGHT};")
        root.addWidget(title)

        subtitle = QLabel("Rank clan members by their war utility over recent battles.")
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        root.addWidget(subtitle)

        # ── Controls ──────────────────────────────────────────────────────
        controls = QHBoxLayout()
        controls.setSpacing(16)

        self.clan_tag_input = QLineEdit()
        self.clan_tag_input.setPlaceholderText("#CLANTAG")
        self.clan_tag_input.returnPressed.connect(self.run_analysis)

        self.wars_input = QSpinBox()
        self.wars_input.setMinimum(1)
        self.wars_input.setMaximum(10)
        self.wars_input.setValue(5)
        self.wars_input.setFixedWidth(70)

        self.run_button = QPushButton("Load War Ranking")
        self.run_button.clicked.connect(self.run_analysis)

        controls.addLayout(_form_row("Clan tag", self.clan_tag_input))
        controls.addLayout(_form_row("Wars to analyse", self.wars_input))
        controls.addStretch(1)
        controls.addWidget(self.run_button)
        root.addLayout(controls)

        # ── Status row ────────────────────────────────────────────────────
        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        self.summary_label = QLabel("Enter a clan tag to load war ranking.")
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

        # ── Legend ────────────────────────────────────────────────────────
        legend = QHBoxLayout()
        legend.setSpacing(20)
        for tier_key, label, colour in [
            ("Strong", "Strong",  GREEN_ACTIVE),
            ("Solid",  "Solid",   AMBER_RISK),
            ("Low",    "Low",     RED_INACTIVE),
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
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels([
            "#", "TIER", "NAME", "TAG", "UTILITY",
            "WARS", "PART.", "CONSIST.", "FAME/DECK",
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)

        self.table.setColumnWidth(0, 44)   # Rank
        self.table.setColumnWidth(1, 90)   # Tier badge
        self.table.setColumnWidth(2, 140)  # Name
        self.table.setColumnWidth(3, 100)  # Tag
        self.table.setColumnWidth(4, 140)  # Utility bar
        self.table.setColumnWidth(5, 70)   # Wars
        self.table.setColumnWidth(6, 70)   # Part.
        self.table.setColumnWidth(7, 80)   # Consist.
        self.table.setColumnWidth(8, 80)   # Fame/deck

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

        wars = int(self.wars_input.value())
        self.run_button.setEnabled(False)
        self.run_button.setText("Loading…")
        self.summary_label.setText(f"Loading war ranking for {clan_tag}…")
        self.spinner.start()
        self.table.setRowCount(0)

        thread = QThread(self)
        worker = _WarRankWorker(clan_tag, wars)
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
        self.run_button.setText("Load War Ranking")
        self.spinner.stop()
        status, data = payload

        if status == "success":
            self._render_result(data)
            return
        if status == "empty":
            self.summary_label.setText(f"No war data found for {data}.")
            return
        self.summary_label.setText(f"Failed to load war ranking: {data}")

    def _render_result(self, vm: WarRankViewModel) -> None:
        self.summary_label.setText(
            f"{vm.clan_tag}  ·  {vm.total_players} players  ·  "
            f"Wars requested: {vm.requested_wars}  ·  Wars used: {vm.actual_wars}"
        )

        self.table.setRowCount(len(vm.rows))
        util_bars: list[ScoreBar] = []

        mono_font = QFont(FONT_MONO, 11)
        body_font = QFont(FONT_BODY, 13)
        rank_font = QFont(FONT_DISPLAY, 13)
        rank_font.setBold(True)

        for i, row in enumerate(vm.rows):
            self.table.setRowHeight(i, ROW_HEIGHT)

            # Col 0 — Rank number (gold for top 3)
            rank_item = QTableWidgetItem(row.rank_text)
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rank_item.setFont(rank_font)
            rank_num = i + 1
            rank_colour = _RANK_COLOURS.get(rank_num, GOLD_DIM)
            rank_item.setForeground(QColor(rank_colour))
            self.table.setItem(i, 0, rank_item)

            # Col 1 — Tier badge
            self._center_cell_widget(i, 1, TierBadge(row.tier_label))

            # Col 2 — Name
            name_item = QTableWidgetItem(row.name)
            name_item.setFont(body_font)
            self.table.setItem(i, 2, name_item)

            # Col 3 — Tag (monospace, accent colour)
            tag_item = QTableWidgetItem(row.tag)
            tag_item.setFont(mono_font)
            tag_item.setForeground(QColor(GOLD_MID))
            self.table.setItem(i, 3, tag_item)

            # Col 4 — Utility bar (animated)
            try:
                util_val = float(row.utility_text)
            except ValueError:
                util_val = 0.0
            bar = ScoreBar(0.0)
            bar._target = util_val
            util_bars.append(bar)
            self._center_cell_widget(i, 4, bar)

            # Cols 5-8 — Text stats
            for col, text, align in [
                (5, row.wars_text,          Qt.AlignmentFlag.AlignCenter),
                (6, row.participation_text, Qt.AlignmentFlag.AlignCenter),
                (7, row.consistency_text,   Qt.AlignmentFlag.AlignCenter),
                (8, row.fame_text,          Qt.AlignmentFlag.AlignCenter),
            ]:
                item = QTableWidgetItem(text)
                item.setTextAlignment(align)
                item.setFont(body_font)
                self.table.setItem(i, col, item)

        self._fade_in_table()
        self._stagger_score_bars(util_bars)
        self._persist_default_clan_tag(vm.clan_tag)

    def _center_cell_widget(self, row: int, col: int, widget: QWidget) -> None:
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
        from PySide6.QtCore import QTimer
        for idx, bar in enumerate(bars):
            target = getattr(bar, "_target", 0.0)
            QTimer.singleShot(idx * 35, lambda b=bar, t=target: b.animate_to(t))

    def _persist_default_clan_tag(self, clan_tag: str) -> None:
        settings = load_local_settings()
        if settings.default_clan_tag == clan_tag:
            return
        settings.default_clan_tag = clan_tag
        save_local_settings(settings)

    def _clear_worker(self) -> None:
        self._worker_thread = None
        self._worker = None
