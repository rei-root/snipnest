"""Панель списка загрузок: строки со ссылкой, состоянием и прогрессом."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import (
    Property,
    QAbstractAnimation,
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    Signal,
)
from PySide6.QtGui import QBrush, QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..jobs import DownloadJob
from .models import JobRow

__all__ = ["JobsPanel"]

_COLUMNS = ("Ссылка", "Состояние", "Прогресс", "Скорость", "Файлы", "Итог")

#: Длительность появления новой строки.
ROW_FADE_DURATION_MS = 180


class _RowFade(QObject):
    """Прозрачность текста новой строки: растёт от нуля до единицы."""

    value_changed = Signal(float)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._value = 0.0

    def _get_value(self) -> float:
        return self._value

    def set_opacity(self, value: float) -> None:
        """Задать прозрачность текста строки."""
        self._value = value
        self.value_changed.emit(value)

    @property
    def opacity(self) -> float:
        """Текущая прозрачность текста строки."""
        return self._value

    value = Property(float, _get_value, set_opacity)


class JobsPanel(QWidget):
    """Список загрузок с прогрессом, скоростью, файлами и итогом."""

    def __init__(
        self,
        on_cancel: Callable[[str], None],
        on_retry: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_cancel = on_cancel
        self._on_retry = on_retry
        self._rows: dict[str, JobRow] = {}
        self._order: list[str] = []
        self._jobs: dict[str, DownloadJob] = {}
        self._fades: dict[str, _RowFade] = {}

        layout = QVBoxLayout(self)

        self._table = QTableWidget(0, len(_COLUMNS), self)
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for index in range(1, len(_COLUMNS)):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)
        self._table.itemSelectionChanged.connect(self._refresh_files)
        layout.addWidget(self._table)

        buttons = QHBoxLayout()
        self._cancel_button = QPushButton("Остановить", self)
        self._cancel_button.clicked.connect(self._cancel_selected)
        self._retry_button = QPushButton("Повторить", self)
        self._retry_button.clicked.connect(self._retry_selected)
        buttons.addWidget(self._cancel_button)
        buttons.addWidget(self._retry_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        layout.addWidget(QLabel("Файлы выбранной загрузки:", self))
        self._files_list = QListWidget(self)
        self._files_list.setMinimumHeight(90)
        layout.addWidget(self._files_list)

    @property
    def row_count(self) -> int:
        """Сколько загрузок в списке."""
        return len(self._order)

    def job_ids(self) -> list[str]:
        """Идентификаторы загрузок в порядке показа."""
        return list(self._order)

    def row_for(self, job_id: str) -> JobRow | None:
        """Строка загрузки по идентификатору."""
        return self._rows.get(job_id)

    def add_job(self, job: DownloadJob) -> None:
        """Добавить загрузку в список."""
        self._jobs[job.job_id] = job
        self._rows[job.job_id] = JobRow(
            job_id=job.job_id,
            url=job.url,
            destination=job.destination,
        )
        self._order.append(job.job_id)
        self._table.insertRow(self._table.rowCount())
        self._render_row(job.job_id)
        self._start_row_fade(job.job_id)

    def row_opacity(self, job_id: str) -> float:
        """Насколько проявилась строка загрузки: от нуля до единицы."""
        fade = self._fades.get(job_id)
        return fade.opacity if fade is not None else 1.0

    def _start_row_fade(self, job_id: str) -> None:
        """Новая строка появляется плавно: текст проявляется постепенно."""
        fade = _RowFade(self)
        self._fades[job_id] = fade
        fade.value_changed.connect(lambda value: self._apply_row_opacity(job_id, value))
        fade.set_opacity(0.0)

        animation = QPropertyAnimation(fade, b"value", self)
        animation.setDuration(ROW_FADE_DURATION_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

    def _apply_row_opacity(self, job_id: str, value: float) -> None:
        """Сделать текст строки прозрачнее или плотнее."""
        if job_id not in self._order:
            return
        index = self._order.index(job_id)
        color = QColor(self.palette().color(QPalette.ColorRole.WindowText))
        color.setAlphaF(min(1.0, max(0.0, value)))
        brush = QBrush(color)
        for column in range(len(_COLUMNS)):
            item = self._table.item(index, column)
            if item is not None:
                item.setForeground(brush)

    def update_row(self, job_id: str) -> None:
        """Перерисовать строку по текущему состоянию загрузки."""
        if job_id not in self._rows:
            return
        self._render_row(job_id)

    def selected_job_id(self) -> str | None:
        """Идентификатор выбранной загрузки."""
        row = self._table.currentRow()
        if row < 0 or row >= len(self._order):
            return None
        return self._order[row]

    def selected_file_names(self) -> list[str]:
        """Имена файлов выбранной загрузки."""
        return [self._files_list.item(i).text() for i in range(self._files_list.count())]

    def _render_row(self, job_id: str) -> None:
        row = self._rows[job_id]
        index = self._order.index(job_id)
        values = (
            row.url,
            row.state_label,
            row.progress_label,
            row.speed_label,
            str(len(row.files)),
            row.result_label,
        )
        for column, value in enumerate(values):
            item = self._table.item(index, column)
            if item is None:
                item = QTableWidgetItem()
                self._table.setItem(index, column, item)
            item.setText(value)
            item.setToolTip(row.summary())
        self._table.resizeRowsToContents()
        self._update_buttons(row)
        if self.selected_job_id() == job_id:
            self._refresh_files()

    def _update_buttons(self, row: JobRow) -> None:
        job = self._jobs.get(row.job_id)
        can_cancel = job.can_cancel() if job is not None else False
        can_retry = job.can_retry() if job is not None else False
        self._cancel_button.setEnabled(can_cancel)
        self._retry_button.setEnabled(can_retry)

    def _refresh_files(self) -> None:
        """Показать файлы выбранной загрузки."""
        self._files_list.clear()
        job_id = self.selected_job_id()
        if job_id is None:
            return
        row = self._rows.get(job_id)
        if row is None:
            return
        for name in row.file_names:
            self._files_list.addItem(name)

    def _cancel_selected(self) -> None:
        job_id = self.selected_job_id()
        if job_id is not None:
            self._on_cancel(job_id)

    def _retry_selected(self) -> None:
        job_id = self.selected_job_id()
        if job_id is not None:
            self._on_retry(job_id)
