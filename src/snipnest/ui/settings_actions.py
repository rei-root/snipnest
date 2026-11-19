"""Действия с настройками: папка сохранения, токен, путь к gallery-dl.

Отдельный модуль, чтобы окно не занималось деталями диалогов.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget

from ..settings import Settings
from .dialogs import TokenDialog, choose_directory, choose_executable

__all__ = ["SettingsActions"]

PINTEREST_URL = "https://www.pinterest.com/"


class SettingsActions:
    """Операции над настройками, которые зовёт окно."""

    def __init__(
        self,
        parent: QWidget,
        settings: Settings,
        on_status: Callable[[str], None],
        on_destination_changed: Callable[[str], None],
    ) -> None:
        self._parent = parent
        self._settings = settings
        self._on_status = on_status
        self._on_destination_changed = on_destination_changed

    @property
    def settings(self) -> Settings:
        """Настройки приложения."""
        return self._settings

    def choose_destination(self) -> None:
        """Выбрать папку сохранения и запомнить её."""
        selected = choose_directory(self._parent, self._settings.destination)
        if selected is None:
            return
        self._settings.destination = selected
        self._on_destination_changed(selected)
        self.save()
        self._on_status(f"Папка сохранения: {selected}")

    def edit_token(self) -> None:
        """Ввести и сохранить токен Pinterest."""
        dialog = TokenDialog(self._parent, self._settings.token or "")
        if dialog.exec() != TokenDialog.DialogCode.Accepted:
            return
        token = dialog.token()
        if not token:
            self._on_status("Токен не задан")
            return
        self._settings.set_token(token)
        self._on_status("Токен Pinterest сохранён в системном хранилище")

    def choose_gallery_dl(self) -> None:
        """Указать путь к бинарнику gallery-dl вручную."""
        selected = choose_executable(self._parent, self._settings.gallery_dl_path)
        if selected is None:
            return
        self._settings.gallery_dl_path = selected
        self.save()
        self._on_status(f"Путь к gallery-dl: {selected}")

    def open_pinterest(self) -> None:
        """Открыть Pinterest в браузере."""
        if not QDesktopServices.openUrl(QUrl(PINTEREST_URL)):
            webbrowser.open(PINTEREST_URL)
        self._on_status("Открыт Pinterest в браузере")

    def save(self) -> None:
        """Сохранить настройки, не роняя приложение при ошибке записи."""
        try:
            self._settings.save()
        except OSError as exc:
            self._on_status(f"Не удалось сохранить настройки: {exc}")
