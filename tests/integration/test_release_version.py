"""Релиз: имена артефактов и сведения о сборке берутся из версии пакета.

Версия живёт в одном месте — в пакете. Всё остальное (имя пакета, имя
образа, адрес релиза, сведения внутри установщика) читает её оттуда, поэтому
следующий релиз не требует правок во многих местах.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import snipnest

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "packaging" / "common.sh"
BUILD_INSTALLER = ROOT / "packaging" / "build-installer.sh"


def _helper(name: str) -> str:
    """Вызвать функцию сборки и вернуть её вывод."""
    completed = subprocess.run(
        ["bash", "-c", f'source "{COMMON}"; {name}'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def test_версия_в_имени_пакета() -> None:
    assert snipnest.__version__ in _helper("deb_name")


def test_версия_в_имени_образа() -> None:
    assert snipnest.__version__ in _helper("appimage_name")


def test_адрес_релиза_ведёт_на_тег_версии() -> None:
    assert _helper("release_url").endswith(f"/v{snipnest.__version__}")


def test_сборщик_установщика_кладёт_версию_и_адрес_релиза() -> None:
    """Внутри установщика должны быть версия и адрес релиза этой версии."""
    body = BUILD_INSTALLER.read_text(encoding="utf-8")

    assert '"version": "$VERSION"' in body
    assert '"release_url": "$(release_url)"' in body
