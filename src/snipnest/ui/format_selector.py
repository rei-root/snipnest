"""Выбор формата сохранения в окне.

Виджет показывает форматы для того, что в поле ссылки: картинку или видео.
Выбор помнится отдельно для каждого вида ссылки — переключение «фото — видео»
не сбрасывает его.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from ..formats import (
    AUDIO_FORMATS,
    DEFAULT_AUDIO,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_IMAGE,
    DEFAULT_IMAGE_FORMAT,
    DEFAULT_VIDEO,
    DEFAULT_VIDEO_FORMAT,
    IMAGE_FORMATS,
    VIDEO_FORMATS,
    FormatKind,
    SaveFormat,
    audio_format_by_id,
    image_format_by_id,
    video_format_by_id,
)

__all__ = ["FormatSelector"]

#: Варианты видео, для которых владелец выбирает формат звука: «только звук»
#: и «видео и звук отдельными файлами».
AUDIO_NEEDED_IDS = ("audio", "separate")


class FormatSelector(QWidget):
    """Список форматов сохранения: подстраивается под вид ссылки."""

    #: Владелец сменил формат — пора запомнить выбор.
    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = FormatKind.IMAGE
        self._image_id = DEFAULT_IMAGE_FORMAT
        self._video_id = DEFAULT_VIDEO_FORMAT
        self._audio_id = DEFAULT_AUDIO_FORMAT

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Формат:", self))

        self._format_combo = QComboBox(self)
        layout.addWidget(self._format_combo, 1)

        self._audio_label = QLabel("Звук:", self)
        layout.addWidget(self._audio_label)
        self._audio_combo = QComboBox(self)
        layout.addWidget(self._audio_combo)

        for fmt in AUDIO_FORMATS:
            self._audio_combo.addItem(fmt.title, fmt.id)
        self._fill_formats()

        self._format_combo.currentIndexChanged.connect(self._on_format_changed)
        self._audio_combo.currentIndexChanged.connect(self._on_audio_changed)

    # -- состояние ----------------------------------------------------------

    @property
    def kind(self) -> FormatKind:
        """Что сейчас выбирается: картинка или видео."""
        return self._kind

    @property
    def image_id(self) -> str:
        """Выбранный формат картинки."""
        return self._image_id

    @property
    def video_id(self) -> str:
        """Выбранный формат видео."""
        return self._video_id

    @property
    def audio_id(self) -> str:
        """Выбранный формат звука."""
        return self._audio_id

    # -- действия -----------------------------------------------------------

    def set_kind(self, kind: FormatKind) -> None:
        """Показать форматы для вида ссылки."""
        if kind == self._kind:
            return
        self._save_current()
        self._kind = kind
        self._fill_formats()

    def set_choices(self, image_id: str, video_id: str, audio_id: str) -> None:
        """Восстановить последний выбор владельца."""
        if image_format_by_id(image_id) is not None:
            self._image_id = image_id
        if video_format_by_id(video_id) is not None:
            self._video_id = video_id
        if audio_format_by_id(audio_id) is not None:
            self._audio_id = audio_id
        index = self._audio_combo.findData(self._audio_id)
        if index >= 0:
            self._audio_combo.blockSignals(True)
            self._audio_combo.setCurrentIndex(index)
            self._audio_combo.blockSignals(False)
        self._fill_formats()

    def select_format(self, format_id: str) -> None:
        """Выбрать формат — как будто владелец выбрал его в списке."""
        index = self._format_combo.findData(format_id)
        if index >= 0:
            self._format_combo.setCurrentIndex(index)

    def select_audio(self, audio_id: str) -> None:
        """Выбрать формат звука."""
        index = self._audio_combo.findData(audio_id)
        if index >= 0:
            self._audio_combo.setCurrentIndex(index)

    def format_ids(self) -> list[str]:
        """Идентификаторы форматов в списке."""
        return [
            str(self._format_combo.itemData(index)) for index in range(self._format_combo.count())
        ]

    def audio_ids(self) -> list[str]:
        """Идентификаторы форматов звука в списке."""
        return [
            str(self._audio_combo.itemData(index)) for index in range(self._audio_combo.count())
        ]

    def audio_enabled(self) -> bool:
        """Нужен ли владельцу формат звука для выбранного варианта."""
        return (
            self._kind is FormatKind.VIDEO
            and str(self._format_combo.currentData()) in AUDIO_NEEDED_IDS
        )

    def selected_format(self) -> SaveFormat:
        """Выбор владельца — объектом."""
        format_id = str(self._format_combo.currentData())
        audio_id = str(self._audio_combo.currentData())
        if self._kind is FormatKind.IMAGE:
            image = image_format_by_id(format_id) or DEFAULT_IMAGE
            return SaveFormat(kind=FormatKind.IMAGE, image=image)
        video = video_format_by_id(format_id) or DEFAULT_VIDEO
        audio = audio_format_by_id(audio_id) or DEFAULT_AUDIO
        return SaveFormat(kind=FormatKind.VIDEO, video=video, audio=audio)

    # -- внутреннее ---------------------------------------------------------

    def _current_id(self) -> str:
        """Выбранный идентификатор для текущего вида ссылки."""
        return self._image_id if self._kind is FormatKind.IMAGE else self._video_id

    def _save_current(self) -> None:
        """Запомнить выбор текущего вида ссылки."""
        current = str(self._format_combo.currentData())
        if self._kind is FormatKind.IMAGE:
            self._image_id = current
        else:
            self._video_id = current

    def _fill_formats(self) -> None:
        """Наполнить список форматов под текущий вид ссылки."""
        formats = IMAGE_FORMATS if self._kind is FormatKind.IMAGE else VIDEO_FORMATS
        self._format_combo.blockSignals(True)
        self._format_combo.clear()
        for fmt in formats:
            self._format_combo.addItem(fmt.title, fmt.id)
        index = self._format_combo.findData(self._current_id())
        self._format_combo.setCurrentIndex(index if index >= 0 else 0)
        self._format_combo.blockSignals(False)
        self._update_audio_enabled()

    def _update_audio_enabled(self) -> None:
        """Формат звука нужен вариантам «только звук» и «видео и звук отдельно»."""
        needs_audio = self.audio_enabled()
        self._audio_combo.setEnabled(needs_audio)
        self._audio_label.setEnabled(needs_audio)

    def _on_format_changed(self, index: int) -> None:
        """Владелец выбрал другой формат."""
        self._save_current()
        self._update_audio_enabled()
        self.changed.emit()

    def _on_audio_changed(self, index: int) -> None:
        """Владелец выбрал другой формат звука."""
        self._audio_id = str(self._audio_combo.currentData())
        self.changed.emit()
