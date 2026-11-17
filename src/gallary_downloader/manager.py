"""Менеджер загрузок: список и параллельный запуск."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .jobs import DownloadJob, JobEvent

__all__ = ["JobManager"]


class JobManager:
    """Ведёт список загрузок и запускает их в отдельных потоках."""

    def __init__(self, on_event: Callable[[JobEvent], None] | None = None) -> None:
        self.jobs: list[DownloadJob] = []
        self._on_event = on_event
        self._counter = 0
        self._lock = threading.Lock()

    def submit(self, url: str, destination: str) -> DownloadJob:
        """Поставить загрузку в очередь."""
        from .jobs import DownloadJob

        with self._lock:
            self._counter += 1
            job_id = f"job-{self._counter}"
        job = DownloadJob(job_id, url, destination, on_event=self._on_event)
        self.jobs.append(job)
        return job

    def start_all(self) -> None:
        """Запустить все загрузки из очереди — параллельно."""
        from .jobs import JobState

        threads = [
            threading.Thread(target=job.start, daemon=True)
            for job in self.jobs
            if job.state is JobState.QUEUED
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
