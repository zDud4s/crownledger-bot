from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
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
from desktop.version import APP_NAME, __version__


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
            staged_update = stage_update_from_release(
                download_url=self.download_url,
                version=self.version,
            )
            self.finished.emit(("success", staged_update))
        except Exception as exc:
            self.finished.emit(("error", str(exc)))


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
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        root.addWidget(title)

        self.version_label = QLabel()
        self.path_label = QLabel()
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.default_clan_input = QLineEdit()
        self.last_player_input = QLineEdit()
        self.github_repo_input = QLineEdit()
        self.github_repo_input.setPlaceholderText("owner/repository")

        self.release_channel_input = QComboBox()
        self.release_channel_input.addItems(["stable", "beta"])

        self.war_history_checkbox = QCheckBox("Enable war history scraping")

        form.addRow("App version", self.version_label)
        form.addRow("Local data path", self.path_label)
        form.addRow("Clash API token", self.token_input)
        form.addRow("Default clan tag", self.default_clan_input)
        form.addRow("Last player tag", self.last_player_input)
        form.addRow("GitHub repo", self.github_repo_input)
        form.addRow("Release channel", self.release_channel_input)
        form.addRow("", self.war_history_checkbox)

        root.addLayout(form)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.reload_button = QPushButton("Reload")
        self.save_button = QPushButton("Save settings")
        self.update_button = QPushButton("Check for updates")

        self.reload_button.clicked.connect(self.reload_settings)
        self.save_button.clicked.connect(self.save_settings)
        self.update_button.clicked.connect(self.check_updates)

        button_row.addWidget(self.reload_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.update_button)
        button_row.addStretch(1)

        root.addLayout(button_row)

        self.status_label = QLabel("Settings not loaded yet.")
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        root.addWidget(self.status_label)
        root.addStretch(1)

    def reload_settings(self) -> None:
        result = load_local_settings_result()
        settings = result.settings
        self.version_label.setText(f"{APP_NAME} {__version__}")
        self.path_label.setText(str(get_app_data_dir()))
        self.token_input.setText(settings.clash_api_token)
        self.default_clan_input.setText(settings.default_clan_tag)
        self.last_player_input.setText(settings.last_used_player_tag)
        self.github_repo_input.setText(settings.github_repo)
        self.war_history_checkbox.setChecked(settings.war_history_enabled)

        idx = self.release_channel_input.findText(settings.release_channel)
        self.release_channel_input.setCurrentIndex(0 if idx < 0 else idx)
        if result.error:
            self.status_label.setText(f"Settings fallback loaded. {result.error}")
        else:
            self.status_label.setText("Settings loaded from local storage.")

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
        self.status_label.setText(f"Settings saved to {path}.")

    def check_updates(self) -> None:
        try:
            settings = self._collect_settings()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid settings", str(exc))
            return

        self.update_button.setEnabled(False)
        self.status_label.setText("Checking for updates...")

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
        if result.status == "update_available":
            details = result.latest_version or "unknown version"
            if result.release_url:
                details = f"{details} | {result.release_url}"
            self.status_label.setText(f"Update available: {details}")
            self._offer_update_install(result)
            return

        self.status_label.setText(result.message)

    def _clear_update_thread(self) -> None:
        self._update_thread = None
        self._update_worker = None

    def _offer_update_install(self, result: UpdateCheckResult) -> None:
        if not result.download_url:
            return

        if not can_apply_inplace_update():
            self.status_label.setText(
                f"Update available: {result.latest_version}. Install flow is only enabled in packaged builds."
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
        self.status_label.setText("Downloading update package...")

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
            self.status_label.setText(f"Update download failed: {data}")
            return

        staged_update: StagedUpdate = data
        self.status_label.setText(f"Installing update {staged_update.version}...")
        try:
            launch_staged_update(staged_update.app_dir)
        except Exception as exc:
            self.status_label.setText(f"Failed to start updater: {exc}")
            return

        QApplication.instance().quit()

    def _clear_install_thread(self) -> None:
        self._install_thread = None
        self._install_worker = None
