"""Сворачиваемая область лога вывода исполнителя."""

from __future__ import annotations

from PySide6.QtCore import QAbstractAnimation, QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

__all__ = ["LogArea"]

#: Длительность сворачивания и разворачивания лога.
ANIMATION_DURATION_MS = 150


class LogArea(QWidget):
    """Лог с кнопкой свернуть/развернуть."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self._title = QLabel("Лог", self)
        header.addWidget(self._title)
        header.addStretch(1)
        self.toggle_button = QToolButton(self)
        self.toggle_button.setText("Свернуть")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        header.addWidget(self.toggle_button)
        layout.addLayout(header)

        self.view = QTextEdit(self)
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.view)

        self._expanded = True
        self._expanded_height = 0
        self._max_height = self.view.maximumHeight()
        self._animation = QPropertyAnimation(self.view, b"maximumHeight", self)
        self._animation.finished.connect(self._on_animation_finished)

    @property
    def title(self) -> str:
        """Название области лога."""
        return self._title.text()

    @property
    def text(self) -> str:
        """Весь накопленный лог."""
        return self.view.toPlainText()

    @property
    def expanded(self) -> bool:
        """Развёрнута ли область лога."""
        return self._expanded

    def append(self, line: str) -> None:
        """Дописать строку в лог."""
        self.view.append(line)

    def is_animating(self) -> bool:
        """Идёт ли сейчас анимация сворачивания или разворачивания."""
        return self._animation.state() == QAbstractAnimation.State.Running

    def set_expanded(self, expanded: bool) -> None:
        """Развернуть или свернуть область лога.

        Сворачивание и разворачивание идут анимацией: высота области меняется
        плавно, а не рывком.
        """
        if self._expanded == expanded and not self.is_animating():
            return
        self._expanded = expanded
        self._animation.stop()

        if expanded:
            self.view.setVisible(True)
            start = 0
            target = max(self._expanded_height, 1)
        else:
            self._expanded_height = max(self.view.height(), 1)
            start = max(self.view.height(), 1)
            target = 0

        self._animation.setDuration(ANIMATION_DURATION_MS)
        self._animation.setStartValue(start)
        self._animation.setEndValue(target)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.start()

    def _on_animation_finished(self) -> None:
        """Анимация закончилась: доводим вид области до конца."""
        if self._expanded:
            self.view.setMaximumHeight(self._max_height)
        else:
            self.view.setMaximumHeight(0)
            self.view.setVisible(False)
        self.toggle_button.setText("Свернуть" if self._expanded else "Развернуть")
