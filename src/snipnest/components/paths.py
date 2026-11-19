"""Пути компонентов: каталог пользователя, каталог пакета, рантайм Python.

Установленные компоненты лежат в двух местах:

* ``~/.local/share/snipnest/components`` — то, что поставил сам человек;
* ``/usr/lib/snipnest/components`` — то, что приехало с пакетом .deb.

Переносимый Python — часть артефакта: в одном файле он разворачивается
в каталог PyInstaller, в каталоговой сборке лежит рядом с программой.
"""

from __future__ import annotations

import sys
from pathlib import Path

__all__ = [
    "component_bin_dirs",
    "component_dir",
    "runtime_python",
    "system_components_root",
    "user_components_root",
    "user_runtime_dir",
]

SYSTEM_COMPONENTS_ROOT = Path("/usr/lib/snipnest/components")

#: Относительный путь каталога компонентов в домашней папке.
USER_COMPONENTS_PARTS = (".local", "share", "snipnest", "components")


def user_components_root() -> Path:
    """Каталог компонентов пользователя."""
    return Path.home().joinpath(*USER_COMPONENTS_PARTS)


def system_components_root() -> Path:
    """Каталог компонентов, поставленных пакетом .deb."""
    return SYSTEM_COMPONENTS_ROOT


def user_runtime_dir() -> Path:
    """Каталог переносимого Python в домашней папке.

    Лаунчеры установленных компонентов ссылаются на этот Python: путь
    внутри AppImage меняется при каждом запуске образа, а путь в домашней
    папке — нет.
    """
    return Path.home().joinpath(*USER_COMPONENTS_PARTS[:-1], "runtime", "python")


def component_dir(component_id: str, *, root: Path | None = None) -> Path:
    """Каталог компонента внутри корня."""
    base = root if root is not None else user_components_root()
    return base / component_id


def component_bin_dirs(
    *, user_root: Path | None = None, system_root: Path | None = None
) -> list[Path]:
    """Каталоги запуска установленных компонентов.

    В них лежат запускающие файлы (``bin/gallery-dl`` и подобные).
    """
    roots = [
        user_root if user_root is not None else user_components_root(),
        system_root if system_root is not None else system_components_root(),
    ]
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            bin_dir = child / "bin"
            if bin_dir.is_dir():
                found.append(bin_dir)
    return found


def runtime_python() -> Path | None:
    """Переносимый Python из артефакта или None, если его нет."""
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "runtime" / "python" / "bin" / "python3")
    executable = Path(sys.executable).resolve()
    candidates.append(executable.parent.parent / "runtime" / "python" / "bin" / "python3")
    candidates.append(executable.parent / "runtime" / "python" / "bin" / "python3")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
