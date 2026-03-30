from __future__ import annotations

import asyncio

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.config import load_local_settings, save_local_settings
from app.input_normalizers import normalize_player_tag
from app.presenters.player_scout_presenter import PlayerScoutViewModel, present_player_scout
from app.use_cases.player_scout import scout_player
from desktop.assets import AssetManager
from desktop.components import LoadingSpinner, ScoreBar, StatCard
from desktop.theme import (
    AMBER_RISK,
    BG_DEEP,
    BG_SURFACE,
    BG_SURFACE_2,
    BORDER_DARK,
    BORDER_GOLD,
    CARD_RADIUS,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_MONO,
    GOLD_BRIGHT,
    GOLD_DIM,
    GOLD_MID,
    GREEN_ACTIVE,
    RED_INACTIVE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_WHITE,
    candidate_verdict,
)


def _form_row(label_text: str, widget: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(110)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    return row


# ── Player header card ────────────────────────────────────────────────────────

class _PlayerHeaderCard(QFrame):
    """Dark hero card shown at the top of the scout results.

    Displays: avatar | name / tag / clan | candidate score bar + verdict label.
    """

    _HEIGHT = 110

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(self._HEIGHT)
        self._verdict_colour = GOLD_MID

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.setSpacing(16)

        # Avatar
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(72, 72)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setStyleSheet(
            f"border: 1px solid {BORDER_GOLD}; border-radius: 6px;"
        )
        outer.addWidget(self.avatar_label)

        # Centre column — name, tag, clan
        centre = QVBoxLayout()
        centre.setSpacing(3)

        self.name_label = QLabel()
        name_font = QFont(FONT_DISPLAY, 18)
        name_font.setBold(True)
        self.name_label.setFont(name_font)
        self.name_label.setStyleSheet(f"color: {TEXT_WHITE};")

        self.tag_label = QLabel()
        tag_font = QFont(FONT_MONO, 12)
        self.tag_label.setFont(tag_font)
        self.tag_label.setStyleSheet(f"color: {GOLD_MID};")

        self.clan_label = QLabel()
        self.clan_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")

        centre.addStretch(1)
        centre.addWidget(self.name_label)
        centre.addWidget(self.tag_label)
        centre.addWidget(self.clan_label)
        centre.addStretch(1)
        outer.addLayout(centre, 1)

        # Right column — score bar + verdict
        right = QVBoxLayout()
        right.setSpacing(5)
        right.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        score_lbl = QLabel("CANDIDATE SCORE")
        score_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; font-weight: bold;")
        right.addWidget(score_lbl)

        self.score_bar = ScoreBar(0.0)
        self.score_bar.setMinimumWidth(180)
        right.addWidget(self.score_bar)

        self.verdict_label = QLabel()
        verdict_font = QFont(FONT_DISPLAY, 12)
        verdict_font.setBold(True)
        self.verdict_label.setFont(verdict_font)
        right.addWidget(self.verdict_label)

        outer.addLayout(right)

    def populate(self, vm: PlayerScoutViewModel) -> None:
        # Parse name from "Name | #TAG"
        parts = vm.title_text.split(" | ", 1)
        name = parts[0].strip() if parts else vm.title_text
        self.name_label.setText(name)
        self.tag_label.setText(vm.player_tag)
        self.clan_label.setText(vm.clan_text)

        # Avatar (placeholder or real game image)
        pixmap = AssetManager.player_avatar(vm.player_tag, size=72)
        self.avatar_label.setPixmap(pixmap)

        # Candidate verdict
        verdict, colour = candidate_verdict(vm.candidate_score)
        self._verdict_colour = colour
        self.verdict_label.setText(verdict)
        self.verdict_label.setStyleSheet(f"color: {colour};")
        self.score_bar.animate_to(vm.candidate_score)

        self.update()  # repaint custom background

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background gradient
        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(BG_SURFACE_2))
        grad.setColorAt(0.6, QColor(BG_SURFACE))
        grad.setColorAt(1.0, QColor(BG_DEEP))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawRoundedRect(0, 0, w, h, CARD_RADIUS, CARD_RADIUS)

        # Coloured top edge
        accent = QColor(self._verdict_colour)
        accent.setAlpha(160)
        painter.setBrush(accent)
        painter.drawRoundedRect(0, 0, w, 3, 1, 1)

        # Border
        painter.setPen(QPen(QColor(BORDER_GOLD), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0.5, 0.5, w - 1, h - 1, CARD_RADIUS, CARD_RADIUS)

        painter.end()


# ── Worker ────────────────────────────────────────────────────────────────────

class _PlayerScoutWorker(QObject):
    finished = Signal(object)

    def __init__(self, player_tag: str, wars: int, war_history_enabled: bool) -> None:
        super().__init__()
        self.player_tag = player_tag
        self.wars = wars
        self.war_history_enabled = war_history_enabled

    def run(self) -> None:
        try:
            report = asyncio.run(
                scout_player(
                    self.player_tag,
                    war_weeks=self.wars,
                    war_history_enabled=self.war_history_enabled,
                )
            )
            self.finished.emit(("success", present_player_scout(report)))
        except Exception as exc:
            self.finished.emit(("error", str(exc)))


# ── Main widget ───────────────────────────────────────────────────────────────

class PlayerScoutWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker_thread: QThread | None = None
        self._worker: _PlayerScoutWorker | None = None
        self._build_ui()
        self._load_defaults()

    # ── Build ─────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 0)
        root.setSpacing(12)

        # Title
        title = QLabel("Scout")
        title_font = QFont(FONT_DISPLAY, 18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {GOLD_BRIGHT};")
        root.addWidget(title)

        subtitle = QLabel("Deep-dive player stats: activity, mode utility, war performance, and candidacy.")
        subtitle.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px;")
        root.addWidget(subtitle)

        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(16)

        self.player_tag_input = QLineEdit()
        self.player_tag_input.setPlaceholderText("#PLAYERTAG")
        self.player_tag_input.returnPressed.connect(self.run_analysis)

        self.wars_input = QSpinBox()
        self.wars_input.setMinimum(5)
        self.wars_input.setMaximum(20)
        self.wars_input.setValue(10)
        self.wars_input.setFixedWidth(70)

        self.run_button = QPushButton("Scout Player")
        self.run_button.clicked.connect(self.run_analysis)

        controls.addLayout(_form_row("Player tag", self.player_tag_input))
        controls.addLayout(_form_row("War weeks", self.wars_input))
        controls.addStretch(1)
        controls.addWidget(self.run_button)
        root.addLayout(controls)

        # Status / error bar
        status_row = QHBoxLayout()
        self.summary_label = QLabel("Enter a player tag to scout a player.")
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

        # ── Scroll area wraps the results ──────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(0, 4, 0, 12)
        self._results_layout.setSpacing(12)
        self._results_layout.addStretch(1)

        scroll.setWidget(self._results_widget)
        root.addWidget(scroll, 1)

        # Build empty result containers (hidden until data loads)
        self._header_card = _PlayerHeaderCard()
        self._header_card.hide()

        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(10)
        self._grid_widget.hide()

        # StatCards
        self._profile_card  = StatCard("Profile")
        self._activity_card = StatCard("Activity")
        self._utility_card  = StatCard("Mode Utility")
        self._wars_card     = StatCard("Wars")

        self._grid_layout.addWidget(self._profile_card,  0, 0)
        self._grid_layout.addWidget(self._activity_card, 0, 1)
        self._grid_layout.addWidget(self._utility_card,  1, 0)
        self._grid_layout.addWidget(self._wars_card,     1, 1)

        # Dynamic labels inside each card (populated on data load)
        self._profile_label  = self._profile_card.add_text("")
        self._activity_score_bar = ScoreBar(0.0)
        self._activity_card.body_layout.addWidget(self._activity_score_bar)
        self._activity_label = self._activity_card.add_text("")

        self._utility_score_bar = ScoreBar(0.0)
        self._utility_card.body_layout.addWidget(self._utility_score_bar)
        self._utility_label = self._utility_card.add_text("")

        self._wars_score_bar = ScoreBar(0.0)
        self._wars_card.body_layout.addWidget(self._wars_score_bar)
        self._wars_label = self._wars_card.add_text("")

        # Insert into results layout (above the stretch)
        self._results_layout.insertWidget(0, self._header_card)
        self._results_layout.insertWidget(1, self._grid_widget)

    def _load_defaults(self) -> None:
        settings = load_local_settings()
        if settings.last_used_player_tag:
            self.player_tag_input.setText(settings.last_used_player_tag)

    # ── Analysis ──────────────────────────────────────────────────────────
    def run_analysis(self) -> None:
        try:
            player_tag = normalize_player_tag(self.player_tag_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid player tag", str(exc))
            return

        wars = int(self.wars_input.value())
        settings = load_local_settings()

        self.run_button.setEnabled(False)
        self.run_button.setText("Loading…")
        self.summary_label.setText(f"Scouting {player_tag}…")
        self.spinner.start()
        self._header_card.hide()
        self._grid_widget.hide()
        self._wars_score_bar.set_value(0.0)
        self._wars_score_bar.setVisible(True)  # reset; hidden again if no data

        thread = QThread(self)
        worker = _PlayerScoutWorker(
            player_tag=player_tag,
            wars=wars,
            war_history_enabled=settings.war_history_enabled,
        )
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

    def _handle_result(self, payload: object) -> None:
        self.run_button.setEnabled(True)
        self.run_button.setText("Scout Player")
        self.spinner.stop()
        status, data = payload

        if status == "success":
            self._render_result(data)
            return
        self.summary_label.setText(f"Failed to scout player: {data}")

    def _render_result(self, vm: PlayerScoutViewModel) -> None:
        # Status bar
        self.summary_label.setText(f"{vm.title_text}  ·  {vm.clan_text}")

        # ── Header card ────────────────────────────────────────────────────
        self._header_card.populate(vm)
        self._header_card.show()

        # ── Profile card ───────────────────────────────────────────────────
        self._profile_label.setText(vm.profile_text)

        # ── Activity card ──────────────────────────────────────────────────
        # Strip the first line ("Recent activity: 0.82 (Strong)\n…")
        # and show it as a ScoreBar + remaining text
        activity_lines = vm.activity_text.split("\n", 1)
        self._activity_label.setText(activity_lines[1] if len(activity_lines) > 1 else vm.activity_text)

        # ── Utility card ───────────────────────────────────────────────────
        utility_lines = vm.utility_text.split("\n", 1)
        self._utility_label.setText(utility_lines[1] if len(utility_lines) > 1 else vm.utility_text)

        # ── Wars card ──────────────────────────────────────────────────────
        self._wars_label.setText(vm.wars_text)

        # Show grid
        self._grid_widget.show()


        # ── Wars ScoreBar — hide when no war data ──────────────────────────
        self._wars_score_bar.setVisible(vm.war_data_available)

        # ── Animate score bars (staggered) ─────────────────────────────────
        from PySide6.QtCore import QTimer
        bars_targets = [
            (self._activity_score_bar, vm.activity_score),
            (self._utility_score_bar,  vm.battle_utility),
        ]
        if vm.war_data_available:
            bars_targets.append((self._wars_score_bar, vm.war_utility))
        for idx, (bar, target) in enumerate(bars_targets):
            QTimer.singleShot(idx * 80, lambda b=bar, t=target: b.animate_to(t))

        self._persist_last_player_tag(vm.player_tag)

    def _persist_last_player_tag(self, player_tag: str) -> None:
        settings = load_local_settings()
        if settings.last_used_player_tag == player_tag:
            return
        settings.last_used_player_tag = player_tag
        save_local_settings(settings)

    def _clear_worker(self) -> None:
        self._worker_thread = None
        self._worker = None
