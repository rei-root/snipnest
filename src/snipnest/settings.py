"""Настройки приложения: папка сохранения и токен Pinterest.

Путь хранится в конфиге рядом с другими настройками. Токен — в системном
хранилище (keyring), а не в открытом файле.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import keyring

from .formats import DEFAULT_AUDIO_FORMAT, DEFAULT_IMAGE_FORMAT, DEFAULT_VIDEO_FORMAT

__all__ = [
    "Settings",
    "DEFAULT_DESTINATION",
    "KeyringStore",
    "FileSecretStore",
    "CONFIG_DIR",
    "CONFIG_FILE",
    "KEYRING_SERVICE",
    "KEYRING_USERNAME",
]

DEFAULT_DESTINATION = Path.home() / "Изображения" / "Pinterest"

CONFIG_DIR = Path.home() / ".config" / "snipnest"
CONFIG_FILE = CONFIG_DIR / "settings.json"

KEYRING_SERVICE = "snipnest"
KEYRING_USERNAME = "pinterest-token"


class KeyringStore:
    """Хранение секрета в системном хранилище (libsecret / kwallet)."""

    def __init__(self, service: str = KEYRING_SERVICE, username: str = KEYRING_USERNAME) -> None:
        self._service = service
        self._username = username

    def get(self) -> str | None:
        return keyring.get_password(self._service, self._username)

    def set(self, secret: str) -> None:
        keyring.set_password(self._service, self._username, secret)

    def delete(self) -> None:
        try:
            keyring.delete_password(self._service, self._username)
        except keyring.errors.PasswordDeleteError:
            return


class FileSecretStore:
    """Запасное хранилище: файл с правами 600. Используется, если keyring недоступен."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (CONFIG_DIR / "secret")

    def get(self) -> str | None:
        try:
            return self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def set(self, secret: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(descriptor, secret.encode("utf-8"))
        finally:
            os.close(descriptor)
        os.chmod(self._path, 0o600)

    def delete(self) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            return


class Settings:
    """Настройки приложения: папка сохранения, пути к бинарникам, токен."""

    def __init__(
        self,
        config_path: Path | None = None,
        secret_store: KeyringStore | FileSecretStore | None = None,
    ) -> None:
        self._config_path = config_path or CONFIG_FILE
        self._secret_store = secret_store or KeyringStore()
        self.destination: str = str(DEFAULT_DESTINATION)
        self.gallery_dl_path: str = ""
        self.yt_dlp_path: str = ""
        self.cookies_browser: str = ""
        self.cookies_file: str = ""
        self.image_format: str = DEFAULT_IMAGE_FORMAT
        self.video_format: str = DEFAULT_VIDEO_FORMAT
        self.audio_format: str = DEFAULT_AUDIO_FORMAT
        self.load()

    def load(self) -> None:
        """Прочитать настройки из конфига. Отсутствие конфига — не ошибка."""
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):
            return
        destination = data.get("destination")
        if isinstance(destination, str) and destination:
            self.destination = destination
        gallery_dl_path = data.get("gallery_dl_path")
        if isinstance(gallery_dl_path, str):
            self.gallery_dl_path = gallery_dl_path
        yt_dlp_path = data.get("yt_dlp_path")
        if isinstance(yt_dlp_path, str):
            self.yt_dlp_path = yt_dlp_path
        cookies_browser = data.get("cookies_browser")
        if isinstance(cookies_browser, str):
            self.cookies_browser = cookies_browser
        cookies_file = data.get("cookies_file")
        if isinstance(cookies_file, str):
            self.cookies_file = cookies_file
        image_format = data.get("image_format")
        if isinstance(image_format, str) and image_format:
            self.image_format = image_format
        video_format = data.get("video_format")
        if isinstance(video_format, str) and video_format:
            self.video_format = video_format
        audio_format = data.get("audio_format")
        if isinstance(audio_format, str) and audio_format:
            self.audio_format = audio_format

    def save(self) -> None:
        """Записать настройки в конфиг."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "destination": self.destination,
            "gallery_dl_path": self.gallery_dl_path,
            "yt_dlp_path": self.yt_dlp_path,
            "cookies_browser": self.cookies_browser,
            "cookies_file": self.cookies_file,
            "image_format": self.image_format,
            "video_format": self.video_format,
            "audio_format": self.audio_format,
        }
        self._config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @property
    def token(self) -> str | None:
        """Токен Pinterest из системного хранилища."""
        try:
            return self._secret_store.get()
        except Exception:
            return None

    def set_token(self, token: str) -> None:
        """Сохранить токен Pinterest в системном хранилище."""
        try:
            self._secret_store.set(token)
        except Exception:
            fallback = FileSecretStore(self._config_path.parent / "secret")
            fallback.set(token)
            self._secret_store = fallback

    def clear_token(self) -> None:
        """Удалить токен Pinterest."""
        try:
            self._secret_store.delete()
        except Exception:
            return
