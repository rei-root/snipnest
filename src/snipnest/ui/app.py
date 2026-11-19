"""Запуск приложения: QApplication, имя приложения, главное окно."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ..settings import Settings
from .window import MainWindow

__all__ = ["APPLICATION_NAME", "make_application", "run"]

APPLICATION_NAME = "Snipnest"
DESKTOP_FILE_NAME = "snipnest"


def make_application(settings: Settings | None = None) -> tuple[QApplication, MainWindow]:
    """Создать QApplication и главное окно.

    Имя приложения выставляется всегда: QApplication мог достаться
    снаружи (тесты, встраивание), а имя всё равно должно быть нашим.
    """
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    app.setApplicationName(APPLICATION_NAME)
    app.setApplicationDisplayName(APPLICATION_NAME)
    app.setDesktopFileName(DESKTOP_FILE_NAME)
    window = MainWindow(settings)
    # Висящий поток QThread роняет приложение при выходе: потоки
    # останавливаются до того, как Qt начнёт разрушать объекты.
    app.aboutToQuit.connect(window.shutdown)
    return app, window


def run(settings: Settings | None = None) -> int:
    """Запустить приложение. Возвращает код завершения."""
    app, window = make_application(settings)
    window.show_component_wizard_if_needed()
    window.show()
    return app.exec()
