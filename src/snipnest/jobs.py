"""Жизненный цикл загрузки: состояния, права, видимость, прогресс.

Состояния и переходы повторяют граф машинной нормы
``docs/ba/spec/app-spec/model/transitions.yaml``.
"""

from __future__ import annotations

import dataclasses
import enum
import time
from collections.abc import Callable
from pathlib import Path

from .downloader import (
    DownloadEvent,
    DownloadEventKind,
    DownloadResult,
    DownloadRunner,
    GalleryDlRunner,
)
from .manager import JobManager

__all__ = [
    "JobState",
    "JobEvent",
    "JobEventKind",
    "JobProgress",
    "DownloadJob",
    "JobManager",
]


def _file_size(path: str) -> int:
    """Размер скачанного файла в байтах. 0, если файл недоступен."""
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


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
    percent: float | None = None
    result: DownloadResult | None = None


@dataclasses.dataclass
class JobProgress:
    """Счётчики прогресса по загрузке."""

    downloaded: int = 0
    skipped: int = 0
    total: int = 0
    bytes_per_second: float = 0.0
    percent: float | None = None

    @property
    def label(self) -> str:
        """Подпись «скачано X из Y»."""
        return f"скачано {self.downloaded} из {self.total}"


class DownloadJob:
    """Одна загрузка: ссылка, папка сохранения, состояние, прогресс."""

    def __init__(
        self,
        job_id: str,
        url: str,
        destination: str,
        runner: DownloadRunner | None = None,
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
        self._started_at: float | None = None
        self._bytes_at_start: int = 0
        self._bytes_downloaded: int = 0
        self._counting: bool = False

    def set_event_sink(self, on_event: Callable[[JobEvent], None] | None) -> None:
        """Подключить подписчика событий после создания загрузки."""
        self._on_event = on_event

    @property
    def runner(self) -> DownloadRunner:
        """Исполнитель загрузки."""
        return self._runner

    def set_runner(self, runner: DownloadRunner) -> None:
        """Подключить исполнителя: его события идут в загрузку.

        Без этого загрузка узнаёт о файлах только по итогу, а прогресс
        во время скачивания не идёт. Исполнитель, который не умеет
        раздавать события (заглушка в тестах), просто не шлёт их.
        """
        self._runner = runner
        sink = getattr(runner, "set_event_sink", None)
        if callable(sink):
            sink(self.handle_download_event)

    def can_cancel(self) -> bool:
        """Владелец может отменить загрузку в этом состоянии."""
        return self.state in (JobState.QUEUED, JobState.RUNNING)

    def can_retry(self) -> bool:
        """Владелец может повторить загрузку в этом состоянии."""
        return self.state in (JobState.FAILED, JobState.CANCELLED)

    def visible_fields(self) -> tuple[str, ...]:
        """Какие поля загрузки видит владелец в этом состоянии."""
        if self.state is JobState.QUEUED:
            return ("ссылка", "папка_сохранения")
        return (
            "ссылка",
            "папка_сохранения",
            "прогресс",
            "скорость",
            "список_файлов",
            "лог",
        )

    def _current_state(self) -> JobState:
        """Состояние загрузки прямо сейчас.

        Отдельный метод нужен потому, что состояние меняет и поток
        загрузки, и поток интерфейса: значение читается заново, а не
        берётся из того места, где его сузил анализатор.
        """
        return self.state

    def start(self) -> None:
        """Перевести загрузку из очереди в выполнение и дождаться итога."""
        if self.state is not JobState.QUEUED:
            raise RuntimeError(f"загрузку нельзя запустить из состояния {self.state.value}")
        self._set_state(JobState.RUNNING)
        self._started_at = time.monotonic()
        self._bytes_at_start = 0
        try:
            self._counting = True
            self.progress.total = self._runner.count_files(self.url)
            self._counting = False
            self._emit_progress()
            self.result = self._runner.run(self.url)
        except Exception as exc:
            self._counting = False
            if self._current_state() is JobState.CANCELLED:
                return
            self.error_text = str(exc) or exc.__class__.__name__
            self._set_state(JobState.FAILED)
            self._emit(JobEventKind.ERROR, text=self.error_text)
            return

        self.progress.downloaded = self.result.downloaded
        self.progress.skipped = self.result.skipped
        self.files = list(self.result.files)
        self._measure_speed()
        self._emit_progress()
        self._emit(JobEventKind.RESULT, result=self.result)
        if self._current_state() is JobState.CANCELLED:
            # Пока шёл download, владелец отменил загрузку: итог уже не
            # перебивает отмену, иначе состояние скачет.
            return
        if self.result.returncode == 0:
            self._set_state(JobState.DONE)
        else:
            self.error_text = f"{self._runner.name} завершился с кодом {self.result.returncode}"
            self._set_state(JobState.FAILED)
            self._emit(JobEventKind.ERROR, text=self.error_text)

    def cancel(self) -> bool:
        """Отменить загрузку. True, если отмена состоялась."""
        if not self.can_cancel():
            return False
        if self.state is JobState.RUNNING:
            self._runner.cancel()
        self._set_state(JobState.CANCELLED)
        return True

    def retry(self) -> bool:
        """Повторить загрузку после ошибки или отмены."""
        if not self.can_retry():
            return False
        self.state = JobState.QUEUED
        self.progress = JobProgress()
        self.files = []
        self.result = None
        self.error_text = ""
        self._started_at = None
        self._bytes_at_start = 0
        self._bytes_downloaded = 0
        self._counting = False
        self._set_state(JobState.QUEUED)
        return True

    def handle_download_event(self, event: DownloadEvent) -> None:
        """Перевести событие исполнителя в событие загрузки."""
        if self._counting:
            # Предварительный проход --simulate только считает файлы:
            # в список скачанных они не попадают.
            return
        if event.kind is DownloadEventKind.PROGRESS:
            # Процент и скорость приходят от исполнителя: у видео один
            # файл на полтора часа, счётчик файлов тут бесполезен.
            if event.percent is not None:
                self.progress.percent = event.percent
            if event.bytes_per_second is not None:
                # Скорость исполнителя своя: средняя по объёму посчитается
                # только после конца файла, а до этого она была бы нулём.
                self.progress.bytes_per_second = event.bytes_per_second
            self._emit_progress()
        elif event.kind is DownloadEventKind.FILE_DOWNLOADED:
            self.progress.downloaded += 1
            if event.path:
                self.files.append(event.path)
                self._bytes_downloaded += _file_size(event.path)
            self._measure_speed()
            self._emit_progress()
            self._emit(JobEventKind.FILE, path=event.path, text=event.text)
        elif event.kind is DownloadEventKind.FILE_SKIPPED:
            self.progress.skipped += 1
            self._emit_progress()
            self._emit(JobEventKind.FILE, path=event.path, text=event.text)
        elif event.kind is DownloadEventKind.ERROR:
            self.log_lines.append(event.text)
            self._emit(JobEventKind.ERROR, text=event.text)
        else:
            self.log_lines.append(event.text)
            self._emit(JobEventKind.LOG, text=event.text)

    def _measure_speed(self) -> None:
        """Пересчитать среднюю скорость по объёму скачанного и времени."""
        if self._started_at is None:
            return
        elapsed = time.monotonic() - self._started_at
        if elapsed <= 0:
            return
        transferred = self._bytes_downloaded - self._bytes_at_start
        self.progress.bytes_per_second = max(0.0, transferred / elapsed)

    def _set_state(self, state: JobState) -> None:
        self.state = state
        self._emit(JobEventKind.STATE_CHANGED, state=state)

    def _emit_progress(self) -> None:
        self._emit(
            JobEventKind.PROGRESS,
            downloaded=self.progress.downloaded,
            total=self.progress.total,
            bytes_per_second=self.progress.bytes_per_second,
            percent=self.progress.percent,
        )

    def _emit(self, kind: JobEventKind, **fields: object) -> None:
        if self._on_event is None:
            return
        event = JobEvent(kind=kind, job_id=self.job_id)
        state = fields.get("state")
        text = fields.get("text")
        path = fields.get("path")
        downloaded = fields.get("downloaded")
        total = fields.get("total")
        speed = fields.get("bytes_per_second")
        percent = fields.get("percent")
        result = fields.get("result")
        self._on_event(
            dataclasses.replace(
                event,
                state=state if isinstance(state, JobState) else None,
                text=text if isinstance(text, str) else "",
                path=path if isinstance(path, str) else None,
                downloaded=downloaded if isinstance(downloaded, int) else 0,
                total=total if isinstance(total, int) else 0,
                bytes_per_second=speed if isinstance(speed, float) else 0.0,
                percent=percent if isinstance(percent, float) else None,
                result=result if isinstance(result, DownloadResult) else None,
            )
        )
