#!/usr/bin/env python3
"""Положить иконки приложения в каталог темы иконок.

Размеры PNG получаются из векторного логотипа средствами Qt — внешняя
программа не нужна.

    uv run python packaging/render-icons.py --out ~/.local/share/icons/hicolor
    uv run python packaging/render-icons.py --icon-file AppDir/.DirIcon
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snipnest.branding import ICON_SIZES, app_logo_path, render_png  # noqa: E402

#: Имя иконки в теме иконок.
ICON_NAME = "snipnest.png"

#: Имя векторной иконки в теме иконок.
VECTOR_ICON_NAME = "snipnest.svg"


def _write_theme(target: Path) -> None:
    """Разложить иконки по размерам и положить векторную рядом."""
    for size in ICON_SIZES:
        directory = target / f"{size}x{size}" / "apps"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ICON_NAME).write_bytes(render_png(size))

    scalable = target / "scalable" / "apps"
    scalable.mkdir(parents=True, exist_ok=True)
    (scalable / VECTOR_ICON_NAME).write_bytes(app_logo_path().read_bytes())


def main() -> int:
    """Разобрать аргументы и положить иконки."""
    parser = argparse.ArgumentParser(description="Иконки приложения из векторного логотипа")
    parser.add_argument("--out", type=Path, help="каталог темы иконок")
    parser.add_argument("--icon-file", type=Path, help="один PNG-файл (например .DirIcon)")
    parser.add_argument("--size", type=int, default=256, help="размер PNG-файла")
    args = parser.parse_args()

    if args.out is not None:
        _write_theme(args.out)
    if args.icon_file is not None:
        args.icon_file.parent.mkdir(parents=True, exist_ok=True)
        args.icon_file.write_bytes(render_png(args.size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())