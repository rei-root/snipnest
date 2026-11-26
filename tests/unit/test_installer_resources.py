"""Ресурсы установщика: ярлык, иконка и сведения о сборке."""

from __future__ import annotations

import json
from pathlib import Path

import snipnest
from snipnest.installer import resources


def test_ярлык_читается() -> None:
    text = resources.desktop_file_text()

    assert "[Desktop Entry]" in text
    assert "Name=Snipnest" in text


def test_иконка_читается() -> None:
    data = resources.icon_bytes()

    assert data
    assert data[:4] == b"\x89PNG"


def test_размеры_иконок_на_месте() -> None:
    assert 256 in resources.icon_sizes()


def test_сведения_о_сборке_читаются_из_файла(tmp_path, monkeypatch) -> None:
    path = tmp_path / "build-info.json"
    path.write_text(
        json.dumps({"version": snipnest.__version__, "min_glibc": "2.38"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("SNIPNEST_BUILD_INFO", str(path))
    resources.build_info.cache_clear()

    info = resources.build_info()

    assert info["version"] == snipnest.__version__
    assert info["min_glibc"] == "2.38"


def test_без_сведений_о_сборке_пусто(monkeypatch) -> None:
    monkeypatch.setenv("SNIPNEST_BUILD_INFO", str(Path("/нет-такого-файла")))
    resources.build_info.cache_clear()

    assert resources.build_info() == {}
