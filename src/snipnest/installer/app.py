"""Запуск установщика: QApplication и окно.

Название приложения выставляется всегда: QApplication мог достаться
снаружи (тесты), а имя всё равно должно быть нашим.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from .plan import release_url
from .resources import build_info
from .window import InstallerContext, InstallerWindow, make_context

__all__ = ["APPLICATION_NAME", "context_from_build_info", "make_application", "run"]

APPLICATION_NAME = "Snipnest installer"
DESKTOP_FILE_NAME = "snipnest-installer"


def context_from_build_info() -> InstallerContext:
    """Собрать сведения о системе из данных сборки."""
    info = build_info()
    version = info.get("version", "0.0.0")
    min_glibc = info.get("min_glibc", "2.38")
    url = info.get("release_url") or release_url(version)
    return make_context(version, min_glibc, url)


def make_application(
    context: InstallerContext | None = None,
) -> tuple[QApplication, InstallerWindow]:
    """Создать QApplication и окно установщика."""
    app = QApplication.instance()
    if not isinstance(app, QApplication):
        app = QApplication([])
    app.setApplicationName(APPLICATION_NAME)
    app.setApplicationDisplayName(APPLICATION_NAME)
    app.setDesktopFileName(DESKTOP_FILE_NAME)
    window = InstallerWindow(context or context_from_build_info())
    return app, window


def run(context: InstallerContext | None = None) -> int:
    """Запустить установщик. Возвращает код завершения."""
    app, window = make_application(context)
    window.show()
    return app.exec()
