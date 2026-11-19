"""Тесты диалогов: выбор источника cookies для YouTube."""

from __future__ import annotations

from pathlib import Path

import pytest

from snipnest.cookies import detect_browser_sources
from snipnest.ui.dialogs import CookieSourceDialog

pytest.importorskip("PySide6")


@pytest.fixture
def home(tmp_path: Path, monkeypatch) -> Path:
    """Домашний каталог с профилями Firefox и Chrome."""
    firefox = tmp_path / ".mozilla" / "firefox" / "abc.default-release"
    firefox.mkdir(parents=True)
    (firefox / "cookies.sqlite").write_bytes(b"")
    chrome = tmp_path / ".config" / "google-chrome"
    chrome.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def test_диалог_показывает_найденные_источники(qtbot, home: Path) -> None:
    dialog = CookieSourceDialog()
    qtbot.addWidget(dialog)
    labels = [dialog.itemText(index) for index in range(dialog.item_count())]
    assert "Не использовать" in labels
    assert "Firefox (abc.default-release)" in labels
    assert "Google Chrome" in labels
    assert "Файл cookies.txt" in labels


def test_диалог_выбирает_браузер(qtbot, home: Path) -> None:
    dialog = CookieSourceDialog()
    qtbot.addWidget(dialog)
    dialog.select_browser("firefox:abc.default-release")
    assert dialog.selection() == ("firefox:abc.default-release", "")


def test_диалог_выбирает_файл(qtbot, home: Path) -> None:
    dialog = CookieSourceDialog()
    qtbot.addWidget(dialog)
    dialog.select_file("/home/sato/cookies.txt")
    assert dialog.selection() == ("", "/home/sato/cookies.txt")


def test_диалог_показывает_текущий_выбор(qtbot, home: Path) -> None:
    dialog = CookieSourceDialog(browser="chrome")
    qtbot.addWidget(dialog)
    assert dialog.selection() == ("chrome", "")


def test_диалог_без_выбора_ничего_не_возвращает(qtbot, home: Path) -> None:
    dialog = CookieSourceDialog()
    qtbot.addWidget(dialog)
    assert dialog.selection() == ("", "")


def test_источники_совпадают_с_найденными_в_системе(home: Path) -> None:
    assert len(detect_browser_sources(home)) == 2
