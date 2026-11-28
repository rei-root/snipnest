"""Верхняя часть окна: шапка, поле ссылки, папка сохранения, формат.

Отдельный виджет, чтобы главное окно не разрасталось. Кнопок настроек здесь
нет: они живут в строке меню.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..branding import symbolic_icon
from .format_selector import FormatSelector

__all__ = ["TopControls"]

#: Размер символа приложения в шапке окна.
SYMBOL_SIZE = 32


class TopControls(QWidget):
    """Шапка окна, поле ссылки, выбор папки сохранения и выбор формата."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_link_row())
        layout.addWidget(self._build_destination_row())
        layout.addWidget(self._build_format_row())

    def _build_header(self) -> QWidget:
        """Шапка окна: символ приложения и название."""
        box = QWidget(self)
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)

        self.header_icon = QLabel(box)
        self.header_icon.setFixedSize(SYMBOL_SIZE, SYMBOL_SIZE)
        layout.addWidget(self.header_icon)

        self.header_label = QLabel("Snipnest", box)
        font = self.header_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        self.header_label.setFont(font)
        layout.addWidget(self.header_label)
        layout.addStretch(1)

        self.refresh_header()
        return box

    def refresh_header(self) -> None:
        """Перерисовать символ: он красится цветом текста темы."""
        self.header_icon.setPixmap(symbolic_icon().pixmap(SYMBOL_SIZE, SYMBOL_SIZE))

    def _build_link_row(self) -> QWidget:
        box = QWidget(self)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)

        self.link_edit = QLineEdit(box)
        self.link_edit.setPlaceholderText(
            "Ссылка на Pinterest или видео YouTube (можно перетащить из браузера)"
        )
        self.link_edit.setClearButtonEnabled(True)
        layout.addWidget(self.link_edit)

        buttons = QHBoxLayout()
        self.download_button = QPushButton("Скачать", box)
        self.download_button.setObjectName("primaryButton")
        buttons.addWidget(self.download_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return box

    def _build_destination_row(self) -> QWidget:
        box = QWidget(self)
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Папка сохранения:", box))

        self.destination_edit = QLineEdit(box)
        self.destination_edit.setReadOnly(True)
        layout.addWidget(self.destination_edit, 1)

        self.choose_destination_button = QPushButton("Выбрать папку", box)
        layout.addWidget(self.choose_destination_button)
        return box

    def _build_format_row(self) -> QWidget:
        box = QWidget(self)
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)

        self.format_selector = FormatSelector(box)
        layout.addWidget(self.format_selector)
        layout.addStretch(1)
        return box

    @property
    def link_text(self) -> str:
        """Текст в поле ссылки."""
        return self.link_edit.text()

    @link_text.setter
    def link_text(self, value: str) -> None:
        self.link_edit.setText(value)

    @property
    def destination_text(self) -> str:
        """Текущая папка сохранения."""
        return self.destination_edit.text()
