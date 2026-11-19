"""Внешние программы приложения: поиск бинарника и окружение для запуска.

Исполнители живут в системе, а не в venv приложения: бинарник ищется по
своему имени в PATH и в известных местах, а окружение ребёнка очищается от
каталогов приложения — иначе обёртка на python3 упадёт с ModuleNotFoundError.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .components.paths import component_bin_dirs

__all__ = [
    "build_child_env",
    "find_component_binary",
    "find_executable",
    "find_gallery_dl",
    "find_yt_dlp",
]


def _is_working_binary(candidate: str | os.PathLike[str]) -> bool:
    """Проверить, что кандидат запускается и отвечает на ``--version``."""
    try:
        result = subprocess.run(
            [str(candidate), "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _executable_candidates(name: str) -> list[str]:
    """Кандидаты в порядке предпочтения.

    Сначала компоненты, поставленные мастером установки: человек выбрал их
    сам, и версия известна. Потом PATH, потом известные места.
    """
    candidates: list[str] = []
    for directory in component_bin_dirs():
        candidates.append(str(directory / name))
    found = shutil.which(name)
    if found:
        candidates.append(found)
    candidates.extend(
        [
            f"/usr/bin/{name}",
            f"/usr/local/bin/{name}",
            str(Path.home() / ".local" / "bin" / name),
        ]
    )
    unique: list[str] = []
    for candidate in candidates:
        resolved = str(Path(candidate).expanduser().resolve())
        if resolved not in unique:
            unique.append(resolved)
    return unique


def find_executable(name: str, explicit: str | None = None) -> str | None:
    """Найти рабочий бинарник: явный путь, затем известные места.

    Общий поиск для всех внешних исполнителей приложения: gallery-dl и
    yt-dlp ищутся одинаково.
    """
    if explicit:
        explicit_candidate = Path(explicit).expanduser()
        if (
            explicit_candidate.is_file()
            and os.access(explicit_candidate, os.X_OK)
            and _is_working_binary(explicit_candidate)
        ):
            return str(explicit_candidate.resolve())
        return None
    for candidate in _executable_candidates(name):
        candidate_path = Path(candidate)
        if (
            candidate_path.is_file()
            and os.access(candidate_path, os.X_OK)
            and _is_working_binary(candidate_path)
        ):
            return candidate
    return None


def find_gallery_dl(explicit: str | None = None) -> str | None:
    """Найти рабочий бинарник gallery-dl: явный путь, затем известные места."""
    return find_executable("gallery-dl", explicit)


def find_component_binary(name: str) -> str | None:
    """Исполняемый файл из каталогов установленных компонентов.

    Без проверки запуска: так находятся и те программы, у которых нет
    ключа ``--version`` (ffmpeg, например).
    """
    for directory in component_bin_dirs():
        candidate = directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def find_yt_dlp(explicit: str | None = None) -> str | None:
    """Найти рабочий бинарник yt-dlp: явный путь, затем известные места."""
    return find_executable("yt-dlp", explicit)


def build_child_env() -> dict[str, str]:
    """Окружение для запуска внешней программы.

    Приложение часто живёт в своём venv, и его ``bin`` стоит первым в
    ``PATH``. Многие установки gallery-dl — это bash-обёртки вида
    ``exec python3 .../gallery_dl/__main__.py``, поэтому ``python3`` ищется
    в ``PATH`` и попадает в venv приложения. Там нет ``requests``, и
    бинарник падает с ``ModuleNotFoundError`` вместо скачивания.

    Поэтому из ``PATH`` убирается каталог venv самого приложения, а
    ``PYTHONHOME``/``PYTHONPATH`` приложения сбрасываются: иначе они
    подменят интерпретатор ребёнка. Остальные каталоги на месте, поэтому
    ``/usr/bin/gallery-dl`` с закреплённым shebang и системный ``python3``
    продолжают работать.
    """
    env = dict(os.environ)

    # Каталоги, которые не должны достаться ребёнку: venv приложения и
    # каталоги его собственного интерпретатора. ``base_prefix`` тут не
    # нужен: там стоит системный Python, который внешней программе как раз
    # и нужен.
    shadowing: set[str] = set()
    venv_dir = os.environ.get("VIRTUAL_ENV")
    if venv_dir:
        shadowing.add(os.path.join(venv_dir, "bin"))
    shadowing.add(os.path.join(sys.prefix, "bin"))
    shadowing.add(os.path.dirname(os.path.realpath(sys.executable)))

    path = env.get("PATH", "")
    parts = [part for part in path.split(os.pathsep) if part]
    kept = [part for part in parts if os.path.realpath(part) not in shadowing]
    if kept:
        env["PATH"] = os.pathsep.join(kept)

    for name in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(name, None)
    return env
