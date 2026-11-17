"""Диалоги: токен Pinterest, путь к gallery-dl."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

__all__ = [
    "TokenDialog",
    "choose_directory",
    "choose_executable",
    "describe_missing_binary",
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


def choose_executable(parent: QWidget | None, current: str) -> str | None:
    """Выбрать бинарник gallery-dl. None, если владелец отказался."""
    path, _ = QFileDialog.getOpenFileName(parent, "Путь к gallery-dl", current)
    return path or None


def describe_missing_binary(binary_path: str) -> str:
    """Текст сообщения об отсутствии gallery-dl."""
    if binary_path:
        return f"gallery-dl не найден по пути {binary_path}. Укажите правильный путь в настройках."
    return "gallery-dl не найден в PATH. Установите его или укажите путь к бинарнику вручную."
