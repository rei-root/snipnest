"""Настройки приложения: папка сохранения и токен Pinterest.

Путь хранится в конфиге рядом с другими настройками. Токен — в системном
хранилище (keyring), а не в открытом файле.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "Settings",
    "DEFAULT_DESTINATION",
    "KeyringStore",
    "FileSecretStore",
]

DEFAULT_DESTINATION = Path.home() / "Изображения" / "Pinterest"

CONFIG_DIR = Path.home() / ".config" / "gallary-downloader"
CONFIG_FILE = CONFIG_DIR / "settings.json"

_KEYRING_SERVICE = "gallary-downloader"
_KEYRING_USERNAME = "pinterest-token"


class KeyringStore:
    """Хранение секрета в системном хранилище (libsecret / kwallet)."""

    def __init__(self, service: str = _KEYRING_SERVICE, username: str = _KEYRING_USERNAME) -> None:
        self._service = service
        self._username = username

    def get(self) -> str | None:
        raise NotImplementedError

    def set(self, secret: str) -> None:
        raise NotImplementedError

    def delete(self) -> None:
        raise NotImplementedError


class FileSecretStore:
    """Запасное хранилище: файл с правами 600. Используется, если keyring недоступен."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (CONFIG_DIR / "secret")

    def get(self) -> str | None:
        raise NotImplementedError

    def set(self, secret: str) -> None:
        raise NotImplementedError

    def delete(self) -> None:
        raise NotImplementedError


class Settings:
    """Настройки приложения: папка сохранения, путь к gallery-dl, токен."""

    def __init__(
        self,
        config_path: Path | None = None,
        secret_store: KeyringStore | FileSecretStore | None = None,
    ) -> None:
        self._config_path = config_path or CONFIG_FILE
        self._secret_store = secret_store or KeyringStore()
        self.destination: str = str(DEFAULT_DESTINATION)
        self.gallery_dl_path: str = ""
        self.load()

    def load(self) -> None:
        """Прочитать настройки из конфига. Отсутствие конфига — не ошибка."""
        raise NotImplementedError

    def save(self) -> None:
        """Записать настройки в конфиг."""
        raise NotImplementedError

    @property
    def token(self) -> str | None:
        """Токен Pinterest из системного хранилища."""
        raise NotImplementedError

    def set_token(self, token: str) -> None:
        """Сохранить токен Pinterest в системном хранилище."""
        raise NotImplementedError

    def clear_token(self) -> None:
        """Удалить токен Pinterest."""
        raise NotImplementedError
