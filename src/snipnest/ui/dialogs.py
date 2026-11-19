"""Диалоги: токен Pinterest, путь к бинарнику, источник cookies."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..cookies import detect_browser_sources, file_source

__all__ = [
    "TokenDialog",
    "CookieSourceDialog",
    "choose_directory",
    "choose_executable",
]


class TokenDialog(QDialog):
    """Ввод токена или cookie Pinterest.

    Пароль не вводится: пользователь вставляет готовый токен или cookie
    из браузера. Значение показывается скрытым.
    """

    def __init__(self, parent: QWidget | None = None, current: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Токен Pinterest")
        self.setModal(True)

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Вставьте токен или cookie Pinterest. "
            "Значение хранится в системном хранилище (keyring), "
            "пароль от аккаунта не нужен."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._field = QLineEdit(self)
        self._field.setEchoMode(QLineEdit.EchoMode.Password)
        self._field.setPlaceholderText("токен или cookie")
        self._field.setText(current)
        layout.addWidget(self._field)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def token(self) -> str:
        """Введённый токен (без пробелов по краям)."""
        return self._field.text().strip()


def choose_directory(parent: QWidget | None, current: str) -> str | None:
    """Выбрать папку сохранения. None, если владелец отказался."""
    selected = QFileDialog.getExistingDirectory(parent, "Папка сохранения", current)
    return selected or None


def choose_executable(
    parent: QWidget | None,
    current: str,
    title: str = "Путь к бинарнику",
) -> str | None:
    """Выбрать бинарник. None, если владелец отказался."""
    path, _ = QFileDialog.getOpenFileName(parent, title, current)
    return path or None


class CookieSourceDialog(QDialog):
    """Выбор источника cookies для YouTube.

    Источник один: либо браузер с профилем, либо файл cookies.txt.
    Приложение cookies не читает и не хранит — только указывает yt-dlp,
    откуда их взять.
    """

    #: Метка пункта «Файл cookies.txt» в списке.
    FILE_MARKER = "file"

    def __init__(
        self,
        parent: QWidget | None = None,
        browser: str = "",
        file: str = "",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cookies YouTube")
        self.setModal(True)

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Откуда yt-dlp взять cookies для YouTube. Без них YouTube "
            "просит подтвердить, что ты не бот, и не отдаёт ролик. "
            "Приложение cookies не читает и не сохраняет."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._combo = QComboBox(self)
        self._combo.addItem("Не использовать", ("", ""))
        for source in detect_browser_sources():
            self._combo.addItem(source.label, (source.browser, ""))
        self._combo.addItem("Файл cookies.txt", (self.FILE_MARKER, ""))
        layout.addWidget(self._combo)

        self._file_edit = QLineEdit(self)
        self._file_edit.setReadOnly(True)
        self._file_edit.setPlaceholderText("Файл cookies.txt в формате Netscape")
        self._file_button = QPushButton("Выбрать файл…", self)
        file_row = QHBoxLayout()
        file_row.addWidget(self._file_edit, 1)
        file_row.addWidget(self._file_button)
        layout.addLayout(file_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._combo.currentIndexChanged.connect(self._on_source_changed)
        self._file_button.clicked.connect(self._on_choose_file)

        if browser:
            self.select_browser(browser)
        elif file:
            self.select_file(file)
        self._on_source_changed()

    # -- выбор ---------------------------------------------------------------

    def item_count(self) -> int:
        """Сколько пунктов в списке источников."""
        return self._combo.count()

    def itemText(self, index: int) -> str:
        """Название пункта списка."""
        return self._combo.itemText(index)

    def select_browser(self, browser: str) -> None:
        """Выбрать браузер с профилем."""
        for index in range(self._combo.count()):
            data = self._combo.itemData(index)
            if isinstance(data, tuple) and data and data[0] == browser:
                self._combo.setCurrentIndex(index)
                return

    def select_file(self, path: str) -> None:
        """Выбрать файл cookies.txt."""
        for index in range(self._combo.count()):
            data = self._combo.itemData(index)
            if isinstance(data, tuple) and data and data[0] == self.FILE_MARKER:
                self._combo.setCurrentIndex(index)
                break
        self._file_edit.setText(path)
        self._on_source_changed()

    def selection(self) -> tuple[str, str]:
        """Выбранный источник: браузер с профилем и путь к файлу."""
        data = self._combo.currentData()
        browser = data[0] if isinstance(data, tuple) and data else ""
        if browser == self.FILE_MARKER:
            return ("", self._file_edit.text().strip())
        return (browser, "")

    # -- внутреннее ----------------------------------------------------------

    def _on_source_changed(self) -> None:
        """Файл cookies выбирают только тогда, когда выбран именно он."""
        data = self._combo.currentData()
        is_file = isinstance(data, tuple) and bool(data) and data[0] == self.FILE_MARKER
        self._file_button.setEnabled(is_file)
        self._file_edit.setEnabled(is_file)

    def _on_choose_file(self) -> None:
        """Выбрать файл cookies.txt."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Файл cookies.txt",
            self._file_edit.text(),
            "Текстовые файлы (*.txt);;Все файлы (*)",
        )
        if path:
            self._file_edit.setText(path)
            index = self._combo.currentIndex()
            self._combo.setItemText(index, file_source(path).label)
