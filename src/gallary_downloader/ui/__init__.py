"""Слой интерфейса на PySide6.

Модули:

- ``bridge`` — перенос событий из рабочего потока в GUI-поток;
- ``controller`` — очередь загрузок, потоки, отмена и повтор;
- ``controls`` — поле ссылки, папка сохранения, кнопки Pinterest;
- ``dialogs`` — диалоги (токен, выбор папки, путь к gallery-dl);
- ``dnd`` — приём ссылки, перетащенной из браузера;
- ``logarea`` — сворачиваемая область лога;
- ``models`` — строки списка загрузок;
- ``panel`` — список загрузок;
- ``presenter`` — правила показа события загрузки;
- ``settings_actions`` — операции над настройками;
- ``window`` — главное окно.
"""

from __future__ import annotations

__all__ = ["MainWindow", "main_window", "make_application", "run"]

from .app import make_application, run
from .window import MainWindow


def main_window() -> MainWindow:
    """Создать главное окно приложения.

    QApplication должен существовать: если его нет, окно создаётся
    вместе с ним.
    """
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])
    return MainWindow()
