"""Точка входа: ``python -m gallary_downloader`` и ``gallary-downloader``."""

from __future__ import annotations

import sys

from .ui.app import run

__all__ = ["main"]


def main() -> int:
    """Запустить графическое приложение. Возвращает код завершения."""
    return run()


if __name__ == "__main__":
    sys.exit(main())
