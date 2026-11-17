"""Управление загрузками в окне: очередь, потоки, отмена и повтор.

Контроллер не знает про виджеты: он работает с загрузками и отдаёт события
наружу. Окно подписывается на них.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ..jobs import DownloadJob, JobEvent
from .bridge import JobEventBridge, JobWorker

__all__ = ["JobController"]


class JobController(QObject):
    """Ведёт загрузки окна: создаёт, запускает, отменяет, повторяет."""

    job_added = Signal(object)
    job_finished = Signal(str)

    def __init__(
        self,
        bridge: JobEventBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._bridge = bridge
        self._workers: dict[str, JobWorker] = {}
        self._jobs: dict[str, DownloadJob] = {}

    @property
    def jobs(self) -> dict[str, DownloadJob]:
        """Загрузки по идентификаторам."""
        return dict(self._jobs)

    def job(self, job_id: str) -> DownloadJob | None:
        """Загрузка по идентификатору."""
        return self._jobs.get(job_id)

    def add(self, job: DownloadJob) -> None:
        """Принять готовую загрузку и показать её."""
        self._jobs[job.job_id] = job
        self.job_added.emit(job)

    def start(self, job: DownloadJob) -> None:
        """Запустить загрузку в отдельном потоке.

        Если загрузка уже идёт, её поток дожидается завершения: иначе
        два потока работали бы с одной загрузкой.
        """
        previous = self._workers.get(job.job_id)
        if previous is not None:
            previous.wait()
        worker = JobWorker(job, self._bridge, self)
        # Удалять поток можно только после его реального завершения:
        # сигнал finished приходит тогда, когда run() уже вышел.
        worker.finished.connect(lambda w=worker: self._on_worker_finished(job.job_id, w))
        self._workers[job.job_id] = worker
        worker.start()

    def cancel(self, job_id: str) -> bool:
        """Остановить загрузку. True, если остановлена."""
        job = self._jobs.get(job_id)
        if job is None:
            return False
        return job.cancel()

    def retry(self, job_id: str) -> bool:
        """Повторить загрузку. True, если повтор запущен.

        Прежний поток дожидается завершения: иначе два потока работали
        бы с одной загрузкой.
        """
        job = self._jobs.get(job_id)
        if job is None:
            return False
        previous = self._workers.get(job_id)
        if previous is not None:
            previous.wait()
        if not job.retry():
            return False
        self.start(job)
        return True

    def shutdown(self) -> None:
        """Остановить все загрузки и дождаться потоков.

        Вызывается при закрытии окна: висящий поток QThread при
        уничтожении роняет приложение.
        """
        for job in list(self._jobs.values()):
            job.cancel()
        for worker in list(self._workers.values()):
            worker.wait()
            worker.deleteLater()
        self._workers.clear()

    def post_event(self, event: JobEvent) -> None:
        """Событие из рабочего потока: только кладём в очередь."""
        self._bridge.post(event)

    def _on_worker_finished(self, job_id: str, worker: JobWorker) -> None:
        """Поток закончился: убрать его из реестра.

        Убирается только тот поток, который закончился: под тем же
        идентификатором может уже идти следующая попытка.
        """
        if self._workers.get(job_id) is worker:
            self._workers.pop(job_id, None)
        worker.deleteLater()
        self.job_finished.emit(job_id)
