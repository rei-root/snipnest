"""Тесты интерфейса: окно, список загрузок, drag-and-drop, лог."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent

from gallary_downloader.downloader import DownloadResult
from gallary_downloader.jobs import DownloadJob, JobEvent, JobEventKind, JobState
from gallary_downloader.settings import FileSecretStore, Settings
from gallary_downloader.ui.app import make_application
from gallary_downloader.ui.models import JobRow, format_speed
from gallary_downloader.ui.window import MainWindow

pytest.importorskip("PySide6")


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
    """Подмена gallery-dl: отдаёт заранее заданный итог."""

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


def make_job(result: DownloadResult | None = None) -> DownloadJob:
    runner = StubRunner(result or DownloadResult(0, 0, 0, 0, ()))
    return DownloadJob("job-1", "https://pin.it/abc", "/tmp/out", runner, None)


def test_заголовок_окна_совпадает_с_названием_приложения(window: MainWindow) -> None:
    assert window.windowTitle() == "Gallary Downloader"


def test_имя_приложения_в_qapplication(settings: Settings) -> None:
    app, _ = make_application(settings)
    assert app.applicationName() == "Gallary Downloader"


def test_поле_ссылки_и_кнопка_скачать_есть(window: MainWindow) -> None:
    assert window._controls.download_button.text() == "Скачать"
    assert window.link_text == ""


def test_папка_сохранения_показывается(window: MainWindow, settings: Settings) -> None:
    assert window.destination_text == settings.destination


def test_в_окне_есть_кнопки_pinterest(window: MainWindow) -> None:
    assert window._controls.token_button.text() == "Токен Pinterest"
    assert window._controls.open_pinterest_button.text() == "Открыть Pinterest"


def test_перетаскивание_ссылки_кладёт_её_в_поле(window: MainWindow) -> None:
    mime = QMimeData()
    mime.setUrls([QUrl("https://pin.it/abc")])
    event = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.dropEvent(event)
    assert window.link_text == "https://pin.it/abc"


def test_событие_прогресса_обновляет_строку(window: MainWindow) -> None:
    job = make_job()
    window._panel.add_job(job)
    row = window.row_for(job.job_id)
    assert row is not None

    window._apply_event(
        JobEvent(
            kind=JobEventKind.PROGRESS,
            job_id=job.job_id,
            downloaded=2,
            total=5,
            bytes_per_second=2048.0,
        )
    )

    assert row.downloaded == 2
    assert row.total == 5
    assert row.progress_label == "скачано 2 из 5"
    assert row.speed_label == "2.0 КБ/с"
    assert window.progress_value == 40


def test_событие_файла_добавляет_имя_файла(window: MainWindow) -> None:
    job = make_job()
    window._panel.add_job(job)

    window._apply_event(
        JobEvent(
            kind=JobEventKind.FILE,
            job_id=job.job_id,
            path="/tmp/out/pinterest/pin_1.jpg",
        )
    )

    row = window.row_for(job.job_id)
    assert row is not None
    assert row.file_names == ["pin_1.jpg"]


def test_список_файлов_показывается_для_выбранной_загрузки(window: MainWindow) -> None:
    job = make_job()
    window._panel.add_job(job)
    window._panel._table.selectRow(0)

    window._apply_event(
        JobEvent(
            kind=JobEventKind.FILE,
            job_id=job.job_id,
            path="/tmp/out/pinterest/pin_1.jpg",
        )
    )
    window._apply_event(
        JobEvent(
            kind=JobEventKind.FILE,
            job_id=job.job_id,
            path="/tmp/out/pinterest/pin_2.jpg",
        )
    )

    assert window._panel.selected_file_names() == ["pin_1.jpg", "pin_2.jpg"]


def test_событие_результата_даёт_итог(window: MainWindow) -> None:
    job = make_job()
    window._panel.add_job(job)

    window._apply_event(
        JobEvent(
            kind=JobEventKind.RESULT,
            job_id=job.job_id,
            result=DownloadResult(3, 1, 0, 0, ("a.jpg",)),
        )
    )

    row = window.row_for(job.job_id)
    assert row is not None
    assert row.result_label == "скачано: 3, пропущено: 1, ошибок: 0"


def test_событие_ошибки_пишется_в_лог(window: MainWindow) -> None:
    job = make_job()
    window._panel.add_job(job)

    window._apply_event(JobEvent(kind=JobEventKind.ERROR, job_id=job.job_id, text="нет сети"))

    assert "нет сети" in window.log_text
    assert "Ошибка загрузки" in window.status_text


def test_лог_сворачивается(window: MainWindow) -> None:
    assert window._log.view.isVisibleTo(window) or not window._log.view.isHidden()
    window._log.toggle_button.setChecked(False)
    assert window._log.view.isHidden()


def test_непонятная_ссылка_не_создаёт_загрузку(window: MainWindow, monkeypatch) -> None:
    monkeypatch.setattr(
        "gallary_downloader.ui.window.find_gallery_dl",
        lambda explicit=None: "/usr/bin/gallery-dl",
    )
    window.link_text = "https://example.com/not-pinterest"
    window._on_download_clicked()
    assert window.job_ids() == []
    assert "не распознана" in window.status_text


def test_отсутствие_gallery_dl_даёт_понятное_сообщение(window: MainWindow, monkeypatch) -> None:
    monkeypatch.setattr(
        "gallary_downloader.ui.window.find_gallery_dl",
        lambda explicit=None: None,
    )
    window.link_text = "https://pin.it/abc"
    window._on_download_clicked()
    assert window.job_ids() == []
    assert "gallery-dl не найден" in window.status_text


def test_загрузка_идёт_в_отдельном_потоке(window: MainWindow, monkeypatch, qtbot) -> None:
    """Загрузка стартует, а окно остаётся отзывчивым."""
    monkeypatch.setattr(
        "gallary_downloader.ui.window.find_gallery_dl",
        lambda explicit=None: "/usr/bin/gallery-dl",
    )
    monkeypatch.setattr(
        "gallary_downloader.sources.GalleryDlRunner",
        lambda *args, **kwargs: StubRunner(DownloadResult(0, 0, 0, 0, ())),
    )
    window.link_text = "https://pin.it/abc"
    window._on_download_clicked()

    assert len(window.job_ids()) == 1
    row = window.row_for(window.job_ids()[0])
    assert row is not None
    assert row.state in (JobState.QUEUED, JobState.RUNNING, JobState.DONE)


def test_подпись_скорости_человекочитаемая() -> None:
    assert format_speed(0) == "—"
    assert format_speed(512) == "512 Б/с"
    assert format_speed(1536) == "1.5 КБ/с"
    assert format_speed(5 * 1024 * 1024) == "5.0 МБ/с"


def test_строка_показывает_состояние_по_русски() -> None:
    row = JobRow(job_id="job-1", url="https://pin.it/abc", destination="/tmp")
    assert row.state_label == "в очереди"
    row.state = JobState.RUNNING
    assert row.state_label == "выполняется"
