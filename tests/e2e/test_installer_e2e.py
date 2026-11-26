"""Установщик с начала до конца: человек запускает его и получает приложение.

Проверяется домашний режим: всё ставится в каталог человека, система не
трогается.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "packaging" / "build-installer.sh"


def _installer(tmp_path: Path) -> Path:
    """Собрать установщик во временный каталог."""
    dist = tmp_path / "dist"
    completed = subprocess.run(
        ["bash", str(BUILD_SCRIPT)],
        cwd=ROOT,
        env={**os.environ, "DIST": str(dist)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return dist / "snipnest-installer-linux-amd64.bin"


def test_установка_в_домашний_каталог_создаёт_лаунчер(tmp_path) -> None:
    installer = _installer(tmp_path)
    release = tmp_path / "os-release"
    release.write_text('ID=arch\nID_LIKE=""\n', encoding="utf-8")
    image = tmp_path / "snipnest.AppImage"
    image.write_text("подделка образа\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()

    completed = subprocess.run(
        [str(installer), "--user", "--local", str(image), "--yes"],
        cwd=tmp_path,
        env={
            **os.environ,
            "HOME": str(home),
            "SNIPNEST_OS_RELEASE": str(release),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    launcher = home / ".local" / "bin" / "snipnest"
    assert launcher.is_file()
    assert os.access(launcher, os.X_OK)
    assert (home / ".local" / "opt" / "snipnest" / "snipnest.AppImage").is_file()


def test_установщик_не_трогает_систему_без_подтверждения(tmp_path) -> None:
    """Без согласия установщик ничего не ставит."""
    installer = _installer(tmp_path)
    release = tmp_path / "os-release"
    release.write_text('ID=arch\nID_LIKE=""\n', encoding="utf-8")
    image = tmp_path / "snipnest.AppImage"
    image.write_text("подделка образа\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()

    completed = subprocess.run(
        [str(installer), "--user", "--local", str(image)],
        cwd=tmp_path,
        env={
            **os.environ,
            "HOME": str(home),
            "SNIPNEST_OS_RELEASE": str(release),
        },
        input="n\n",
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert not (home / ".local" / "bin" / "snipnest").exists()


def test_установка_пакета_на_debian_проходит_целиком(tmp_path, fake_commands) -> None:
    """Человек запускает установщик на debian — и пакет ставится."""
    installer = _installer(tmp_path)
    release = tmp_path / "os-release"
    release.write_text('ID=debian\nID_LIKE=""\n', encoding="utf-8")
    package = tmp_path / "snipnest_0.2.0_amd64.deb"
    package.write_text("подделка пакета\n", encoding="utf-8")

    completed = subprocess.run(
        [str(installer), "--local", str(package), "--yes"],
        cwd=tmp_path,
        env={
            **fake_commands.env(),
            "SNIPNEST_OS_RELEASE": str(release),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "через apt-get" in completed.stdout
    arguments = fake_commands.arguments("apt-get")
    assert arguments[:2] == ["install", "-y"]
    assert Path(arguments[-1]).is_absolute()
    assert not arguments[-1].startswith(".//")
