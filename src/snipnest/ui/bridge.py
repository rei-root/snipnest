"""Мост между рабочим потоком загрузки и GUI-потоком Qt.

Рабочий поток никогда не трогает виджеты: он кладёт события в очередь,
а Qt-сигнал переносит их в GUI-поток, где их разбирает окно.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QThread, Signal

from ..jobs import DownloadJob, JobEvent, JobEventKind

__all__ = ["JobEventBridge", "JobWorker"]


class JobEventBridge(QObject):
    """Принимает события из рабочего потока и отдаёт их в GUI-поток."""

    events_ready = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lock = threading.Lock()
        self._pending: list[JobEvent] = []

    def post(self, event: JobEvent) -> None:
        """Вызывается из рабочего потока: записать событие в очередь.

        Сигнал ``events_ready`` доставляется в GUI-поток: приёмник живёт
        в другом потоке, поэтому Qt переносит вызов сам.
        """
        with self._lock:
            self._pending.append(event)
        self.events_ready.emit()

    def post_error(self, job_id: str, text: str) -> None:
        """Сообщить об ошибке, не связанной с состоянием загрузки."""
        self.post(JobEvent(kind=JobEventKind.ERROR, job_id=job_id, text=text))

    def take_pending(self) -> list[JobEvent]:
        """Забрать и очистить накопленные события."""
        with self._lock:
            pending = self._pending
            self._pending = []
        return pending


class JobWorker(QThread):
    """Загрузка в отдельном потоке: Qt-сигналы приходят в GUI-поток.

    Сигнал ``finished`` (встроенный в QThread) означает, что поток
    действительно закончил работу: только тогда его можно удалять.
    """

    def __init__(
        self,
        job: DownloadJob,
        bridge: JobEventBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._job = job
        self._bridge = bridge

    def run(self) -> None:
        """Выполнить загрузку. Ошибки не поднимаются наружу — они события."""
        job_id = self._job.job_id
        try:
            self._job.start()
        except Exception as exc:  # noqa: BLE001 - загрузка не должна ронять поток
            self._bridge.post_error(job_id, str(exc) or exc.__class__.__name__)
