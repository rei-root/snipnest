"""Пути компонентов: каталог пользователя, каталог пакета, рантайм Python."""

from __future__ import annotations

from pathlib import Path

from snipnest.components import paths


def test_каталог_пользователя_в_домашней_папке(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    root = paths.user_components_root()

    assert root == tmp_path / ".local" / "share" / "snipnest" / "components"


def test_системный_каталог_в_usr_lib() -> None:
    assert paths.system_components_root() == Path("/usr/lib/snipnest/components")


def test_каталог_компонента_внутри_корня(tmp_path) -> None:
    folder = paths.component_dir("gallery-dl", root=tmp_path)

    assert folder == tmp_path / "gallery-dl"


def test_каталоги_запуска_собираются_из_компонентов(tmp_path) -> None:
    (tmp_path / "gallery-dl" / "bin").mkdir(parents=True)
    (tmp_path / "yt-dlp" / "bin").mkdir(parents=True)

    dirs = paths.component_bin_dirs(user_root=tmp_path, system_root=tmp_path / "system")

    assert tmp_path / "gallery-dl" / "bin" in dirs
    assert tmp_path / "yt-dlp" / "bin" in dirs


def test_пустой_каталог_не_даёт_каталогов_запуска(tmp_path) -> None:
    dirs = paths.component_bin_dirs(user_root=tmp_path / "user", system_root=tmp_path / "sys")

    assert dirs == []
