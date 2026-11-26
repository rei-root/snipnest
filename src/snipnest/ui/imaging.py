"""Перевод картинки в другой формат средствами Qt.

Модуль знает про Qt: перекодировкой занимается именно он. Ядро загрузки о Qt
не знает — оно получает готовую функцию подставкой.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

__all__ = ["IMAGE_QUALITY", "convert_image"]

#: Качество JPEG и WebP: 90 — без заметной потери и в разы меньше веса.
IMAGE_QUALITY = 90

#: Форматы, которыми приложение умеет писать. Ключ — расширение файла.
_FORMAT_NAMES = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
}


def _on_white(image: QImage) -> QImage:
    """Положить картинку на белый фон.

    Прозрачные места при записи в JPEG иначе стали бы чёрными.
    """
    background = QImage(image.size(), QImage.Format.Format_RGB32)
    background.fill(Qt.GlobalColor.white)
    painter = QPainter(background)
    painter.drawImage(0, 0, image)
    painter.end()
    return background


def convert_image(source: Path, extension: str) -> Path | None:
    """Перевести картинку в другой формат.

    Вернуть путь к готовому файлу или None, если перевести не вышло.
    Если исходный файл уже в нужном формате, вернуть его же.
    """
    name = _FORMAT_NAMES.get(extension.lower())
    if name is None:
        return None
    target = source.with_suffix("." + extension.lower())
    if target == source:
        return source
    image = QImage(str(source))
    if image.isNull():
        return None
    if name == "JPEG":
        image = _on_white(image)
    # Формат Qt выбирает сам — по расширению файла.
    if not image.save(str(target), None, IMAGE_QUALITY):
        return None
    return target
