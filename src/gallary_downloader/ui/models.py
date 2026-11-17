"""Строка списка загрузок: то, что видит владелец.

Модель не знает про Qt-виджеты: она хранит состояние и отдаёт готовые
подписи. Список в окне рисует её сам.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from ..downloader import DownloadResult
from ..jobs import JobEvent, JobEventKind, JobState

__all__ = ["JobRow", "STATE_LABELS", "format_speed", "format_result"]

STATE_LABELS: dict[JobState, str] = {
    JobState.QUEUED: "в очереди",
    JobState.RUNNING: "выполняется",
    JobState.DONE: "завершена",
    JobState.FAILED: "ошибка",
    JobState.CANCELLED: "отменена",
}


def format_speed(bytes_per_second: float) -> str:
    """Подпись скорости: «1,2 МБ/с»."""
    if bytes_per_second <= 0:
        return "—"
    units = ("Б/с", "КБ/с", "МБ/с", "ГБ/с")
    value = float(bytes_per_second)
    index = 0
    while value >= 1024 and index < len(units) - 1:
        value /= 1024
        index += 1
    if index == 0:
        return f"{value:.0f} {units[index]}"
    return f"{value:.1f} {units[index]}"


def format_result(result: DownloadResult | None) -> str:
    """Итог загрузки: скачано / пропущено / ошибок."""
    if result is None:
        return ""
    return f"скачано: {result.downloaded}, пропущено: {result.skipped}, ошибок: {result.errors}"


@dataclasses.dataclass
class JobRow:
    """Одна загрузка в списке: ссылка, состояние, прогресс, скорость, итог."""

    job_id: str
    url: str
    destination: str
    state: JobState = JobState.QUEUED
    downloaded: int = 0
    skipped: int = 0
    total: int = 0
    bytes_per_second: float = 0.0
    files: list[str] = dataclasses.field(default_factory=list)
    log_lines: list[str] = dataclasses.field(default_factory=list)
    result: DownloadResult | None = None
    error_text: str = ""

    @property
    def state_label(self) -> str:
        """Состояние по-русски."""
        return STATE_LABELS[self.state]

    @property
    def progress_label(self) -> str:
        """Подпись «скачано X из Y»."""
        return f"скачано {self.downloaded} из {self.total}"

    @property
    def speed_label(self) -> str:
        """Подпись скорости."""
        return format_speed(self.bytes_per_second)

    @property
    def result_label(self) -> str:
        """Итог загрузки."""
        return format_result(self.result)

    @property
    def progress_percent(self) -> int:
        """Доля выполнения в процентах для прогресс-бара."""
        if self.total <= 0:
            return 0
        return min(100, int(self.downloaded * 100 / self.total))

    @property
    def file_names(self) -> list[str]:
        """Имена скачанных файлов (без путей)."""
        return [Path(path).name for path in self.files]

    def apply(self, event: JobEvent) -> None:
        """Применить событие загрузки к строке списка."""
        if event.state is not None:
            self.state = event.state
        if event.kind is JobEventKind.PROGRESS:
            self.downloaded = event.downloaded
            self.total = event.total
            self.bytes_per_second = event.bytes_per_second
        elif event.kind is JobEventKind.FILE:
            if event.path and event.path not in self.files:
                self.files.append(event.path)
        elif event.kind is JobEventKind.LOG:
            if event.text:
                self.log_lines.append(event.text)
        elif event.kind is JobEventKind.ERROR:
            if event.text:
                self.log_lines.append(event.text)
                self.error_text = event.text
        elif event.kind is JobEventKind.RESULT:
            self.result = event.result

    def summary(self) -> str:
        """Короткое описание строки для подсказки."""
        parts = [self.url, self.state_label, self.progress_label]
        result = self.result_label
        if result:
            parts.append(result)
        if self.error_text:
            parts.append(self.error_text)
        return " — ".join(parts)
