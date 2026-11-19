"""Тесты жизненного цикла загрузки: состояния, права, видимость."""

from __future__ import annotations

import pytest

from snipnest.downloader import DownloadEvent, DownloadEventKind, DownloadResult
from snipnest.jobs import DownloadJob, JobEvent, JobEventKind, JobManager, JobState


class FakeRunner:
    """Подмена gallery-dl: отдаёт заранее заданный итог."""

    def __init__(self, result: DownloadResult, files: list[str] | None = None) -> None:
        self.result = result
        self.files = files or []
        self.cancelled = False

    def count_files(self, url: str) -> int:
        return len(self.files)

    def run(self, url: str, *, simulate: bool = False) -> DownloadResult:
        return self.result

    def cancel(self) -> bool:
        self.cancelled = True
        return True


def make_job(
    result: DownloadResult | None = None,
    files: list[str] | None = None,
) -> tuple[DownloadJob, list[JobEvent]]:
    events: list[JobEvent] = []
    runner = FakeRunner(result or DownloadResult(0, 0, 0, 0, ()), files or [])
    job = DownloadJob("job-1", "https://pin.it/abc", "/tmp/out", runner, events.append)
    return job, events


def test_новый_загрузка_в_очереди() -> None:
    job, _ = make_job()
    assert job.state is JobState.QUEUED


def test_успешная_загрузка_завершается() -> None:
    job, _ = make_job(DownloadResult(3, 1, 0, 0, ("a.jpg",)), ["a.jpg"])
    job.start()
    assert job.state is JobState.DONE
    assert job.progress.downloaded == 3
    assert job.progress.skipped == 1


def test_ненулевой_код_возврата_даёт_ошибку() -> None:
    job, _ = make_job(DownloadResult(0, 0, 1, 4, ()))
    job.start()
    assert job.state is JobState.FAILED
    assert job.error_text


def test_отмена_разрешена_в_очереди_и_при_выполнении() -> None:
    job, _ = make_job()
    assert job.can_cancel()
    job.cancel()
    assert job.state is JobState.CANCELLED


def test_отмена_невозможна_после_завершения() -> None:
    job, _ = make_job(DownloadResult(1, 0, 0, 0, ("a.jpg",)))
    job.start()
    assert job.state is JobState.DONE
    assert not job.can_cancel()
    assert not job.cancel()


def test_повтор_возможен_после_ошибки() -> None:
    job, _ = make_job(DownloadResult(0, 0, 1, 4, ()))
    job.start()
    assert job.state is JobState.FAILED
    assert job.can_retry()
    assert job.retry()
    assert job.state is JobState.QUEUED


def test_повтор_возможен_после_отмены() -> None:
    job, _ = make_job()
    job.cancel()
    assert job.can_retry()


def test_повтор_невозможен_в_очереди() -> None:
    job, _ = make_job()
    assert not job.can_retry()
    assert not job.retry()


def test_в_очереди_видны_только_ссылка_и_папка() -> None:
    job, _ = make_job()
    assert job.visible_fields() == ("ссылка", "папка_сохранения")


def test_при_выполнении_видны_прогресс_скорость_файлы_и_лог() -> None:
    job, _ = make_job(DownloadResult(1, 0, 0, 0, ("a.jpg",)), ["a.jpg"])
    job.start()
    visible = job.visible_fields()
    assert "прогресс" in visible
    assert "скорость" in visible
    assert "список_файлов" in visible
    assert "лог" in visible


def test_событие_файла_обновляет_счётчик() -> None:
    job, events = make_job()
    job.handle_download_event(DownloadEvent(DownloadEventKind.FILE_DOWNLOADED, path="a.jpg"))
    assert job.progress.downloaded == 1
    assert job.files == ["a.jpg"]
    assert any(e.kind is JobEventKind.FILE for e in events)


def test_событие_пропуска_не_увеличивает_скачанные() -> None:
    job, _ = make_job()
    job.handle_download_event(DownloadEvent(DownloadEventKind.FILE_SKIPPED, path="a.jpg"))
    assert job.progress.downloaded == 0
    assert job.progress.skipped == 1


def test_подпись_счётчика_имеет_вид_скачано_x_из_y() -> None:
    job, _ = make_job()
    job.progress.downloaded = 2
    job.progress.total = 5
    assert job.progress.label == "скачано 2 из 5"


def test_событие_прогресса_исполнителя_меняет_процент_и_скорость() -> None:
    """Видео идёт долго: процент и скорость приходят от исполнителя."""
    job, events = make_job()
    job.handle_download_event(
        DownloadEvent(
            DownloadEventKind.PROGRESS,
            percent=45.2,
            bytes_per_second=5 * 1024 * 1024,
        )
    )

    assert job.progress.percent == pytest.approx(45.2)
    assert job.progress.bytes_per_second == pytest.approx(5 * 1024 * 1024)
    assert any(e.kind is JobEventKind.PROGRESS for e in events)


def test_скорость_исполнителя_не_затирается_средней_по_объёму() -> None:
    """Средняя скорость считается по объёму файла, а у видео он один и большой."""
    job, _ = make_job(DownloadResult(1, 0, 0, 0, ("a.mp4",)), ["a.mp4"])
    job.start()

    job.handle_download_event(
        DownloadEvent(DownloadEventKind.PROGRESS, percent=10.0, bytes_per_second=1024.0)
    )

    assert job.progress.bytes_per_second == pytest.approx(1024.0)


def test_менеджер_раздаёт_разные_идентификаторы() -> None:
    manager = JobManager()
    first = manager.submit("https://pin.it/a", "/tmp")
    second = manager.submit("https://pin.it/b", "/tmp")
    assert first.job_id != second.job_id


def test_менеджер_кладёт_загрузки_в_список() -> None:
    manager = JobManager()
    manager.submit("https://pin.it/a", "/tmp")
    assert len(manager.jobs) == 1


def test_запуск_не_в_очереди_запрещён() -> None:
    job, _ = make_job()
    job.cancel()
    with pytest.raises(RuntimeError):
        job.start()
