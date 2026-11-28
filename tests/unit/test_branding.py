"""Брендинг приложения: логотип, символ и иконки.

Требования, которые закрывают эти проверки:

* R3 — функциональные требования: logo/snipnest.svg становится иконкой
  приложения, монохромный logo/snipnest-symbolic.svg используется внутри
  приложения;
* R4 — бизнес-правила: иконка приложения одна — цветной SVG, размеры PNG
  генерируются из неё, а не хранятся отдельными файлами.
"""

from __future__ import annotations

from pathlib import Path

from snipnest.branding import (
    APP_LOGO_NAME,
    ICON_SIZES,
    SYMBOL_LOGO_NAME,
    app_icon,
    app_logo_path,
    logo_dir,
    render_png,
    symbol_logo_path,
    symbolic_icon,
)


def test_логотип_и_символ_приложения_на_месте() -> None:
    """Логотип и символ лежат в каталоге logo/ и читаются как SVG."""
    assert logo_dir().is_dir()
    assert app_logo_path().name == APP_LOGO_NAME
    assert app_logo_path().is_file()
    assert symbol_logo_path().name == SYMBOL_LOGO_NAME
    assert symbol_logo_path().is_file()
    assert app_logo_path().read_text(encoding="utf-8").lstrip().startswith("<svg")
    assert symbol_logo_path().read_text(encoding="utf-8").lstrip().startswith("<svg")


def test_иконка_приложения_рендерится_из_svg() -> None:
    """Иконка приложения рисуется из SVG сама, без растрового файла."""
    icon = app_icon()
    assert not icon.isNull()
    pixmap = icon.pixmap(64, 64)
    assert not pixmap.isNull()
    assert pixmap.width() == 64

    symbol = symbolic_icon()
    assert not symbol.isNull()
    assert not symbol.pixmap(24, 24).isNull()


def test_размеры_иконок_стандартные() -> None:
    """Темы иконок ждут стандартные размеры, а не один произвольный."""
    assert ICON_SIZES == (16, 24, 32, 48, 64, 128, 256, 512)


def test_старый_растр_логотипа_не_хранится() -> None:
    """Один источник иконки — SVG: старый PNG в репозитории не остаётся."""
    assert not (logo_dir() / "snipnest.png").exists()


def test_размеры_рендерятся_из_логотипа() -> None:
    """PNG нужных размеров получаются из того же SVG."""
    data = render_png(48)
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(data) > 0