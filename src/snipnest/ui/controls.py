"""Верхняя часть окна: поле ссылки, папка сохранения, кнопки.

Отдельный виджет, чтобы главное окно не разрасталось.
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

__all__ = ["TopControls"]


class TopControls(QWidget):
    """Поле ссылки, выбор папки сохранения и кнопки источника."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_link_row())
        layout.addWidget(self._build_destination_row())
        layout.addWidget(self._build_toolbar())

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

    def _build_toolbar(self) -> QWidget:
        box = QWidget(self)
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)

        self.token_button = QPushButton("Токен Pinterest", box)
        layout.addWidget(self.token_button)

        self.open_pinterest_button = QPushButton("Открыть Pinterest", box)
        layout.addWidget(self.open_pinterest_button)

        self.components_button = QPushButton("Компоненты…", box)
        layout.addWidget(self.components_button)

        self.gallery_dl_button = QPushButton("Путь к gallery-dl", box)
        layout.addWidget(self.gallery_dl_button)

        self.yt_dlp_button = QPushButton("Путь к yt-dlp", box)
        layout.addWidget(self.yt_dlp_button)

        self.cookies_button = QPushButton("Cookies YouTube", box)
        layout.addWidget(self.cookies_button)

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
