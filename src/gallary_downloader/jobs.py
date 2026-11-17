"""Жизненный цикл загрузки: состояния, права, видимость, прогресс.

Состояния и переходы повторяют граф машинной нормы
``docs/ba/spec/app-spec/model/transitions.yaml``.
"""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Callable

from .downloader import DownloadEvent, DownloadResult, GalleryDlRunner

__all__ = [
    "JobState",
    "JobEvent",
    "JobEventKind",
    "JobProgress",
    "DownloadJob",
    "JobManager",
]


class JobState(enum.Enum):
    """Состояния загрузки — как в графе нормы."""

    QUEUED = "в_очереди"
    RUNNING = "выполняется"
    DONE = "завершена"
    FAILED = "ошибка"
    CANCELLED = "отменена"


class JobEventKind(enum.Enum):
    """События, которые видит UI по загрузке."""

    STATE_CHANGED = "state_changed"
    PROGRESS = "progress"
    FILE = "file"
    LOG = "log"
    RESULT = "result"
    ERROR = "error"


@dataclasses.dataclass(frozen=True)
class JobEvent:
    """Событие по загрузке."""

    kind: JobEventKind
    job_id: str
    state: JobState | None = None
    text: str = ""
    path: str | None = None
    downloaded: int = 0
    total: int = 0
    bytes_per_second: float = 0.0
    result: DownloadResult | None = None


@dataclasses.dataclass
class JobProgress:
    """Счётчики прогресса по загрузке."""

    downloaded: int = 0
    skipped: int = 0
    total: int = 0
    bytes_per_second: float = 0.0

    @property
    def label(self) -> str:
        """Подпись «скачано X из Y»."""
        raise NotImplementedError


class DownloadJob:
    """Одна загрузка: ссылка, папка сохранения, состояние, прогресс."""

    def __init__(
        self,
        job_id: str,
        url: str,
        destination: str,
        runner: GalleryDlRunner | None = None,
        on_event: Callable[[JobEvent], None] | None = None,
    ) -> None:
        self.job_id = job_id
        self.url = url
        self.destination = destination
        self.state = JobState.QUEUED
        self.progress = JobProgress()
        self.files: list[str] = []
        self.log_lines: list[str] = []
        self.result: DownloadResult | None = None
        self.error_text: str = ""
        self._runner = runner or GalleryDlRunner()
        self._on_event = on_event

    def can_cancel(self) -> bool:
        """Владелец может отменить загрузку в этом состоянии."""
        raise NotImplementedError

    def can_retry(self) -> bool:
        """Владелец может повторить загрузку в этом состоянии."""
        raise NotImplementedError

    def visible_fields(self) -> tuple[str, ...]:
        """Какие поля загрузки видит владелец в этом состоянии."""
        raise NotImplementedError

    def start(self) -> None:
        """Перевести загрузку из очереди в выполнение и дождаться итога."""
        raise NotImplementedError

    def cancel(self) -> bool:
        """Отменить загрузку. True, если отмена состоялась."""
        raise NotImplementedError

    def retry(self) -> bool:
        """Повторить загрузку после ошибки или отмены."""
        raise NotImplementedError

    def handle_download_event(self, event: DownloadEvent) -> None:
        """Перевести событие gallery-dl в событие загрузки."""
        raise NotImplementedError


class JobManager:
    """Ведёт список загрузок и запускает их в отдельных потоках."""

    def __init__(self, on_event: Callable[[JobEvent], None] | None = None) -> None:
        self.jobs: list[DownloadJob] = []
        self._on_event = on_event
        self._counter = 0

    def submit(self, url: str, destination: str) -> DownloadJob:
        """Поставить загрузку в очередь."""
        raise NotImplementedError

    def start_all(self) -> None:
        """Запустить все загрузки из очереди — параллельно."""
        raise NotImplementedError
