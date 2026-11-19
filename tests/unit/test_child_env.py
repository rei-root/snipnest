"""Регрессия: окружение запуска gallery-dl не должно ломать его интерпретатор.

Многие установки gallery-dl — bash-обёртки вида
``exec python3 .../gallery_dl/__main__.py``. Если каталог venv приложения
первый в ``PATH``, то ``python3`` указывает на venv без ``requests``, и
бинарник падает с ``ModuleNotFoundError`` вместо скачивания.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from snipnest.downloader import build_child_env


def test_каталог_venv_приложения_не_попадает_в_path() -> None:
    env = build_child_env()
    parts = env.get("PATH", "").split(os.pathsep)
    venv_dir = os.environ.get("VIRTUAL_ENV")
    if venv_dir:
        assert os.path.join(venv_dir, "bin") not in parts


def test_каталог_интерпретатора_приложения_не_попадает_в_path() -> None:
    env = build_child_env()
    parts = [os.path.realpath(part) for part in env.get("PATH", "").split(os.pathsep) if part]
    assert os.path.realpath(sys.prefix) not in parts


def test_системные_каталоги_остаются_в_path() -> None:
    """gallery-dl должен по-прежнему находиться и запускаться."""
    env = build_child_env()
    parts = env.get("PATH", "").split(os.pathsep)
    assert "/usr/bin" in parts


def test_системный_каталог_остаётся_даже_если_интерпретатор_системный(monkeypatch) -> None:
    """venv на системном Python: каталог ``/usr/bin`` ребёнку нужен.

    ``realpath`` интерпретатора в таком venv указывает на ``/usr/bin``;
    если его выбрасывать, gallery-dl из ``/usr/bin`` перестаёт находиться.
    """
    monkeypatch.setattr(sys, "executable", "/usr/bin/python3")
    monkeypatch.setattr(sys, "prefix", "/usr")
    monkeypatch.setattr(sys, "base_prefix", "/usr")

    env = build_child_env()

    assert "/usr/bin" in env.get("PATH", "").split(os.pathsep)


def test_pythonhome_и_pythonpath_сброшены() -> None:
    env = build_child_env()
    assert "PYTHONHOME" not in env
    assert "PYTHONPATH" not in env


def test_прочие_переменные_окружения_сохраняются() -> None:
    env = build_child_env()
    for name in ("HOME", "LANG", "LC_ALL", "XDG_RUNTIME_DIR"):
        if name in os.environ:
            assert env.get(name) == os.environ.get(name)


def test_собственный_каталог_не_пропадает_совсем() -> None:
    """Системный Python должен остаться доступен ребёнку."""
    env = build_child_env()
    parts = env.get("PATH", "").split(os.pathsep)
    assert any(Path(part).name == "bin" for part in parts if part)
