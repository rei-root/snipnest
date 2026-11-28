"""Тесты интерфейса: окно, список загрузок, drag-and-drop, лог."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QLineEdit

from snipnest.downloader import DownloadResult
from snipnest.jobs import DownloadJob, JobEvent, JobEventKind, JobState
from snipnest.settings import FileSecretStore, Settings
from snipnest.ui.app import make_application
from snipnest.ui.models import JobRow, format_speed
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
    """Подмена gallery-dl: отдаёт заранее заданный итог."""

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


def make_job(result: DownloadResult | None = None) -> DownloadJob:
    runner = StubRunner(result or DownloadResult(0, 0, 0, 0, ()))
    return DownloadJob("job-1", "https://pin.it/abc", "/tmp/out", runner, None)


def test_заголовок_окна_совпадает_с_названием_приложения(window: MainWindow) -> None:
    assert window.windowTitle() == "Snipnest"


def test_имя_приложения_в_qapplication(settings: Settings) -> None:
    app, _ = make_application(settings)
    assert app.applicationName() == "Snipnest"


def test_поле_ссылки_и_кнопка_скачать_есть(window: MainWindow) -> None:
    assert window._controls.download_button.text() == "Скачать"
    assert window.link_text == ""


def test_папка_сохранения_показывается(window: MainWindow, settings: Settings) -> None:
    assert window.destination_text == settings.destination


def test_область_лога_называется_лог(window: MainWindow) -> None:
    """В логе вывод обоих исполнителей — название не должно быть узким."""
    assert window._log.title == "Лог"


def test_в_окне_только_поле_ссылки(window: MainWindow) -> None:
    """R6: поиск, логин и пароль в задачу не входят — редактируемое поле одно."""
    editable = [edit for edit in window.findChildren(QLineEdit) if not edit.isReadOnly()]
    assert len(editable) == 1
    assert "Ссылка" in editable[0].placeholderText()


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


def test_процент_от_исполнителя_двигает_прогресс_бар(window: MainWindow) -> None:
    """Видео качается долго: процент приходит от исполнителя, а не от счётчика файлов."""
    job = make_job()
    window._panel.add_job(job)

    window._apply_event(
        JobEvent(
            kind=JobEventKind.PROGRESS,
            job_id=job.job_id,
            downloaded=0,
            total=1,
            percent=45,
        )
    )

    row = window.row_for(job.job_id)
    assert row is not None
    assert row.progress_percent == 45
    assert window.progress_value == 45


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


def test_лог_сворачивается(window: MainWindow, qtbot) -> None:
    """Лог сворачивается анимацией — ждём конца и проверяем, что он скрыт."""
    window._log.toggle_button.setChecked(False)
    qtbot.wait(600)
    assert window._log.view.isHidden()


def test_непонятная_ссылка_не_создаёт_загрузку(window: MainWindow) -> None:
    window.link_text = "https://example.com/not-pinterest"
    window._on_download_clicked()
    assert window.job_ids() == []
    assert "не распознана" in window.status_text


def test_отсутствие_gallery_dl_даёт_понятное_сообщение(window: MainWindow, monkeypatch) -> None:
    monkeypatch.setattr(
        "snipnest.sources.find_gallery_dl",
        lambda explicit=None: None,
    )
    window.link_text = "https://pin.it/abc"
    window._on_download_clicked()
    assert window.job_ids() == []
    assert "gallery-dl не найден" in window.status_text


def test_загрузка_идёт_в_отдельном_потоке(window: MainWindow, monkeypatch, qtbot) -> None:
    """Загрузка стартует, а окно остаётся отзывчивым."""
    monkeypatch.setattr(
        "snipnest.sources.find_gallery_dl",
        lambda explicit=None: "/usr/bin/gallery-dl",
    )
    monkeypatch.setattr(
        "snipnest.sources.GalleryDlRunner",
        lambda *args, **kwargs: StubRunner(DownloadResult(0, 0, 0, 0, ())),
    )
    window.link_text = "https://pin.it/abc"
    window._on_download_clicked()

    assert len(window.job_ids()) == 1
    row = window.row_for(window.job_ids()[0])
    assert row is not None
    assert row.state in (JobState.QUEUED, JobState.RUNNING, JobState.DONE)


def test_ссылка_на_youtube_создаёт_загрузку(window: MainWindow, monkeypatch) -> None:
    """Ссылка на YouTube распознаётся и попадает в список загрузок."""
    monkeypatch.setattr(
        "snipnest.sources.YtDlpRunner",
        lambda *args, **kwargs: StubRunner(DownloadResult(0, 0, 0, 0, ())),
    )
    window.link_text = "https://youtu.be/dQw4w9WgXcQ"
    window._on_download_clicked()

    assert len(window.job_ids()) == 1
    assert "не распознана" not in window.status_text


def test_отсутствие_yt_dlp_даёт_понятное_сообщение(window: MainWindow, monkeypatch) -> None:
    monkeypatch.setattr(
        "snipnest.sources.find_yt_dlp",
        lambda explicit=None: None,
    )
    window.link_text = "https://youtu.be/dQw4w9WgXcQ"
    window._on_download_clicked()

    assert window.job_ids() == []
    assert "yt-dlp не найден" in window.status_text


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
