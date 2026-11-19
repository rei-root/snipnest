"""Главное окно приложения.

Сверху — поле ссылки, папка сохранения и кнопки источников. Ниже — список
загрузок, прогресс-бар, статус и сворачиваемый лог.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..components.catalog import GALLERY_DL, YT_DLP, ComponentKind
from ..components.finder import find_component
from ..components.installer import ComponentInstaller
from ..components.state import ComponentState
from ..jobs import DownloadJob, JobEvent
from ..settings import Settings
from ..sources import SourceRegistry
from .bridge import JobEventBridge
from .components_dialog import ComponentsDialog
from .controller import JobController
from .controls import TopControls
from .dnd import DropTargetMixin
from .logarea import LogArea
from .models import JobRow
from .panel import JobsPanel
from .presenter import EventPresenter
from .settings_actions import SettingsActions

__all__ = ["MainWindow"]


class MainWindow(DropTargetMixin, QMainWindow):
    """Окно приложения: ссылка, загрузки, прогресс, статус, лог."""

    def __init__(
        self,
        settings: Settings | None = None,
        registry: SourceRegistry | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Snipnest")
        self.setAcceptDrops(True)
        self.resize(940, 700)

        self._settings = settings if settings is not None else Settings()
        self._registry = registry if registry is not None else SourceRegistry()
        self._bridge = JobEventBridge(self)
        self._counter = 0
        self._controller = JobController(self._bridge, self)

        self._build_ui()
        self._actions = SettingsActions(
            self,
            self._settings,
            self._set_status,
            self._on_destination_changed,
        )
        self._presenter = EventPresenter(self._set_status, self._append_log)
        self._connect_signals()
        self._controls.destination_edit.setText(self._settings.destination)

    # -- построение интерфейса --------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)

        self._controls = TopControls(central)
        root.addWidget(self._controls)

        splitter = QSplitter(self)
        self._panel = JobsPanel(self._cancel_job, self._retry_job, splitter)
        splitter.addWidget(self._panel)
        self._log = LogArea(splitter)
        splitter.addWidget(self._log)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        root.addWidget(self._build_status_row())
        self.setCentralWidget(central)

    def _build_status_row(self) -> QWidget:
        box = QWidget(self)
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)

        self._progress_bar = QProgressBar(box)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar, 1)

        self._status_label = QLabel("Готов к работе", box)
        layout.addWidget(self._status_label)
        return box

    def _connect_signals(self) -> None:
        self._controls.download_button.clicked.connect(self._on_download_clicked)
        self._controls.link_edit.returnPressed.connect(self._on_download_clicked)
        self._controls.choose_destination_button.clicked.connect(self._actions.choose_destination)
        self._controls.token_button.clicked.connect(self._actions.edit_token)
        self._controls.open_pinterest_button.clicked.connect(self._actions.open_pinterest)
        self._controls.gallery_dl_button.clicked.connect(self._actions.choose_gallery_dl)
        self._controls.yt_dlp_button.clicked.connect(self._actions.choose_yt_dlp)
        self._controls.cookies_button.clicked.connect(self._actions.choose_youtube_cookies)
        self._controls.components_button.clicked.connect(self._on_components_clicked)
        self._log.toggle_button.toggled.connect(self._log.set_expanded)
        self._bridge.events_ready.connect(self._drain_events)

    # -- публичный доступ для тестов и проверок ----------------------------

    @property
    def settings(self) -> Settings:
        """Настройки приложения."""
        return self._settings

    @property
    def link_text(self) -> str:
        """Текст в поле ссылки."""
        return self._controls.link_text

    @link_text.setter
    def link_text(self, value: str) -> None:
        self._controls.link_text = value

    @property
    def destination_text(self) -> str:
        """Текущая папка сохранения."""
        return self._controls.destination_text

    @property
    def status_text(self) -> str:
        """Текст в строке статуса."""
        return self._status_label.text()

    @property
    def log_text(self) -> str:
        """Весь накопленный лог."""
        return self._log.text

    @property
    def progress_value(self) -> int:
        """Текущее значение общего прогресс-бара."""
        return self._progress_bar.value()

    def row_for(self, job_id: str) -> JobRow | None:
        """Строка загрузки по идентификатору."""
        return self._panel.row_for(job_id)

    def job_ids(self) -> list[str]:
        """Идентификаторы загрузок в списке."""
        return self._panel.job_ids()

    # -- обработка пользователя --------------------------------------------

    def _on_download_clicked(self) -> None:
        """Поставить ссылку в очередь и запустить загрузку."""
        url = self._controls.link_text.strip()
        if not url:
            self._set_status("Введите ссылку")
            return

        source = self._registry.find(url)
        if source is None:
            self._set_status("Ссылка не распознана: поддерживаются Pinterest и YouTube")
            self._show_error(
                "Непонятная ссылка",
                f"Приложение не умеет работать со ссылкой:\n{url}\n"
                "Поддерживаются ссылки Pinterest и YouTube.",
            )
            return

        missing = source.missing_binary_message(self._settings)
        if missing is not None:
            self._set_status(f"{source.binary.name} не найден")
            self._show_error("Бинарник не найден", missing)
            return

        job = self._build_job(self._next_job_id(), url)
        self._controller.add(job)
        self._panel.add_job(job)
        self._controls.link_text = ""
        self._set_status(f"Загрузка поставлена в очередь: {url}")
        self._controller.start(job)

    # -- работа с загрузками ------------------------------------------------

    def _next_job_id(self) -> str:
        """Идентификатор следующей загрузки."""
        self._counter += 1
        return f"job-{self._counter}"

    def _build_job(self, job_id: str, url: str) -> DownloadJob:
        """Собрать загрузку через слой источников."""
        source = self._registry.find(url)
        if source is None:
            raise ValueError(f"источник для ссылки не найден: {url}")
        return source.build_job(
            job_id,
            url,
            self._settings.destination,
            self._settings,
            self._controller.post_event,
        )

    def _drain_events(self) -> None:
        """Перенести накопленные события в GUI-поток и применить их."""
        for event in self._bridge.take_pending():
            self._apply_event(event)

    def _apply_event(self, event: JobEvent) -> None:
        """Применить событие к интерфейсу."""
        row = self._panel.row_for(event.job_id)
        if row is None:
            return
        self._presenter.apply(row, event)
        self._panel.update_row(event.job_id)
        self._progress_bar.setValue(row.progress_percent)

    def _cancel_job(self, job_id: str) -> None:
        """Остановить выбранную загрузку."""
        if self._controller.cancel(job_id):
            self._panel.update_row(job_id)
            self._set_status("Загрузка остановлена")

    def _retry_job(self, job_id: str) -> None:
        """Повторить загрузку после ошибки или отмены."""
        if self._controller.retry(job_id):
            self._panel.update_row(job_id)
            self._set_status("Загрузка повторена")

    # -- вспомогательное ----------------------------------------------------

    def _append_log(self, text: str) -> None:
        """Дописать строку в лог."""
        self._log.append(text)

    def _set_status(self, text: str) -> None:
        """Обновить строку статуса."""
        self._status_label.setText(text)

    def _show_error(self, title: str, text: str) -> None:
        """Показать сообщение об ошибке.

        Окно неблокирующее: приложение продолжает работать, пока
        сообщение висит на экране.
        """
        box = QMessageBox(
            QMessageBox.Icon.Warning,
            title,
            text,
            QMessageBox.StandardButton.Ok,
            self,
        )
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        box.open()

    def _on_destination_changed(self, destination: str) -> None:
        """Папка сохранения изменилась: показать её."""
        self._controls.destination_edit.setText(destination)

    # -- компоненты ---------------------------------------------------------

    def _on_components_clicked(self) -> None:
        """Кнопка «Компоненты…»: открыть мастер установки."""
        self.show_component_wizard()

    def show_component_wizard(self) -> None:
        """Показать мастер установки компонентов.

        После мастера пути к установленным компонентам попадают в настройки,
        а отметка «мастер уже показывали» сохраняется: при следующем запуске
        он не появится сам.
        """
        dialog = ComponentsDialog(self, installer=ComponentInstaller())
        dialog.exec()
        self._apply_installed_components()
        state = ComponentState()
        state.mark_wizard_done()
        state.save()

    def show_component_wizard_if_needed(self) -> None:
        """Показать мастер при первом запуске."""
        if ComponentState().wizard_done:
            return
        self.show_component_wizard()

    def _apply_installed_components(self) -> None:
        """Прописать пути к установленным компонентам в настройки.

        Путь, заданный человеком руками, не перетирается: мастер дописывает
        только пустые.
        """
        changed = False
        for spec, setting in (
            (GALLERY_DL, "gallery_dl_path"),
            (YT_DLP, "yt_dlp_path"),
        ):
            if getattr(self._settings, setting):
                continue
            location = find_component(spec)
            if location is None:
                continue
            path = location.path
            if spec.kind is ComponentKind.PIP:
                path = path.parent / "bin" / spec.binary
            if not path.is_file():
                continue
            setattr(self._settings, setting, str(path))
            changed = True
        if changed:
            self._settings.save()

    # -- drag and drop ------------------------------------------------------

    def _accept_dropped_link(self, url: str) -> None:
        """Ссылка, перетащенная из браузера, попала в поле."""
        self._controls.link_text = url
        self._set_status("Ссылка вставлена")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Остановить загрузки перед закрытием окна.

        Иначе висящий поток QThread роняет приложение при выходе.
        """
        self.shutdown()
        super().closeEvent(event)

    def shutdown(self) -> None:
        """Остановить все загрузки и дождаться потоков."""
        self._controller.shutdown()
