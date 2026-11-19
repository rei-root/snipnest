"""Инварианты переименования: старое имя не осталось в рабочем дереве.

Тест не импортирует пакет на уровне модуля: проверка старого имени должна
падать самостоятельно, а не из-за не найденного модуля.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

# Старое имя инструмента собирается из частей: иначе сам тест содержал бы
# его в виде текста и проверка нашла бы его в этом же файле.
_LEGACY_NAME = "gall" + "ary"

# Артефакты орка и дословная запись интервью хранят старое имя намеренно.
_ALLOWED_PREFIXES = ("tasks/", "docs/ba/spec/")
_ALLOWED_FILES = frozenset({"docs/TASK-BRIEF.md"})

# Модуль миграции — единственное место, где старое имя обязано быть названо:
# по нему переносятся настройки и токен старого приложения.
_ALLOWED_SOURCES = frozenset({"src/snipnest/migration.py"})

# Каталоги сборки и окружения: в них лежат копии установленного пакета.
_SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _iter_files(root: Path) -> list[Path]:
    """Файлы рабочего дерева без служебных каталогов.

    Симлинки в каталоги не разыгрываются (followlinks=False), поэтому
    ссылка на нормативную модель орка не читается.
    """
    found: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for name in files:
            found.append(Path(current) / name)
    return found


def _is_allowed(relative: str) -> bool:
    return (
        relative.startswith(_ALLOWED_PREFIXES)
        or relative in _ALLOWED_FILES
        or relative in _ALLOWED_SOURCES
    )


def test_в_рабочем_дереве_нет_старого_имени() -> None:
    """Ни один файл проекта, кроме артефактов орка, не упоминает старое имя."""
    root = _repo_root()
    needle = _LEGACY_NAME.encode()
    offenders = []
    for path in _iter_files(root):
        relative = path.relative_to(root).as_posix()
        if _is_allowed(relative):
            continue
        if needle in path.read_bytes().lower():
            offenders.append(relative)
    assert not offenders, "старое имя осталось в файлах: " + ", ".join(sorted(offenders))


def test_пакет_импортируется_под_новым_именем() -> None:
    module = importlib.import_module("snipnest")
    assert module.__name__ == "snipnest"


def test_старый_пакет_не_импортируется() -> None:
    try:
        importlib.import_module(_LEGACY_NAME + "_downloader")
    except ModuleNotFoundError:
        return
    raise AssertionError("старый пакет всё ещё импортируется")


def test_имя_конфига_новое() -> None:
    settings = importlib.import_module("snipnest.settings")
    assert settings.CONFIG_DIR.name == "snipnest"


def test_имя_сервиса_хранилища_новое() -> None:
    settings = importlib.import_module("snipnest.settings")
    assert settings.KEYRING_SERVICE == "snipnest"
