"""Установщик Snipnest: план установки на разных семействах дистрибутивов.

Установщик — shell-скрипт, поэтому проверяем его как чёрный ящик: собираем
и запускаем с подставленным /etc/os-release и смотрим на план.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "packaging" / "build-installer.sh"
INSTALLER_NAME = "snipnest-installer-linux-amd64.bin"


def _build(tmp_path: Path) -> Path:
    """Собрать установщик во временный каталог."""
    dist = tmp_path / "dist"
    env = {**os.environ, "DIST": str(dist)}
    completed = subprocess.run(
        ["bash", str(BUILD_SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return dist / INSTALLER_NAME


def _os_release(path: Path, distro_id: str, id_like: str = "") -> Path:
    """Написать файл os-release заданного дистрибутива."""
    path.write_text(f'ID={distro_id}\nID_LIKE="{id_like}"\n', encoding="utf-8")
    return path


def _run(installer: Path, os_release: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Запустить установщик с подставленным os-release."""
    env = {**os.environ, "SNIPNEST_OS_RELEASE": str(os_release)}
    return subprocess.run(
        [str(installer), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_установщик_собирается_одним_исполняемым_файлом(tmp_path) -> None:
    installer = _build(tmp_path)

    assert installer.is_file()
    assert os.access(installer, os.X_OK)
    assert installer.read_text(encoding="utf-8").startswith("#!/bin/sh")


def test_в_установщике_нет_приложения(tmp_path) -> None:
    """Внутри установщика нет приложения: только скрипт установки."""
    body = _build(tmp_path).read_text(encoding="utf-8")

    assert "_internal" not in body
    assert "PySide6" not in body
    assert "\x7fELF" not in body


def test_на_debian_ставится_пакет(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "debian")

    result = _run(installer, release, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "apt-get install" in result.stdout
    assert ".deb" in result.stdout


def test_на_arch_образ_кладётся_в_opt(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "/opt/snipnest" in result.stdout
    assert "/usr/local/bin/snipnest" in result.stdout


def test_на_rhel_тот_же_план_образа(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "fedora", "rhel centos")

    result = _run(installer, release, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "/opt/snipnest" in result.stdout


def test_на_неизвестной_системе_берётся_образ(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "что-то-неизвестное")

    result = _run(installer, release, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "/opt/snipnest" in result.stdout


def test_в_режиме_пользователя_всё_идёт_в_домашний_каталог(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--dry-run", "--user")

    assert result.returncode == 0, result.stderr
    assert ".local/opt/snipnest" in result.stdout
    assert "каталог: /opt/snipnest" not in result.stdout


def test_план_содержит_имя_образа_с_платформой_и_архитектурой(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--dry-run")

    assert "linux-glibc-" in result.stdout
    assert "x86_64.AppImage" in result.stdout


def test_справка_печатается(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--help")

    assert result.returncode == 0
    assert "--user" in result.stdout
    assert "--dry-run" in result.stdout


def test_версия_печатается(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--version")

    assert result.returncode == 0
    assert "snipnest-installer" in result.stdout


def test_неизвестный_ключ_останавливает_установщик(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--несуществующий")

    assert result.returncode != 0
    assert "неизвестный ключ" in result.stderr
