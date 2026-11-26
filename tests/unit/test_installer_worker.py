"""Установка с правами: куда что кладётся и как ставятся пакеты."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from snipnest.installer import worker
from snipnest.installer.worker import InstallRequest, read_request


def _request(tmp_path: Path, packages: tuple[str, ...] = (), command: tuple[str, ...] = ()):
    """Запрос на установку в тестовый каталог."""
    image = tmp_path / "snipnest.AppImage"
    image.write_text("подделка образа\n", encoding="utf-8")
    return InstallRequest(
        image_path=str(image),
        image_name="snipnest.AppImage",
        app_dir=str(tmp_path / "opt"),
        bin_dir=str(tmp_path / "bin"),
        desktop_dir=str(tmp_path / "share"),
        icons_dir=str(tmp_path / "icons"),
        packages=packages,
        package_command=command,
    )


def _mode(path: Path) -> int:
    """Права файла."""
    return stat.S_IMODE(path.stat().st_mode)


def test_образ_кладётся_и_становится_исполняемым(tmp_path) -> None:
    report = worker.run_install(_request(tmp_path))

    assert report.ok, report.steps
    image = tmp_path / "opt" / "snipnest.AppImage"
    assert image.is_file()
    assert os.access(image, os.X_OK)


def test_лаунчер_создаётся_и_указывает_на_образ(tmp_path) -> None:
    worker.run_install(_request(tmp_path))

    launcher = tmp_path / "bin" / "snipnest"
    assert launcher.is_file()
    assert os.access(launcher, os.X_OK)
    assert str(tmp_path / "opt" / "snipnest.AppImage") in launcher.read_text(encoding="utf-8")


def test_ярлык_указывает_на_лаунчер(tmp_path) -> None:
    worker.run_install(_request(tmp_path))

    desktop = tmp_path / "share" / "snipnest.desktop"
    assert desktop.is_file()
    assert f"Exec={tmp_path / 'bin' / 'snipnest'}" in desktop.read_text(encoding="utf-8")


def test_иконки_кладутся_в_стандартные_размеры(tmp_path) -> None:
    worker.run_install(_request(tmp_path))

    icon = tmp_path / "icons" / "256x256" / "apps" / "snipnest.png"
    assert icon.is_file()
    assert icon.read_bytes()


def test_без_образа_установка_не_проходит(tmp_path) -> None:
    request = InstallRequest(
        image_path=str(tmp_path / "нет-такого.AppImage"),
        image_name="snipnest.AppImage",
        app_dir=str(tmp_path / "opt"),
        bin_dir=str(tmp_path / "bin"),
        desktop_dir=str(tmp_path / "share"),
        icons_dir=str(tmp_path / "icons"),
    )

    report = worker.run_install(request)

    assert not report.ok
    assert any(not step.ok for step in report.steps)


def test_пакеты_ставятся_своей_командой(tmp_path) -> None:
    bin_dir = tmp_path / "bin-tools"
    bin_dir.mkdir()
    log = tmp_path / "packages.log"
    fake = bin_dir / "apt-get"
    fake.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" >> "{log}"\n', encoding="utf-8")
    fake.chmod(0o755)
    request = _request(tmp_path, packages=("gallery-dl",), command=(str(fake), "install", "-y"))

    report = worker.run_install(request)

    assert report.ok, report.steps
    assert "gallery-dl" in log.read_text(encoding="utf-8")


def test_отказ_пакетного_менеджера_виден_в_отчёте(tmp_path) -> None:
    bin_dir = tmp_path / "bin-tools"
    bin_dir.mkdir()
    fake = bin_dir / "apt-get"
    fake.write_text('#!/bin/sh\necho "нет такого пакета" >&2\nexit 100\n', encoding="utf-8")
    fake.chmod(0o755)
    request = _request(tmp_path, packages=("gallery-dl",), command=(str(fake), "install", "-y"))

    report = worker.run_install(request)

    assert not report.ok
    failed = [step for step in report.steps if not step.ok]
    assert failed
    assert "нет такого пакета" in failed[0].message


def test_запрос_и_отчёт_идут_через_json(tmp_path) -> None:
    request = _request(tmp_path, packages=("ffmpeg",), command=("apt-get", "install", "-y"))
    path = tmp_path / "request.json"
    path.write_text(request.to_json(), encoding="utf-8")

    restored = read_request(path)

    assert restored == request
    assert json.loads(request.to_json())["packages"] == ["ffmpeg"]
