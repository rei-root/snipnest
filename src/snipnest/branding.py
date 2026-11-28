"""Логотип, символ и иконки приложения.

Логотип один: ``logo/snipnest.svg``. Из него получаются и иконка окна, и PNG
размеров, которые ждёт тема иконок. Символ ``logo/snipnest-symbolic.svg``
одноцветный: цвет ему задаёт палитра темы, поэтому он перекрашивается сам и
одинаково читается в тёмной и в светлой теме.
"""

from __future__ import annotations

import sys
from functools import cache
from pathlib import Path

from PySide6.QtCore import QBuffer, QRect, QSize, Qt
from PySide6.QtGui import (
    QGuiApplication,
    QIcon,
    QIconEngine,
    QImage,
    QPainter,
    QPalette,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer

__all__ = [
    "APP_LOGO_NAME",
    "ICON_SIZES",
    "SYMBOL_LOGO_NAME",
    "app_icon",
    "app_logo_path",
    "logo_dir",
    "render_png",
    "symbol_logo_path",
    "symbolic_icon",
]

#: Имя файла логотипа приложения.
APP_LOGO_NAME = "snipnest.svg"

#: Имя файла символа приложения.
SYMBOL_LOGO_NAME = "snipnest-symbolic.svg"

#: Размеры иконок, которые ставит установщик и которые ищет тема иконок.
ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256, 512)


def _bundle_dir() -> Path | None:
    """Каталог собранного приложения (PyInstaller) или None."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else None


def logo_dir() -> Path:
    """Каталог с логотипом: в сборке — внутри образа, в исходниках — ``logo/``."""
    bundle = _bundle_dir()
    if bundle is not None:
        candidate = bundle / "logo"
        if candidate.is_dir():
            return candidate
        candidate = bundle
        if (candidate / APP_LOGO_NAME).is_file():
            return candidate
    return Path(__file__).resolve().parents[2] / "logo"


def app_logo_path() -> Path:
    """Путь к логотипу приложения."""
    return logo_dir() / APP_LOGO_NAME


def symbol_logo_path() -> Path:
    """Путь к символу приложения."""
    return logo_dir() / SYMBOL_LOGO_NAME


def _render(path: Path, width: int, height: int) -> QImage:
    """Отрисовать SVG в картинку заданного размера."""
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    QSvgRenderer(str(path)).render(painter, QRect(0, 0, width, height))
    painter.end()
    return image


@cache
def render_png(size: int) -> bytes:
    """PNG заданного размера, собранный из логотипа."""
    image = _render(app_logo_path(), size, size)
    buffer = QBuffer()
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    # Формат картинки PySide6 принимает строкой: байты формата он не берёт.
    image.save(buffer, "PNG")  # type: ignore[call-overload]
    buffer.close()
    return bytes(buffer.data().data())


def app_icon() -> QIcon:
    """Иконка приложения: цветной логотип."""
    return QIcon(str(app_logo_path()))


class _SymbolicEngine(QIconEngine):
    """Иконка, которая берёт цвет из палитры темы.

    Символ одноцветный, поэтому рисуется один раз и перекрашивается при
    смене темы: цвет берётся из роли «текст окна» активной палитры.
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        """Картинка иконки нужного размера."""
        width = max(1, size.width())
        height = max(1, size.height())
        image = _render(self._path, width, height)

        color = QGuiApplication.palette().color(QPalette.ColorRole.WindowText)
        painter = QPainter(image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(image.rect(), color)
        painter.end()
        return QPixmap.fromImage(image)

    def paint(
        self,
        painter: QPainter,
        rect: QRect,
        mode: QIcon.Mode,
        state: QIcon.State,
    ) -> None:
        """Нарисовать иконку в прямоугольнике."""
        painter.drawPixmap(rect, self.pixmap(rect.size(), mode, state))


def symbolic_icon() -> QIcon:
    """Символ приложения: одноцветный логотип, красящийся по теме."""
    return QIcon(_SymbolicEngine(symbol_logo_path()))
