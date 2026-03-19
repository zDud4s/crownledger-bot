from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
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

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("Clan Health")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.clan_tag_input = QLineEdit()
        self.clan_tag_input.setPlaceholderText("#CLANTAG")
        self.show_active_checkbox = QCheckBox("Include active players")

        form.addRow("Clan tag", self.clan_tag_input)
        form.addRow("", self.show_active_checkbox)
        root.addLayout(form)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.run_button = QPushButton("Analyze clan")
        self.run_button.clicked.connect(self.run_analysis)
        actions.addWidget(self.run_button)
        actions.addStretch(1)

        root.addLayout(actions)

        self.summary_label = QLabel("Enter a clan tag to load clan health.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.summary_label)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Tier", "Name", "Tag", "Score", "Utility", "Last Battle", "Battles 7d", "Trend"]
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

        self.run_button.setEnabled(False)
        self.summary_label.setText(f"Loading clan health for {clan_tag}...")
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

    def _handle_result(self, payload: object) -> None:
        self.run_button.setEnabled(True)
        status, data = payload

        if status == "success":
            self._render_result(data)
            return

        if status == "empty":
            self.summary_label.setText(f"No members found for {data}.")
            return

        self.summary_label.setText(f"Failed to load clan health: {data}")

    def _render_result(self, view_model: ClanHealthViewModel) -> None:
        self.summary_label.setText(view_model.summary_text)
        self.table.setRowCount(len(view_model.rows))

        row_colors = {
            "inactive": QColor("#f8d7da"),
            "at_risk": QColor("#fff3cd"),
            "active": QColor("#d1e7dd"),
        }

        for row_index, row in enumerate(view_model.rows):
            values = [
                row.tier_label,
                row.name,
                row.tag,
                row.score_text,
                row.utility_text,
                row.days_since_last_any_text,
                row.raw_7d_text,
                row.trend_text,
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setBackground(row_colors[row.tier_key])
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
