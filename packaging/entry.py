"""Точка входа сборки PyInstaller.

Скрипт запускается как отдельный файл, поэтому пакет `snipnest` должен
импортироваться абсолютным импортом: относительные импорты внутри пакета
не работают, когда файл запускается вне пакета.
"""

from __future__ import annotations

import sys

from snipnest.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
