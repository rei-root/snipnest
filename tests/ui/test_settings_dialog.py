"""Окно настроек: все настройки собраны в одном месте.

Требования, которые закрывают эти проверки:

* R3 — функциональные требования: «Файл → Настройки…» открывает отдельное
  окно с папкой сохранения, токеном Pinterest, cookies YouTube, путями к
  gallery-dl и yt-dlp и разделом «Внешний вид» с выбором темы.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from snipnest.settings import FileSecretStore, Settings
from snipnest.ui.settings_actions import SettingsActions
from snipnest.ui.settings_dialog import SettingsDialog
from snipnest.ui.theme import THEME_LABELS, Theme


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        config_path=tmp_path / "settings.json",
        secret_store=FileSecretStore(tmp_path / "secret"),
    )


@pytest.fixture
def dialog(qtbot, settings: Settings) -> SettingsDialog:
    actions = SettingsActions(None, settings, lambda text: None, lambda value: None)
    window = SettingsDialog(settings, actions)
    qtbot.addWidget(window)
    return window


def test_окно_настроек_содержит_все_настройки(dialog: SettingsDialog) -> None:
    assert dialog.theme_combo.count() == len(THEME_LABELS)
    assert [dialog.theme_combo.itemText(i) for i in range(dialog.theme_combo.count())] == [
        THEME_LABELS[theme] for theme in Theme
    ]
    assert dialog.destination_edit.text()
    assert dialog.gallery_dl_edit is not None
    assert dialog.yt_dlp_edit is not None
    assert dialog.token_button.text()
    assert dialog.cookies_button.text()


def test_в_окне_настроек_меняется_тема(dialog: SettingsDialog) -> None:
    chosen: list[Theme] = []
    dialog.theme_changed.connect(chosen.append)

    index = dialog.theme_combo.findText(THEME_LABELS[Theme.DARK])
    assert index >= 0
    dialog.theme_combo.setCurrentIndex(index)

    assert chosen == [Theme.DARK]