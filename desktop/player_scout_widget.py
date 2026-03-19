from __future__ import annotations

import asyncio

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.config import load_local_settings, save_local_settings
from app.input_normalizers import normalize_player_tag
from app.presenters.player_scout_presenter import PlayerScoutViewModel, present_player_scout
from app.use_cases.player_scout import scout_player


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


def _build_section(title: str) -> tuple[QGroupBox, QLabel]:
    group = QGroupBox(title)
    layout = QVBoxLayout(group)
    label = QLabel()
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(label)
    return group, label


class PlayerScoutWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._worker_thread: QThread | None = None
        self._worker: _PlayerScoutWorker | None = None
        self._build_ui()
        self._load_defaults()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("Scout")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.player_tag_input = QLineEdit()
        self.player_tag_input.setPlaceholderText("#PLAYERTAG")

        self.wars_input = QSpinBox()
        self.wars_input.setMinimum(5)
        self.wars_input.setMaximum(20)
        self.wars_input.setValue(10)

        form.addRow("Player tag", self.player_tag_input)
        form.addRow("War weeks", self.wars_input)
        root.addLayout(form)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.run_button = QPushButton("Scout player")
        self.run_button.clicked.connect(self.run_analysis)
        actions.addWidget(self.run_button)
        actions.addStretch(1)
        root.addLayout(actions)

        self.summary_label = QLabel("Enter a player tag to scout a player.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.summary_label)

        self.profile_group, self.profile_label = _build_section("Profile")
        self.activity_group, self.activity_label = _build_section("Activity")
        self.utility_group, self.utility_label = _build_section("Mode Utility")
        self.wars_group, self.wars_label = _build_section("Wars")
        self.candidate_group, self.candidate_label = _build_section("Candidate")

        root.addWidget(self.profile_group)
        root.addWidget(self.activity_group)
        root.addWidget(self.utility_group)
        root.addWidget(self.wars_group)
        root.addWidget(self.candidate_group)
        root.addStretch(1)

    def _load_defaults(self) -> None:
        settings = load_local_settings()
        if settings.last_used_player_tag:
            self.player_tag_input.setText(settings.last_used_player_tag)

    def run_analysis(self) -> None:
        try:
            player_tag = normalize_player_tag(self.player_tag_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid player tag", str(exc))
            return

        wars = int(self.wars_input.value())
        settings = load_local_settings()

        self.run_button.setEnabled(False)
        self.summary_label.setText(f"Loading scout report for {player_tag}...")
        self._clear_sections()

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
        status, data = payload

        if status == "success":
            self._render_result(data)
            return

        self.summary_label.setText(f"Failed to scout player: {data}")

    def _render_result(self, view_model: PlayerScoutViewModel) -> None:
        self.summary_label.setText(f"{view_model.title_text} | {view_model.clan_text}")
        self.profile_label.setText(view_model.profile_text)
        self.activity_label.setText(view_model.activity_text)
        self.utility_label.setText(view_model.utility_text)
        self.wars_label.setText(view_model.wars_text)
        self.candidate_label.setText(view_model.candidate_text)
        self._persist_last_player_tag(view_model.player_tag)

    def _persist_last_player_tag(self, player_tag: str) -> None:
        settings = load_local_settings()
        if settings.last_used_player_tag == player_tag:
            return

        settings.last_used_player_tag = player_tag
        save_local_settings(settings)

    def _clear_sections(self) -> None:
        self.profile_label.setText("")
        self.activity_label.setText("")
        self.utility_label.setText("")
        self.wars_label.setText("")
        self.candidate_label.setText("")

    def _clear_worker(self) -> None:
        self._worker_thread = None
        self._worker = None
