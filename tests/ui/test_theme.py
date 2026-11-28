"""Тема окраски: переключение, сохранение и перекраска символа.

Требования, которые закрывают эти проверки:

* R3 — функциональные требования: три значения темы, выбор применяется сразу
  и помнится между запусками;
* R4 — бизнес-правила: «Как в системе» означает следование системе, тема
  применяется целиком, символ рисуется цветом текста темы.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPalette
from PySide6.QtWidgets import QApplication

from snipnest.branding import symbolic_icon
from snipnest.settings import FileSecretStore, Settings
from snipnest.ui.theme import Theme, apply_theme
from snipnest.ui.window import MainWindow


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
    yield win
    apply_theme(Theme.SYSTEM)


def _opaque_color(image: QImage) -> QColor:
    """Первый непрозрачный цвет картинки."""
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() > 0:
                return color
    raise AssertionError("картинка пустая")


def test_тема_применяется_мгновенно(qtbot) -> None:
    """Тёмная и светлая темы дают разные цвета окна сразу, без перезапуска."""
    app = QApplication.instance()
    assert app is not None

    apply_theme(Theme.DARK)
    dark = app.palette().color(QPalette.ColorRole.Window)
    apply_theme(Theme.LIGHT)
    light = app.palette().color(QPalette.ColorRole.Window)

    assert dark != light
    assert light.lightness() > dark.lightness()


def test_тема_как_в_системе_следует_системе(qtbot) -> None:
    """«Как в системе» — это следование системной схеме, а не своя тема."""
    hints = QGuiApplication.styleHints()
    hints.setColorScheme(Qt.ColorScheme.Unknown)
    system = hints.colorScheme()

    apply_theme(Theme.SYSTEM)

    assert hints.colorScheme() == system


def test_выбор_темы_сохраняется_в_настройках(qtbot, window: MainWindow, settings: Settings) -> None:
    window.set_theme(Theme.DARK)
    assert settings.theme == Theme.DARK.value

    window.set_theme(Theme.LIGHT)
    assert settings.theme == Theme.LIGHT.value


def test_символ_перекрашивается_по_теме(qtbot) -> None:
    """Символ рисуется цветом текста темы: в тёмной он светлый, в светлой — тёмный."""
    apply_theme(Theme.DARK)
    dark_color = _opaque_color(symbolic_icon().pixmap(24, 24).toImage())
    apply_theme(Theme.LIGHT)
    light_color = _opaque_color(symbolic_icon().pixmap(24, 24).toImage())

    assert dark_color != light_color
    assert dark_color.lightness() > light_color.lightness()
