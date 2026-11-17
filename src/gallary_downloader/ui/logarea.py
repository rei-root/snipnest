"""Сворачиваемая область лога вывода gallery-dl."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

__all__ = ["LogArea"]


class LogArea(QWidget):
    """Лог с кнопкой свернуть/развернуть."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("Лог gallery-dl", self))
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

    @property
    def text(self) -> str:
        """Весь накопленный лог."""
        return self.view.toPlainText()

    def append(self, line: str) -> None:
        """Дописать строку в лог."""
        self.view.append(line)

    def set_expanded(self, expanded: bool) -> None:
        """Развернуть или свернуть область лога."""
        self.view.setVisible(expanded)
        self.toggle_button.setText("Свернуть" if expanded else "Развернуть")
