from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFormLayout,
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

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("War Rank")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.clan_tag_input = QLineEdit()
        self.clan_tag_input.setPlaceholderText("#CLANTAG")

        self.wars_input = QSpinBox()
        self.wars_input.setMinimum(1)
        self.wars_input.setMaximum(10)
        self.wars_input.setValue(5)

        form.addRow("Clan tag", self.clan_tag_input)
        form.addRow("Wars to analyze", self.wars_input)
        root.addLayout(form)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.run_button = QPushButton("Load war ranking")
        self.run_button.clicked.connect(self.run_analysis)
        actions.addWidget(self.run_button)
        actions.addStretch(1)
        root.addLayout(actions)

        self.summary_label = QLabel("Enter a clan tag to load war ranking.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.summary_label)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["Rank", "Tier", "Name", "Tag", "Utility", "Wars", "Participation", "Consistency", "Fame/Deck"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(self.table, 1)

    def _load_defaults(self) -> None:
        settings = load_local_settings()
        if settings.default_clan_tag:
            self.clan_tag_input.setText(settings.default_clan_tag)

    def run_analysis(self) -> None:
        try:
            clan_tag = normalize_clan_tag(self.clan_tag_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid clan tag", str(exc))
            return

        wars = int(self.wars_input.value())
        self.run_button.setEnabled(False)
        self.summary_label.setText(f"Loading war ranking for {clan_tag}...")
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

    def _handle_result(self, payload: object) -> None:
        self.run_button.setEnabled(True)
        status, data = payload

        if status == "success":
            self._render_result(data)
            return

        if status == "empty":
            self.summary_label.setText(f"No war data found for {data}.")
            return

        self.summary_label.setText(f"Failed to load war ranking: {data}")

    def _render_result(self, view_model: WarRankViewModel) -> None:
        self.summary_label.setText(view_model.summary_text)
        self.table.setRowCount(len(view_model.rows))

        row_colors = {
            "Strong": QColor("#d1e7dd"),
            "Solid": QColor("#fff3cd"),
            "Low": QColor("#f8d7da"),
        }

        for row_index, row in enumerate(view_model.rows):
            values = [
                row.rank_text,
                row.tier_label,
                row.name,
                row.tag,
                row.utility_text,
                row.wars_text,
                row.participation_text,
                row.consistency_text,
                row.fame_text,
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setBackground(row_colors[row.tier_label])
                self.table.setItem(row_index, column_index, item)

        self.table.resizeColumnsToContents()
        self._persist_default_clan_tag(view_model.clan_tag)

    def _persist_default_clan_tag(self, clan_tag: str) -> None:
        settings = load_local_settings()
        if settings.default_clan_tag == clan_tag:
            return

        settings.default_clan_tag = clan_tag
        save_local_settings(settings)

    def _clear_worker(self) -> None:
        self._worker_thread = None
        self._worker = None
