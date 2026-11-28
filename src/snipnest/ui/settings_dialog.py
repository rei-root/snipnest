"""Окно настроек: всё в одном месте.

Те же значения, что и в меню «Файл», — собраны здесь: папка сохранения,
токен Pinterest, cookies YouTube, пути к бинарникам и тема окраски.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..settings import Settings
from .settings_actions import SettingsActions
from .theme import THEME_LABELS, THEMES, Theme

__all__ = ["SettingsDialog"]


class SettingsDialog(QDialog):
    """Окно настроек приложения."""

    #: Выбрана тема: окно применяет её и запоминает.
    theme_changed = Signal(object)

    def __init__(
        self,
        settings: Settings,
        actions: SettingsActions,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setModal(True)
        self.resize(560, 420)
        self._settings = settings
        self._actions = actions

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_appearance())
        layout.addWidget(self._build_downloads())

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setText("Закрыть")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.refresh()

    # -- разделы -----------------------------------------------------------

    def _build_appearance(self) -> QGroupBox:
        """Раздел «Внешний вид»: тема окраски."""
        box = QGroupBox("Внешний вид", self)
        row = QHBoxLayout(box)
        row.addWidget(QLabel("Тема:", box))

        self.theme_combo = QComboBox(box)
        for theme in THEMES:
            self.theme_combo.addItem(THEME_LABELS[theme], theme.value)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_selected)
        row.addWidget(self.theme_combo, 1)
        return box

    def _build_downloads(self) -> QGroupBox:
        """Раздел «Загрузка»: папка, токен, cookies и пути к бинарникам."""
        box = QGroupBox("Загрузка", self)
        layout = QVBoxLayout(box)

        self.destination_edit = QLineEdit(box)
        self.destination_edit.setReadOnly(True)
        destination_row = QHBoxLayout()
        destination_row.addWidget(QLabel("Папка сохранения:", box))
        destination_row.addWidget(self.destination_edit, 1)
        self.destination_button = QPushButton("Выбрать папку…", box)
        self.destination_button.clicked.connect(self._on_destination)
        destination_row.addWidget(self.destination_button)
        layout.addLayout(destination_row)

        token_row = QHBoxLayout()
        token_row.addWidget(QLabel("Токен Pinterest:", box))
        self.token_status = QLabel("", box)
        token_row.addWidget(self.token_status, 1)
        self.token_button = QPushButton("Задать токен…", box)
        self.token_button.clicked.connect(self._on_token)
        token_row.addWidget(self.token_button)
        layout.addLayout(token_row)

        cookies_row = QHBoxLayout()
        cookies_row.addWidget(QLabel("Cookies YouTube:", box))
        self.cookies_status = QLabel("", box)
        cookies_row.addWidget(self.cookies_status, 1)
        self.cookies_button = QPushButton("Выбрать источник…", box)
        self.cookies_button.clicked.connect(self._on_cookies)
        cookies_row.addWidget(self.cookies_button)
        layout.addLayout(cookies_row)

        self.gallery_dl_edit = QLineEdit(box)
        self.gallery_dl_edit.setReadOnly(True)
        gallery_row = QHBoxLayout()
        gallery_row.addWidget(QLabel("Путь к gallery-dl:", box))
        gallery_row.addWidget(self.gallery_dl_edit, 1)
        self.gallery_dl_button = QPushButton("Выбрать…", box)
        self.gallery_dl_button.clicked.connect(self._on_gallery_dl)
        gallery_row.addWidget(self.gallery_dl_button)
        layout.addLayout(gallery_row)

        self.yt_dlp_edit = QLineEdit(box)
        self.yt_dlp_edit.setReadOnly(True)
        yt_dlp_row = QHBoxLayout()
        yt_dlp_row.addWidget(QLabel("Путь к yt-dlp:", box))
        yt_dlp_row.addWidget(self.yt_dlp_edit, 1)
        self.yt_dlp_button = QPushButton("Выбрать…", box)
        self.yt_dlp_button.clicked.connect(self._on_yt_dlp)
        yt_dlp_row.addWidget(self.yt_dlp_button)
        layout.addLayout(yt_dlp_row)

        return box

    # -- действия ----------------------------------------------------------

    def refresh(self) -> None:
        """Показать текущие значения настроек."""
        theme = Theme.parse(self._settings.theme)
        index = self.theme_combo.findData(theme.value)
        if index >= 0:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(index)
            self.theme_combo.blockSignals(False)

        self.destination_edit.setText(self._settings.destination)
        self.token_status.setText("задан" if self._settings.token else "не задан")
        self.cookies_status.setText(self._settings.cookies_browser or self._settings.cookies_file)
        self.gallery_dl_edit.setText(self._settings.gallery_dl_path)
        self.yt_dlp_edit.setText(self._settings.yt_dlp_path)

    def _on_theme_selected(self, _index: int) -> None:
        """Выбрана тема: сообщаем окну."""
        value = self.theme_combo.currentData()
        theme = Theme.parse(str(value))
        self.theme_changed.emit(theme)

    def _on_destination(self) -> None:
        """Выбрать папку сохранения."""
        self._actions.choose_destination()
        self.refresh()

    def _on_token(self) -> None:
        """Задать токен Pinterest."""
        self._actions.edit_token()
        self.refresh()

    def _on_cookies(self) -> None:
        """Выбрать источник cookies для YouTube."""
        self._actions.choose_youtube_cookies()
        self.refresh()

    def _on_gallery_dl(self) -> None:
        """Указать путь к gallery-dl."""
        self._actions.choose_gallery_dl()
        self.refresh()

    def _on_yt_dlp(self) -> None:
        """Указать путь к yt-dlp."""
        self._actions.choose_yt_dlp()
        self.refresh()
