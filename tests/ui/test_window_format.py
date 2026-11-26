"""Окно и выбор формата сохранения: что видит владелец и что уходит в загрузку.

Требования, которые закрывают эти проверки:

* R3 — требования: список форматов зависит от вида ссылки, выбранный формат
  доходит до исполнителя.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from snipnest.downloader import DownloadResult
from snipnest.settings import FileSecretStore, Settings
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
    return win


class StubRunner:
    """Подмена исполнителя: отдаёт заранее заданный итог."""

    #: Имя исполнителя — оно попадает в сообщение об ошибке.
    name = "gallery-dl"

    def __init__(self, result: DownloadResult) -> None:
        self.result = result
        self.cancelled = False

    def count_files(self, url: str) -> int:
        return len(self.result.files)

    def run(self, url: str, *, simulate: bool = False) -> DownloadResult:
        return self.result

    def cancel(self) -> bool:
        self.cancelled = True
        return True


def test_ссылка_на_фото_показывает_форматы_картинки(window: MainWindow) -> None:
    """R3: у фото — список форматов картинки."""
    window.link_text = "https://pin.it/abc"

    assert window.format_selector.format_ids() == ["original", "jpg", "png", "webp"]


def test_ссылка_на_видео_показывает_форматы_видео(window: MainWindow) -> None:
    """R3: у видео — список форматов видео."""
    window.link_text = "https://youtu.be/dQw4w9WgXcQ"

    assert window.format_selector.format_ids() == ["mp4", "webm", "mkv", "audio", "separate"]


def test_выбранный_формат_видео_доходит_до_исполнителя(
    window: MainWindow,
    monkeypatch,
) -> None:
    """R3: выбор владельца уходит в исполнителя."""
    captured: dict[str, object] = {}

    def fake_runner(*args: object, **kwargs: object) -> StubRunner:
        captured.update(kwargs)
        return StubRunner(DownloadResult(0, 0, 0, 0, ()))

    monkeypatch.setattr("snipnest.sources.YtDlpRunner", fake_runner)
    window.link_text = "https://youtu.be/dQw4w9WgXcQ"
    window.format_selector.select_format("webm")
    window._on_download_clicked()

    assert captured["video_format"].id == "webm"  # type: ignore[union-attr]


def test_выбранный_формат_картинки_доходит_до_исполнителя(
    window: MainWindow,
    monkeypatch,
) -> None:
    """R3: выбранный формат картинки уходит в исполнителя."""
    captured: dict[str, object] = {}

    def fake_runner(*args: object, **kwargs: object) -> StubRunner:
        captured.update(kwargs)
        return StubRunner(DownloadResult(0, 0, 0, 0, ()))

    monkeypatch.setattr("snipnest.sources.GalleryDlRunner", fake_runner)
    window.link_text = "https://pin.it/abc"
    window.format_selector.select_format("png")
    window._on_download_clicked()

    assert captured["image_extension"] == "png"


def test_без_ссылки_выбор_формата_недоступен(window: MainWindow) -> None:
    """R3: формат выбирают после того, как вставили ссылку."""
    assert window.link_text == ""
    assert window.format_selector.isEnabled() is False


def test_по_вставленной_ссылке_выбор_формата_доступен(window: MainWindow) -> None:
    """R3: распознанная ссылка открывает список форматов."""
    window.link_text = "https://pin.it/abc"

    assert window.format_selector.isEnabled() is True


def test_для_нераспознанной_ссылки_выбор_формата_недоступен(window: MainWindow) -> None:
    """R3: чужой ссылке формат не предлагают — приложение не знает, что за неё."""
    window.link_text = "https://example.com/not-pinterest"

    assert window.format_selector.isEnabled() is False


def test_после_очистки_поля_выбор_формата_снова_недоступен(window: MainWindow) -> None:
    """R3: поле очистили — список форматов снова неактивен."""
    window.link_text = "https://pin.it/abc"
    window.link_text = ""

    assert window.format_selector.isEnabled() is False
