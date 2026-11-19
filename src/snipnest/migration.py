"""Перенос настроек и токена со старого имени приложения.

Единственный модуль, где прежнее имя названо прямо: переносить данные
некогда, не назвав, откуда. Перенос выполняется один раз — новые данные
никогда не перетираются старыми.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import keyring

from .settings import KEYRING_USERNAME

__all__ = [
    "LEGACY_CONFIG_DIR",
    "LEGACY_KEYRING_SERVICE",
    "migrate_settings",
    "migrate_token",
    "migrate_legacy_data",
]

LEGACY_CONFIG_DIR = Path.home() / ".config" / "gallary-downloader"
LEGACY_KEYRING_SERVICE = "gallary-downloader"

_SETTINGS_FILE = "settings.json"
_SECRET_FILE = "secret"


def migrate_settings(legacy_dir: Path, config_dir: Path) -> bool:
    """Переносит конфиг и файловый секрет из старого каталога в новый.

    Возвращает True, если что-то перенесено. Уже существующие новые файлы
    не трогаются: перенос дополняет, а не заменяет.
    """
    if not legacy_dir.is_dir():
        return False
    moved = False
    for name in (_SETTINGS_FILE, _SECRET_FILE):
        source = legacy_dir / name
        target = config_dir / name
        if not source.is_file() or target.exists():
            continue
        config_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if name == _SECRET_FILE:
            os.chmod(target, 0o600)
        moved = True
    return moved


def migrate_token(
    legacy_service: str,
    service: str,
    username: str = KEYRING_USERNAME,
) -> bool:
    """Переносит токен из старого сервиса хранилища в новый.

    Возвращает True, если токен перенесён. Если под новым именем токен уже
    есть, старый сервис не трогается. Недоступное хранилище — не ошибка:
    приложение просто не находит токен, как и до переноса.
    """
    try:
        if keyring.get_password(service, username):
            return False
        legacy = keyring.get_password(legacy_service, username)
        if not legacy:
            return False
        keyring.set_password(service, username, legacy)
    except Exception:
        return False
    return True


def migrate_legacy_data(config_dir: Path, keyring_service: str) -> bool:
    """Переносит настройки и токен со старого имени приложения.

    Возвращает True, если что-то перенесено.
    """
    moved = migrate_settings(LEGACY_CONFIG_DIR, config_dir)
    if migrate_token(LEGACY_KEYRING_SERVICE, keyring_service):
        moved = True
    return moved
