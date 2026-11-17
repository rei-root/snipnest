"""Общие настройки тестов.

PySide6 требует графической сессии. В CI её нет, поэтому при отсутствии
DISPLAY и WAYLAND_DISPLAY тесты идут на offscreen-платформе.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
