"""Сценарий окна: меню, тема и окно настроек.

Требования, которые закрывают эту проверку:

* R3 — функциональные требования: меню, переключение темы и отдельное окно
  настроек работают вместе;
* AC1 — критерии приёмки: тема применяется сразу и помнится, окно настроек
  открывается из меню «Файл».
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QAction

from snipnest.settings import FileSecretStore, Settings
from snipnest.ui.app import make_application
from snipnest.ui.settings_dialog import SettingsDialog
from snipnest.ui.theme import Theme, apply_theme


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        config_path=tmp_path / "settings.json",
        secret_store=FileSecretStore(tmp_path / "secret"),
    )


def _action(window, title: str) -> QAction:
    """Пункт меню по названию."""
    for action in window.menuBar().findChildren(QAction):
        if action.text() == title:
            return action
    raise AssertionError(f"нет пункта меню «{title}»")


def test_сценарий_окна_меню_темы_и_настроек(qtbot, monkeypatch, settings: Settings) -> None:
    app, window = make_application(settings)
    qtbot.addWidget(window)

    try:
        # 1. Строка меню на месте.
        assert [action.text() for action in window.menuBar().actions()] == [
            "Файл",
            "Вид",
            "Справка",
        ]

        # 2. Тема переключается из меню «Вид» и сразу применяется.
        _action(window, "Тёмная").trigger()
        assert settings.theme == Theme.DARK.value

        _action(window, "Светлая").trigger()
        assert settings.theme == Theme.LIGHT.value

        # 3. «Файл → Настройки…» открывает отдельное окно настроек.
        opened: list[SettingsDialog] = []

        def fake_exec(self: SettingsDialog) -> int:
            opened.append(self)
            return int(SettingsDialog.DialogCode.Accepted)

        monkeypatch.setattr(SettingsDialog, "exec", fake_exec)
        _action(window, "Настройки…").trigger()

        assert len(opened) == 1
        dialog = opened[0]
        assert dialog.theme_combo.count() == 3
        assert dialog.theme_combo.currentText() == "Светлая"
    finally:
        apply_theme(Theme.SYSTEM)
        window.close()