"""Главное окно приложения.

Сверху — строка меню и шапка с символом приложения, поле ссылки, папка
сохранения и выбор формата. Ниже — список загрузок, прогресс-бар, статус и
сворачиваемый лог.
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

from ..branding import app_icon
from ..components.catalog import GALLERY_DL, YT_DLP, ComponentKind
from ..components.finder import find_component
from ..components.installer import ComponentInstaller
from ..components.state import ComponentState
from ..formats import FormatKind, SaveFormat
from ..jobs import DownloadJob, JobEvent
from ..settings import Settings
from ..sources import SourceKind, SourceRegistry
from .about import AboutDialog
from .bridge import JobEventBridge
from .components_dialog import ComponentsDialog
from .controller import JobController
from .controls import TopControls
from .dnd import DropTargetMixin
from .format_selector import FormatSelector
from .imaging import convert_image
from .logarea import LogArea
from .menus import AppMenuBar
from .models import JobRow
from .panel import JobsPanel
from .presenter import EventPresenter
from .settings_actions import SettingsActions
from .settings_dialog import SettingsDialog
from .theme import Theme, apply_theme

__all__ = ["MainWindow"]


class MainWindow(DropTargetMixin, QMainWindow):
    """Окно приложения: меню, ссылка, загрузки, прогресс, статус, лог."""

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

        apply_theme(Theme.parse(self._settings.theme))
        self.setWindowIcon(app_icon())

        self._build_ui()
        self._actions = SettingsActions(
            self,
            self._settings,
            self._set_status,
            self._on_destination_changed,
        )
        self._presenter = EventPresenter(self._set_status, self._append_log)
        self._build_menu()
        self._connect_signals()
        self._controls.destination_edit.setText(self._settings.destination)
        self._controls.format_selector.set_choices(
            image_id=self._settings.image_format,
            video_id=self._settings.video_format,
            audio_id=self._settings.audio_format,
        )
        self._update_format_choices("")
        self._menu.set_theme(Theme.parse(self._settings.theme))

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

    def _build_menu(self) -> None:
        """Строка меню: настройки, тема, лог и справка."""
        self._menu = AppMenuBar(
            self,
            on_destination=self._actions.choose_destination,
            on_settings=self.show_settings,
            on_token=self._actions.edit_token,
            on_cookies=self._actions.choose_youtube_cookies,
            on_gallery_dl=self._actions.choose_gallery_dl,
            on_yt_dlp=self._actions.choose_yt_dlp,
            on_components=self.show_component_wizard,
            on_exit=self._on_exit,
            on_theme=self.set_theme,
            on_log_toggled=self._on_log_toggled,
            on_about=self.show_about,
        )
        self.setMenuBar(self._menu)

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
        self._log.toggle_button.toggled.connect(self._on_log_button_toggled)
        self._bridge.events_ready.connect(self._drain_events)
        self._controls.link_edit.textChanged.connect(self._on_link_changed)
        self._controls.format_selector.changed.connect(self._on_format_changed)

    # -- тема ---------------------------------------------------------------

    def set_theme(self, theme: Theme) -> None:
        """Сменить тему окраски: применить, запомнить, обновить символ."""
        apply_theme(theme)
        self._settings.theme = theme.value
        self._actions.save()
        self._controls.refresh_header()
        self._menu.set_theme(theme)

    # -- окна ---------------------------------------------------------------

    def show_settings(self) -> None:
        """Открыть окно настроек."""
        dialog = SettingsDialog(self._settings, self._actions, self)
        dialog.theme_changed.connect(self.set_theme)
        dialog.exec()

    def show_about(self) -> None:
        """Открыть окно «О программе»."""
        AboutDialog(self).exec()

    def _on_exit(self) -> None:
        """Пункт меню «Выход»: закрыть окно."""
        self.close()

    def _on_log_toggled(self, visible: bool) -> None:
        """Пункт меню «Показать лог»: показать или свернуть область лога."""
        if self._log.expanded == visible:
            return
        self._log.set_expanded(visible)
        self._log.toggle_button.setChecked(visible)

    def _on_log_button_toggled(self, expanded: bool) -> None:
        """Кнопка лога: показать или свернуть область лога."""
        self._log.set_expanded(expanded)
        self._menu.set_log_visible(expanded)

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

    @property
    def format_selector(self) -> FormatSelector:
        """Выбор формата сохранения."""
        return self._controls.format_selector

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

        job = self._build_job(self._next_job_id(), url, self.format_selector.selected_format())
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

    def _build_job(self, job_id: str, url: str, save_format: SaveFormat) -> DownloadJob:
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
            save_format=save_format,
            converter=convert_image,
        )

    # -- выбор формата ------------------------------------------------------

    def _on_link_changed(self, text: str) -> None:
        """Ссылка изменилась: форматы под неё."""
        self._update_format_choices(text)

    def _update_format_choices(self, text: str) -> None:
        """Показать форматы для того, что в поле ссылки.

        Формат выбирают после того, как вставили и распознали ссылку: до
        этого список неактивен.
        """
        url = text.strip()
        source = self._registry.find(url) if url else None
        is_video = source is not None and source.kind is SourceKind.YOUTUBE
        self._controls.format_selector.set_kind(FormatKind.VIDEO if is_video else FormatKind.IMAGE)
        self._controls.format_selector.setEnabled(source is not None)

    def _on_format_changed(self) -> None:
        """Владелец сменил формат: запомним выбор."""
        selector = self._controls.format_selector
        self._settings.image_format = selector.image_id
        self._settings.video_format = selector.video_id
        self._settings.audio_format = selector.audio_id
        self._settings.save()

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
