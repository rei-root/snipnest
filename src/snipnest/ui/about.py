"""Окно «О программе»: символ приложения, название и версия."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from .. import __version__
from ..branding import symbolic_icon

__all__ = ["AboutDialog"]

#: Размер символа в окне «О программе».
SYMBOL_SIZE = 64


class AboutDialog(QDialog):
    """Короткое окно о приложении."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setModal(True)

        layout = QVBoxLayout(self)

        self.icon_label = QLabel(self)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setPixmap(symbolic_icon().pixmap(SYMBOL_SIZE, SYMBOL_SIZE))
        layout.addWidget(self.icon_label)

        self.name_label = QLabel("Snipnest", self)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.name_label.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 3)
        self.name_label.setFont(font)
        layout.addWidget(self.name_label)

        self.version_label = QLabel(f"Версия {__version__}", self)
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.version_label)

        self.description_label = QLabel(
            "Загрузчик картинок и видео: скачивание из Pinterest и видео с YouTube.",
            self,
        )
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setText("Закрыть")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
