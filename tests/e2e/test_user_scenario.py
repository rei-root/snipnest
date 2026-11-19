"""E2E-тест: сценарий пользователя целиком.

Тест офлайн: бинарник gallery-dl подменяется заглушкой, которая ведёт себя
как настоящий по контракту вывода.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from snipnest.jobs import JobManager, JobState  # noqa: E402


class StubRunner:
    """Заглушка gallery-dl: отдаёт два файла и успешный код возврата."""

    #: Имя исполнителя — оно попадает в сообщение об ошибке.
    name = "gallery-dl"

    def __init__(self) -> None:
        self.cancelled = False

    def count_files(self, url: str) -> int:
        return 2

    def run(self, url: str, *, simulate: bool = False) -> object:
        from snipnest.downloader import DownloadResult

        return DownloadResult(2, 0, 0, 0, ("a.jpg", "b.jpg"))

    def cancel(self) -> bool:
        self.cancelled = True
        return True


def test_сценарий_пользователя_ставит_загрузку_в_очередь(tmp_path) -> None:
    manager = JobManager()
    job = manager.submit("https://pin.it/abc", str(tmp_path))
    assert job.state is JobState.QUEUED
    assert len(manager.jobs) == 1


def test_сценарий_пользователя_доходит_до_завершения(tmp_path) -> None:
    manager = JobManager()
    job = manager.submit("https://pin.it/abc", str(tmp_path))
    job._runner = StubRunner()  # noqa: SLF001 - подмена внешнего процесса
    job.start()

    assert job.state is JobState.DONE
    assert job.progress.downloaded == 2
    assert job.progress.total == 2
    assert job.progress.label == "скачано 2 из 2"


def test_сценарий_пользователя_видит_папку_сохранения(tmp_path) -> None:
    manager = JobManager()
    job = manager.submit("https://pin.it/abc", str(tmp_path))
    assert job.destination == str(tmp_path)
