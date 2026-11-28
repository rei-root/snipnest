"""Строка меню окна: состав пунктов и перенос кнопок в меню.

Требования, которые закрывают эти проверки:

* R3 — функциональные требования: в окне появляется строка меню «Файл»,
  «Вид», «Справка», кнопки настроек переезжают в меню, «Открыть Pinterest»
  удаляется, у окна есть иконка приложения, в шапке окна — символ;
* R6 — границы: кнопка «Открыть Pinterest» не остаётся ни в меню, ни в
  исходниках интерфейса.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QPushButton

from snipnest.settings import FileSecretStore, Settings
from snipnest.ui.window import MainWindow

UI_DIR = Path(__file__).resolve().parents[2] / "src" / "snipnest" / "ui"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        config_path=tmp_path / "settings.json",
        secret_store=FileSecretStore(tmp_path / "secret"),
    )


@pytest.fixture
def window(qtbot, settings: Settings) -> MainWindow:
    win = MainWindow(settings)
    qtbot.addWidget(win)
    return win


def _menu(window: MainWindow, title: str) -> QMenu:
    """Меню строки меню окна по названию."""
    for action in window.menuBar().actions():
        if action.text() == title:
            menu = action.menu()
            assert menu is not None, f"у меню «{title}» нет подменю"
            return menu
    raise AssertionError(f"в строке меню нет пункта «{title}»")


def _texts(menu: QMenu) -> list[str]:
    """Названия пунктов меню без разделителей."""
    return [action.text() for action in menu.actions() if not action.isSeparator()]


def test_в_окне_есть_строка_меню(window: MainWindow) -> None:
    assert [action.text() for action in window.menuBar().actions()] == [
        "Файл",
        "Вид",
        "Справка",
    ]


def test_меню_файл_содержит_пункты(window: MainWindow) -> None:
    texts = _texts(_menu(window, "Файл"))
    for expected in (
        "Выбрать папку сохранения…",
        "Настройки…",
        "Токен Pinterest…",
        "Cookies YouTube…",
        "Путь к gallery-dl…",
        "Путь к yt-dlp…",
        "Компоненты…",
        "Выход",
    ):
        assert expected in texts, f"в меню «Файл» нет пункта «{expected}»"


def test_меню_вид_содержит_тему_и_лог(window: MainWindow) -> None:
    texts = _texts(_menu(window, "Вид"))
    assert "Тема" in texts
    assert "Показать лог" in texts

    theme_menu = None
    for action in _menu(window, "Вид").actions():
        if action.text() == "Тема":
            theme_menu = action.menu()
    assert theme_menu is not None, "у пункта «Тема» нет подменю"
    assert [action.text() for action in theme_menu.actions()] == [
        "Тёмная",
        "Светлая",
        "Как в системе",
    ]


def test_меню_справка_содержит_о_программе(window: MainWindow) -> None:
    texts = _texts(_menu(window, "Справка"))
    assert "О программе…" in texts


def test_кнопок_настроек_в_верхней_части_окна_не_осталось(window: MainWindow) -> None:
    """Кнопки настроек переехали в меню — в верхней части окна их больше нет."""
    button_texts = [button.text() for button in window._controls.findChildren(QPushButton)]
    for moved in (
        "Токен Pinterest",
        "Компоненты…",
        "Путь к gallery-dl",
        "Путь к yt-dlp",
        "Cookies YouTube",
    ):
        assert moved not in button_texts, f"кнопка «{moved}» осталась в верхней части окна"


def test_кнопки_скачать_и_выбрать_папку_остались(window: MainWindow) -> None:
    button_texts = [button.text() for button in window._controls.findChildren(QPushButton)]
    assert "Скачать" in button_texts
    assert "Выбрать папку" in button_texts


def test_открыть_pinterest_удалена_насовсем(window: MainWindow) -> None:
    """Кнопки «Открыть Pinterest» нет ни в окне, ни в исходниках интерфейса."""
    button_texts = [button.text() for button in window.findChildren(QPushButton)]
    assert "Открыть Pinterest" not in button_texts

    action_texts = [action.text() for action in window.menuBar().findChildren(QAction)]
    assert all("Открыть Pinterest" not in text for text in action_texts)

    for path in sorted(UI_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "Открыть Pinterest" not in text, f"{path.name} упоминает «Открыть Pinterest»"
        assert "open_pinterest" not in text, f"{path.name} упоминает open_pinterest"


def test_у_окна_есть_иконка_приложения(window: MainWindow) -> None:
    icon = window.windowIcon()
    assert not icon.isNull()
    pixmap = icon.pixmap(32, 32)
    assert not pixmap.isNull()
    assert pixmap.width() == 32


def test_в_шапке_окна_есть_символ_приложения(window: MainWindow) -> None:
    header = window._controls.header_icon
    pixmap = header.pixmap()
    assert not pixmap.isNull()
    assert window._controls.header_label.text() == "Snipnest"
