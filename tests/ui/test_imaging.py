"""Перевод картинки в другой формат средствами Qt.

Требования, которые закрывают эти проверки:

* R3 — требования: картинка сохраняется в выбранном формате;
* R4 — бизнес-правила: качество JPEG и WebP, прозрачность заливается белым,
  мусорный файл картинкой не считается.
"""

from __future__ import annotations

import base64
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from snipnest.ui.imaging import convert_image

#: Картинка 1×1 в PNG — настоящий файл, а не заглушка.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _write_png(path: Path) -> Path:
    """Положить настоящую картинку PNG по пути."""
    path.write_bytes(PNG_BYTES)
    return path


def _write_opaque_png(path: Path) -> Path:
    """Положить непрозрачную картинку PNG по пути.

    Непрозрачная — чтобы сравнение с эталоном зависело только от качества,
    а не от того, как картинка ложится на фон.
    """
    image = QImage(4, 4, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.red)
    assert image.save(str(path), "PNG")
    return path


def test_png_переводится_в_jpeg(tmp_path: Path) -> None:
    """R3: картинка сохраняется в выбранном формате."""
    source = _write_png(tmp_path / "photo.png")

    result = convert_image(source, "jpg")

    assert result is not None
    assert result.suffix == ".jpg"
    assert result.is_file()
    image = QImage(str(result))
    assert not image.isNull()
    assert image.size().width() == 1


def test_png_переводится_в_webp(tmp_path: Path) -> None:
    """R3: WebP — тоже доступный формат."""
    source = _write_png(tmp_path / "photo.png")

    result = convert_image(source, "webp")

    assert result is not None
    assert result.suffix == ".webp"
    assert QImage(str(result)).size().width() == 1


def test_картинка_уже_в_нужном_формате_остаётся_на_месте(tmp_path: Path) -> None:
    """R4: перекодировки нет — файл уже в том формате, в котором нужен."""
    source = _write_png(tmp_path / "photo.png")
    converted = convert_image(source, "png")

    assert converted == source
    assert list(tmp_path.iterdir()) == [source]


def test_мусорный_файл_не_переводится(tmp_path: Path) -> None:
    """R4: не картинка — не картинка: перевод не удаётся."""
    source = tmp_path / "photo.png"
    source.write_bytes(b"not an image at all")

    assert convert_image(source, "jpg") is None


def test_прозрачность_заливается_белым(tmp_path: Path) -> None:
    """R4: прозрачные места в JPEG не должны становиться чёрными."""
    source = tmp_path / "logo.png"
    image = QImage(2, 2, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    assert image.save(str(source), "PNG")

    result = convert_image(source, "jpg")

    assert result is not None
    pixel = QImage(str(result)).pixelColor(0, 0)
    assert pixel.red() > 200
    assert pixel.green() > 200
    assert pixel.blue() > 200


def test_качество_jpeg_соответствует_договорённому(tmp_path: Path) -> None:
    """R4: JPEG пишется с качеством 90."""
    source = _write_opaque_png(tmp_path / "photo.png")
    expected = tmp_path / "expected.jpg"
    image = QImage(str(source))
    assert image.save(str(expected), "JPEG", 90)

    result = convert_image(source, "jpg")

    assert result is not None
    assert result.read_bytes() == expected.read_bytes()


def test_качество_webp_соответствует_договорённому(tmp_path: Path) -> None:
    """R4: WebP пишется с качеством 90."""
    source = _write_opaque_png(tmp_path / "photo.png")
    expected = tmp_path / "expected.webp"
    image = QImage(str(source))
    assert image.save(str(expected), "WEBP", 90)

    result = convert_image(source, "webp")

    assert result is not None
    assert result.read_bytes() == expected.read_bytes()
