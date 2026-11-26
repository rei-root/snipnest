"""Сборщики релизных имён и адреса: версия пакета — единственный источник.

Требования, которые закрывают эти проверки:

* R3 — требования: имя пакета, имя образа и адрес релиза собраны из версии
  пакета, поэтому установщик качает именно эту версию.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from snipnest import __version__

REPO_ROOT = Path(__file__).parents[2]
COMMON = REPO_ROOT / "packaging" / "common.sh"


def _common(name: str) -> str:
    """Значение функции из packaging/common.sh."""
    result = subprocess.run(
        ["bash", "-c", f"source '{COMMON}'; {name}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_имя_пакета_собрано_из_версии() -> None:
    """R3: имя пакета содержит версию пакета."""
    assert __version__ in _common("deb_name")


def test_имя_образа_собрано_из_версии() -> None:
    """R3: имя образа содержит версию пакета."""
    assert __version__ in _common("appimage_name")


def test_адрес_релиза_ведёт_на_тег_версии() -> None:
    """R3: установщик качает релиз этой версии."""
    assert _common("release_url").endswith(f"/v{__version__}")
