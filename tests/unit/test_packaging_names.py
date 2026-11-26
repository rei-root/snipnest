"""Имена артефактов: платформа, glibc и архитектура в имени образа."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import snipnest

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "packaging" / "common.sh"


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


def test_имя_образа_содержит_платформу_glibc_и_архитектуру() -> None:
    name = _helper("appimage_name")

    assert re.fullmatch(r"snipnest-\d+\.\d+\.\d+-linux-glibc-\d+\.\d+-x86_64\.AppImage", name)


def test_имя_пакета_deb_не_меняется() -> None:
    assert re.fullmatch(r"snipnest_\d+\.\d+\.\d+_amd64\.deb", _helper("deb_name"))


def test_версия_берётся_из_пакета() -> None:
    assert _helper("app_version") == snipnest.__version__


def test_базовая_glibc_указана_одним_числом() -> None:
    assert re.fullmatch(r"\d+\.\d+", _helper("abi_glibc"))


def test_адрес_релиза_ведёт_на_тег_версии() -> None:
    assert _helper("release_url").endswith(f"/v{snipnest.__version__}")
