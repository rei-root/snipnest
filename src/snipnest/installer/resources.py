"""Ресурсы установщика: ярлык и иконка.

Они лежат внутри собранного установщика, поэтому окну не нужно ничего
распаковывать из образа приложения. В исходниках те же файлы берутся из
каталогов packaging/ и logo/.

Иконка приложения одна — векторная (logo/snipnest.svg). PNG размеров, которые
ждёт тема иконок, получаются из неё средствами Qt.
"""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

from ..branding import app_logo_path, render_png

__all__ = [
    "build_info",
    "desktop_file_text",
    "icon_bytes",
    "icon_png",
    "icon_sizes",
]

#: Размеры иконок, которые ставит установщик.
ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256, 512)

_DESKTOP_NAME = "snipnest.desktop"

#: Файл со сведениями о сборке: его кладёт сборщик установщика.
_BUILD_INFO_NAME = "installer-build-info.json"


def _bundle_dir() -> Path | None:
    """Каталог ресурсов собранного приложения (PyInstaller) или None."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None


def _find(name: str, relative: Path) -> Path | None:
    """Найти ресурс: сначала в сборке, потом в дереве исходников."""
    bundle = _bundle_dir()
    if bundle is not None:
        candidate = bundle / name
        if candidate.is_file():
            return candidate
    root = Path(__file__).resolve().parents[3]
    candidate = root / relative / name
    return candidate if candidate.is_file() else None


@lru_cache(maxsize=1)
def desktop_file_text() -> str:
    """Текст ярлыка приложения."""
    path = _find(_DESKTOP_NAME, Path("packaging"))
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def icon_bytes() -> bytes:
    """Содержимое векторной иконки приложения."""
    path = app_logo_path()
    if not path.is_file():
        return b""
    return path.read_bytes()


def icon_png(size: int) -> bytes:
    """PNG заданного размера, собранный из логотипа."""
    return render_png(size)


def icon_sizes() -> tuple[int, ...]:
    """Размеры иконок, которые ставит установщик."""
    return ICON_SIZES


@lru_cache(maxsize=1)
def build_info() -> dict[str, str]:
    """Сведения о сборке: версия, минимальная glibc, адрес релиза.

    Их записывает сборщик установщика: без них установщик не знает, какую
    версию приложения качать и какой образ подходит системе.
    """
    path: Path | None = None
    from_env = os.environ.get("SNIPNEST_BUILD_INFO", "").strip()
    if from_env:
        candidate = Path(from_env)
        path = candidate if candidate.is_file() else None
    if path is None:
        bundle = _bundle_dir()
        if bundle is not None:
            candidate = bundle / _BUILD_INFO_NAME
            path = candidate if candidate.is_file() else None
    if path is None:
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}
