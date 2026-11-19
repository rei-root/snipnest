"""Точка входа: ``python -m snipnest`` и ``snipnest``."""

from __future__ import annotations

import sys

from . import __version__
from .migration import migrate_legacy_data
from .settings import CONFIG_DIR, KEYRING_SERVICE
from .ui.app import run

__all__ = ["main"]


def main() -> int:
    """Запустить графическое приложение. Возвращает код завершения."""
    if "--version" in sys.argv[1:]:
        sys.stdout.write(f"snipnest {__version__}\n")
        return 0
    migrate_legacy_data(CONFIG_DIR, KEYRING_SERVICE)
    return run()


if __name__ == "__main__":
    sys.exit(main())
