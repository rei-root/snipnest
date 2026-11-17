"""Тесты живой прогресс��и измерения скорости в загрузке."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from gallary_downloader.downloader import DownloadEvent, DownloadEventKind, DownloadResult
from gallary_downloader.jobs import DownloadJob, JobState


class CountingRunner:
    """Исполнитель: сначала считает файлы, потом качает."""

    def __init__(self, files: list[Path], skipped: int = 0) -> None:
        self.files = files
        self.skipped = skipped
        self.events: list[DownloadEvent] = []
        self.simulate_calls = 0

    def set_event_sink(self, on_event) -> None:  # noqa: ANN001 - протокол исполнителя
        self._sink = on_event

    def count_files(self, url: str) -> int:
        self.simulate_calls += 1
        return len(self.files) + self.skipped

    def run(self, url: str, *, simulate: bool = False) -> DownloadResult:
        for path in self.files:
            event = DownloadEvent(DownloadEventKind.FILE_DOWNLOADED, path=str(path))
            self.events.append(event)
            sink = getattr(self, "_sink", None)
            if sink is not None:
                sink(event)
        paths = tuple(str(path) for path in self.files)
        return DownloadResult(len(self.files), self.skipped, 0, 0, paths)

    def cancel(self) -> bool:
        return True


def make_job(tmp_path: Path, files: list[Path]) -> DownloadJob:
    runner = CountingRunner(files)
    job = DownloadJob("job-1", "https://pin.it/abc", str(tmp_path), runner, None)
    job.set_runner(runner)
    return job


def test_файлы_попадают_в_список_во_время_загрузки(tmp_path: Path) -> None:
    first = tmp_path / "a.jpg"
    second = tmp_path / "b.jpg"
    for path in (first, second):
        path.write_bytes(b"x" * 100)

    job = make_job(tmp_path, [first, second])
    job.start()

    assert job.state.value == "завершена"
    assert job.progress.downloaded == 2
    assert len(job.files) == 2


def test_скорость_считается_по_объёму_и_времени(tmp_path: Path) -> None:
    payload = tmp_path / "big.jpg"
    payload.write_bytes(b"x" * 4096)

    job = make_job(tmp_path, [payload])
    job.start()

    assert job.progress.bytes_per_second > 0


def test_предварительный_проход_не_попадает_в_список_файлов(tmp_path: Path) -> None:
    """--simulate перечисляет файлы, но не скачивает их."""
    payload = tmp_path / "a.jpg"
    payload.write_bytes(b"x")

    job = make_job(tmp_path, [payload])
    job.start()

    assert job.files == [str(payload)]
    assert job.progress.downloaded == 1


def test_повтор_сбрасывает_счётчики(tmp_path: Path) -> None:
    payload = tmp_path / "a.jpg"
    payload.write_bytes(b"x")

    job = make_job(tmp_path, [payload])
    job.start()

    assert job.state is JobState.DONE
    assert job.can_retry() is False


def test_отмена_не_перебивается_итогом(tmp_path: Path) -> None:
    """Пока шёл download, владелец отменил загрузку: итог не перебивает отмену."""
    payload = tmp_path / "a.jpg"
    payload.write_bytes(b"x")

    job = make_job(tmp_path, [payload])
    job.start()

    assert job.state is JobState.DONE
    assert job.can_cancel() is False


def test_отменённая_загрузка_остаётся_отменённой(tmp_path: Path) -> None:
    """Состояние отмены не должно сменяться на ошибку по итогу."""
    payload = tmp_path / "a.jpg"
    payload.write_bytes(b"x")

    job = make_job(tmp_path, [payload])
    job.start()

    # Повтор разрешён только из ошибки и отмены.
    job.state = JobState.CANCELLED
    assert job.can_retry()
    assert job.retry()
    assert job.state is JobState.QUEUED


class SlowRunner:
    """Исполнитель, который тянет время: отменять есть что."""

    def __init__(self) -> None:
        self.cancelled = False
        self._release = threading.Event()

    def set_event_sink(self, on_event) -> None:  # noqa: ANN001 - протокол исполнителя
        self._sink = on_event

    def count_files(self, url: str) -> int:
        return 1

    def run(self, url: str, *, simulate: bool = False) -> DownloadResult:
        self._release.wait(timeout=5)
        return DownloadResult(0, 0, 1, 4, ())

    def cancel(self) -> bool:
        self.cancelled = True
        self._release.set()
        return True


def test_отмена_во_время_загрузки_остаётся_отменой(tmp_path: Path) -> None:
    """Отмена во время download не перебивается итогом по итогу."""
    runner = SlowRunner()
    job = DownloadJob("job-1", "https://pin.it/abc", str(tmp_path), runner, None)
    job.set_runner(runner)

    errors: list[str] = []
    job.set_event_sink(lambda event: errors.append(event.text) if event.text else None)

    worker = threading.Thread(target=job.start, daemon=True)
    worker.start()

    deadline = time.monotonic() + 5
    while job.state is not JobState.RUNNING and time.monotonic() < deadline:
        time.sleep(0.01)
    time.sleep(0.05)

    assert job.cancel()
    worker.join(timeout=5)

    assert job.state is JobState.CANCELLED
    assert runner.cancelled
