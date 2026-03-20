from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.config import (
    LocalSettings,
    get_app_data_dir,
    load_local_settings_result,
    save_local_settings,
)
from app.input_normalizers import normalize_clan_tag, normalize_player_tag
from app.update_service import StagedUpdate, UpdateCheckResult, check_for_update, stage_update_from_release
from desktop.runtime import can_apply_inplace_update, launch_staged_update
from desktop.theme import (
    BORDER_DARK,
    BG_SURFACE,
    FONT_BODY,
    FONT_DISPLAY,
    FONT_MONO,
    GOLD_BRIGHT,
    GOLD_DIM,
    RED_INACTIVE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from desktop.version import APP_NAME, __version__


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    font = QFont(FONT_DISPLAY, 12)
    font.setBold(True)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color: {GOLD_DIM};")
    return lbl


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background-color: {BORDER_DARK}; border: none;")
    return line


def _form_row(label_text: str, widget: QWidget, label_width: int = 160) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(10)
    lbl = QLabel(label_text)
    lbl.setFixedWidth(label_width)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    return row


def _section_card(title: str) -> tuple[QFrame, QVBoxLayout]:
    """Returns (card widget, inner vbox for form rows)."""
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ background-color: {BG_SURFACE}; "
        f"border: 1px solid {BORDER_DARK}; "
        f"border-radius: 6px; }}"
    )
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(16, 12, 16, 14)
    card_layout.setSpacing(10)
    card_layout.addWidget(_section_title(title))
    card_layout.addWidget(_separator())
    inner = QVBoxLayout()
    inner.setSpacing(8)
    card_layout.addLayout(inner)
    return card, inner


# ── Workers ───────────────────────────────────────────────────────────────────

class _UpdateWorker(QObject):
    finished = Signal(object)

    def __init__(self, current_version: str, repository: str, release_channel: str) -> None:
        super().__init__()
        self.current_version = current_version
        self.repository = repository
        self.release_channel = release_channel

    def run(self) -> None:
        result = check_for_update(
            current_version=self.current_version,
            repository=self.repository,
            release_channel=self.release_channel,
        )
        self.finished.emit(result)


class _UpdateInstallWorker(QObject):
    finished = Signal(object)

    def __init__(self, download_url: str, version: str) -> None:
        super().__init__()
        self.download_url = download_url
        self.version = version

    def run(self) -> None:
        try:
            staged = stage_update_from_release(
                download_url=self.download_url,
                version=self.version,
            )
            self.finished.emit(("success", staged))
        except Exception as exc:
            self.finished.emit(("error", str(exc)))


# ── Widget ────────────────────────────────────────────────────────────────────

class SettingsWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._update_thread: QThread | None = None
        self._update_worker: _UpdateWorker | None = None
        self._install_thread: QThread | None = None
        self._install_worker: _UpdateInstallWorker | None = None
        self._build_ui()
        self.reload_settings()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 16)
        root.setSpacing(12)

        # Page title
        title = QLabel("Settings")
        title_font = QFont(FONT_DISPLAY, 18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {GOLD_BRIGHT};")
        root.addWidget(title)

        # Scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 4, 12)
        scroll_layout.setSpacing(14)

        # ── App Info ───────────────────────────────────────────────────────
        info_card, info_inner = _section_card("App Info")
        self.version_label = QLabel()
        self.version_label.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 13px;")
        self.path_label = QLabel()
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_font = QFont(FONT_MONO, 11)
        self.path_label.setFont(path_font)
        self.path_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 11px;")
        info_inner.addLayout(_form_row("Version", self.version_label))
        info_inner.addLayout(_form_row("Data path", self.path_label))
        scroll_layout.addWidget(info_card)

        # ── API Configuration ──────────────────────────────────────────────
        api_card, api_inner = _section_card("API Configuration")
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Clash Royale API token")
        self.default_clan_input = QLineEdit()
        self.default_clan_input.setPlaceholderText("#CLANTAG")
        self.last_player_input = QLineEdit()
        self.last_player_input.setPlaceholderText("#PLAYERTAG")
        self.war_history_checkbox = QCheckBox("Enable war history scraping")
        self.war_history_checkbox.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 13px;")
        api_inner.addLayout(_form_row("Clash API token", self.token_input))
        api_inner.addLayout(_form_row("Default clan tag", self.default_clan_input))
        api_inner.addLayout(_form_row("Last player tag", self.last_player_input))
        api_inner.addWidget(self.war_history_checkbox)
        scroll_layout.addWidget(api_card)

        # ── Updates ────────────────────────────────────────────────────────
        upd_card, upd_inner = _section_card("Updates")
        self.github_repo_input = QLineEdit()
        self.github_repo_input.setPlaceholderText("owner/repository")
        self.release_channel_input = QComboBox()
        self.release_channel_input.addItems(["stable", "beta"])
        upd_inner.addLayout(_form_row("GitHub repo", self.github_repo_input))
        upd_inner.addLayout(_form_row("Release channel", self.release_channel_input))

        upd_btn_row = QHBoxLayout()
        self.update_button = QPushButton("Check for Updates")
        self.update_button.clicked.connect(self.check_updates)
        upd_btn_row.addWidget(self.update_button)
        upd_btn_row.addStretch(1)
        upd_inner.addLayout(upd_btn_row)
        scroll_layout.addWidget(upd_card)

        # ── Status ─────────────────────────────────────────────────────────
        status_card, status_inner = _section_card("Status")
        self.status_label = QLabel("Settings not loaded yet.")
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
        status_inner.addWidget(self.status_label)
        scroll_layout.addWidget(status_card)

        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_content)
        root.addWidget(scroll, 1)

        # Bottom action bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)
        self.reload_button = QPushButton("Reload")
        self.reload_button.setObjectName("btnSecondary")
        self.reload_button.clicked.connect(self.reload_settings)
        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings)
        action_bar.addWidget(self.reload_button)
        action_bar.addWidget(self.save_button)
        action_bar.addStretch(1)
        root.addLayout(action_bar)

    # ── Settings I/O ──────────────────────────────────────────────────────
    def reload_settings(self) -> None:
        result = load_local_settings_result()
        s = result.settings
        self.version_label.setText(f"{APP_NAME}  {__version__}")
        self.path_label.setText(str(get_app_data_dir()))
        self.token_input.setText(s.clash_api_token)
        self.default_clan_input.setText(s.default_clan_tag)
        self.last_player_input.setText(s.last_used_player_tag)
        self.github_repo_input.setText(s.github_repo)
        self.war_history_checkbox.setChecked(s.war_history_enabled)
        idx = self.release_channel_input.findText(s.release_channel)
        self.release_channel_input.setCurrentIndex(0 if idx < 0 else idx)
        if result.error:
            self._set_status(f"Settings fallback loaded. {result.error}", is_error=True)
        else:
            self._set_status("Settings loaded from local storage.")

    def _collect_settings(self) -> LocalSettings:
        default_clan_tag = self.default_clan_input.text().strip()
        if default_clan_tag:
            default_clan_tag = normalize_clan_tag(default_clan_tag)
        last_player_tag = self.last_player_input.text().strip()
        if last_player_tag:
            last_player_tag = normalize_player_tag(last_player_tag)
        return LocalSettings(
            clash_api_token=self.token_input.text().strip(),
            default_clan_tag=default_clan_tag,
            last_used_player_tag=last_player_tag,
            war_history_enabled=self.war_history_checkbox.isChecked(),
            release_channel=self.release_channel_input.currentText(),
            github_repo=self.github_repo_input.text().strip(),
        )

    def save_settings(self) -> None:
        try:
            settings = self._collect_settings()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid settings", str(exc))
            return
        path = save_local_settings(settings)
        self._set_status(f"Settings saved to {path}.")

    # ── Updates ───────────────────────────────────────────────────────────
    def check_updates(self) -> None:
        try:
            settings = self._collect_settings()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid settings", str(exc))
            return
        self.update_button.setEnabled(False)
        self.update_button.setText("Checking…")
        self._set_status("Checking for updates…")

        thread = QThread(self)
        worker = _UpdateWorker(
            current_version=__version__,
            repository=settings.github_repo,
            release_channel=settings.release_channel,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_update_result)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_update_thread)
        self._update_thread = thread
        self._update_worker = worker
        thread.start()

    def _handle_update_result(self, result: UpdateCheckResult) -> None:
        self.update_button.setEnabled(True)
        self.update_button.setText("Check for Updates")
        if result.status == "update_available":
            details = result.latest_version or "unknown version"
            if result.release_url:
                details = f"{details}  ·  {result.release_url}"
            self._set_status(f"Update available: {details}")
            self._offer_update_install(result)
            return
        self._set_status(result.message)

    def _clear_update_thread(self) -> None:
        self._update_thread = None
        self._update_worker = None

    def _offer_update_install(self, result: UpdateCheckResult) -> None:
        if not result.download_url:
            return
        if not can_apply_inplace_update():
            self._set_status(
                f"Update available: {result.latest_version}. "
                "Install flow only enabled in packaged builds."
            )
            return
        choice = QMessageBox.question(
            self,
            "Install update",
            f"Version {result.latest_version} is available. Download and install now?",
        )
        if choice != QMessageBox.StandardButton.Yes:
            return
        self.update_button.setEnabled(False)
        self._set_status("Downloading update package…")

        thread = QThread(self)
        worker = _UpdateInstallWorker(
            download_url=result.download_url,
            version=result.latest_version or __version__,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_install_result)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_install_thread)
        self._install_thread = thread
        self._install_worker = worker
        thread.start()

    def _handle_install_result(self, payload: object) -> None:
        self.update_button.setEnabled(True)
        status, data = payload
        if status == "error":
            self._set_status(f"Update download failed: {data}", is_error=True)
            return
        staged: StagedUpdate = data
        self._set_status(f"Installing update {staged.version}…")
        try:
            launch_staged_update(staged.app_dir)
        except Exception as exc:
            self._set_status(f"Failed to start updater: {exc}", is_error=True)
            return
        QApplication.instance().quit()

    def _clear_install_thread(self) -> None:
        self._install_thread = None
        self._install_worker = None

    def _set_status(self, message: str, *, is_error: bool = False) -> None:
        colour = RED_INACTIVE if is_error else TEXT_MUTED
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {colour}; font-size: 12px;")
