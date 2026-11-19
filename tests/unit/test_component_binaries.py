"""Поиск внешних программ: каталоги установленных компонентов тоже в смотре."""

from __future__ import annotations

from pathlib import Path

from snipnest import binaries


def _make_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\necho 1.32.20\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_бинарник_из_каталога_компонентов_находится(monkeypatch, tmp_path) -> None:
    binary = _make_executable(tmp_path / "gallery-dl" / "bin" / "gallery-dl")
    monkeypatch.setattr(binaries, "component_bin_dirs", lambda: [binary.parent])

    found = binaries.find_gallery_dl()

    assert found == str(binary)


def test_компонент_важнее_программы_в_path(monkeypatch, tmp_path) -> None:
    """Установленный человеком компонент важнее того, что лежит в системе."""
    binary = _make_executable(tmp_path / "yt-dlp" / "bin" / "yt-dlp")
    monkeypatch.setattr(binaries, "component_bin_dirs", lambda: [binary.parent])

    found = binaries.find_yt_dlp()

    assert found == str(binary)


def test_явный_путь_важнее_каталога_компонентов(monkeypatch, tmp_path) -> None:
    binary = _make_executable(tmp_path / "gallery-dl" / "bin" / "gallery-dl")
    explicit = _make_executable(tmp_path / "свой" / "gallery-dl")
    monkeypatch.setattr(binaries, "component_bin_dirs", lambda: [binary.parent])

    found = binaries.find_gallery_dl(str(explicit))

    assert found == str(explicit)


def test_компонент_ищется_по_имени_и_без_каталога(monkeypatch, tmp_path) -> None:
    binary = _make_executable(tmp_path / "ffmpeg" / "bin" / "ffmpeg")
    monkeypatch.setattr(binaries, "component_bin_dirs", lambda: [binary.parent])

    assert binaries.find_executable("ffmpeg") == str(binary)
