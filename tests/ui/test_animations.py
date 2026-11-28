"""Сдержанные анимации: появление строки загрузки и разворачивание лога.

Требования, которые закрывают эти проверки:

* R3 — функциональные требования: анимаций ровно две — плавное появление
  строки загрузки и плавное разворачивание/сворачивание лога;
* R5 — нефункциональные требования: анимации короткие и не мешают работе.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from snipnest.downloader import DownloadResult
from snipnest.jobs import DownloadJob
from snipnest.settings import FileSecretStore, Settings
from snipnest.ui.window import MainWindow


class StubRunner:
    """Подмена исполнителя: загрузка ничего не делает."""

    name = "gallery-dl"

    def __init__(self) -> None:
        self.result = DownloadResult(0, 0, 0, 0, ())

    def count_files(self, url: str) -> int:
        return 0

    def run(self, url: str, *, simulate: bool = False) -> DownloadResult:
        return self.result

    def cancel(self) -> bool:
        return True


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


def test_строка_загрузки_появляется_плавно(qtbot, window: MainWindow) -> None:
    """Новая строка появляется не сразу: её текст проявляется постепенно."""
    job = DownloadJob("job-1", "https://pin.it/abc", "/tmp/out", StubRunner(), None)

    window._panel.add_job(job)
    assert window._panel.row_opacity(job.job_id) < 1.0

    qtbot.wait(600)
    assert window._panel.row_opacity(job.job_id) == pytest.approx(1.0)


def test_лог_разворачивается_плавно(qtbot, window: MainWindow) -> None:
    """Лог сворачивается и разворачивается анимацией, а не рывком."""
    log = window._log

    log.set_expanded(False)
    assert log.is_animating()
    qtbot.wait(600)
    assert not log.is_animating()
    assert log.view.isHidden()

    log.set_expanded(True)
    assert log.is_animating()
    qtbot.wait(600)
    assert not log.is_animating()
    assert not log.view.isHidden()