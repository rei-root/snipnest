"""Показ события загрузки в интерфейсе.

Правила показа вынесены отдельно от окна: окно собирает виджеты,
презентер решает, что на них показать.
"""

from __future__ import annotations

from collections.abc import Callable

from ..jobs import JobEvent, JobEventKind, JobState
from .models import JobRow

__all__ = ["EventPresenter"]


class EventPresenter:
    """Переводит событие загрузки в изменения интерфейса."""

    def __init__(
        self,
        set_status: Callable[[str], None],
        append_log: Callable[[str], None],
    ) -> None:
        self._set_status = set_status
        self._append_log = append_log

    def apply(self, row: JobRow, event: JobEvent) -> None:
        """Обновить строку загрузки и показать событие."""
        row.apply(event)
        if event.kind is JobEventKind.LOG and event.text:
            self._append_log(event.text)
        elif event.kind is JobEventKind.ERROR and event.text:
            self._append_log(f"[ошибка] {event.text}")
            self._set_status(f"Ошибка загрузки: {event.text}")
        elif event.kind is JobEventKind.RESULT:
            self._set_status(f"Итог: {row.result_label or 'нет данных'}")
        elif event.kind is JobEventKind.STATE_CHANGED and event.state is JobState.DONE:
            self._set_status(f"Загрузка завершена: {row.result_label}")
