"""Проверки переименования: ярлык, установщик, метаданные пакета и репозиторий.

Это проверки класса B: читаются файлы репозитория и состояние git и
сравниваются между собой — поведение проверяется без запуска приложения.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "packaging" / "snipnest.desktop"
INSTALLER = ROOT / "packaging" / "install-desktop-entry.sh"
PYPROJECT = ROOT / "pyproject.toml"
LOGO = ROOT / "logo" / "snipnest.png"


def _desktop() -> str:
    return DESKTOP.read_text(encoding="utf-8")


def test_ярлык_называет_приложение_с_большой_буквы() -> None:
    assert "Name=Snipnest" in _desktop()


def test_ярлык_запускает_команду_из_метаданных_пакета() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    entry = re.search(r"^snipnest\s*=\s*\"([^\"]+)\"", pyproject, re.MULTILINE)
    assert entry is not None, "в pyproject.toml нет точки входа snipnest"
    assert entry.group(1).endswith(":main")
    assert "Exec=snipnest" in _desktop()


def test_имя_иконки_совпадает_с_именем_команды() -> None:
    desktop = _desktop()
    assert "Icon=snipnest" in desktop
    assert "StartupWMClass=snipnest" in desktop


def test_установщик_ставит_ярлык_и_иконку_под_новым_именем() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")
    assert "snipnest.desktop" in installer
    assert "snipnest.png" in installer


def test_логотип_на_месте() -> None:
    assert LOGO.is_file()


def test_удалённый_репозиторий_новый() -> None:
    """Репозиторий проекта переведён на snipnest."""
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert url.endswith("snipnest.git")
