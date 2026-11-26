"""Графический установщик: сборка и протокол работника с правами.

Сборка установщика (PyInstaller) проверяется оракулом bin/check-installer-gui.sh:
она долгая, а тесты должны быть быстрыми. Здесь — то, что проверяется
быстро: точка входа и протокол, которым окно зовёт работника с правами.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "packaging" / "build-installer.sh"
ENTRY = ROOT / "packaging" / "installer_entry.py"
SPEC = ROOT / "packaging" / "snipnest.spec"


def _request(tmp_path: Path) -> Path:
    """Файл запроса на установку в тестовый каталог."""
    image = tmp_path / "snipnest.AppImage"
    image.write_text("подделка образа\n", encoding="utf-8")
    path = tmp_path / "request.json"
    path.write_text(
        json.dumps(
            {
                "image_path": str(image),
                "image_name": "snipnest.AppImage",
                "app_dir": str(tmp_path / "opt"),
                "bin_dir": str(tmp_path / "bin"),
                "desktop_dir": str(tmp_path / "share"),
                "icons_dir": str(tmp_path / "icons"),
                "packages": [],
                "package_command": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_есть_точка_входа_установщика() -> None:
    assert ENTRY.is_file()
    assert "snipnest.installer" in ENTRY.read_text(encoding="utf-8")


def test_сборщик_собирает_установщик_через_pyinstaller() -> None:
    body = BUILD_SCRIPT.read_text(encoding="utf-8")

    assert "SNIPNEST_ENTRY" in body
    assert "installer_entry.py" in body
    assert "pyinstaller" in body


def test_спека_умеет_собирать_установщик() -> None:
    body = SPEC.read_text(encoding="utf-8")

    assert "SNIPNEST_ENTRY" in body
    assert "SNIPNEST_NAME" in body
    assert "SNIPNEST_INSTALLER" in body


def test_старого_shell_установщика_больше_нет() -> None:
    assert not (ROOT / "packaging" / "installer" / "snipnest-installer.sh").exists()


def test_работник_с_правами_выполняет_установку(tmp_path) -> None:
    """Окно зовёт работника ключом --root-worker — он ставит файлы."""
    request = _request(tmp_path)

    completed = subprocess.run(
        [sys.executable, "-m", "snipnest.installer", "--root-worker", str(request)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["ok"]
    assert (tmp_path / "opt" / "snipnest.AppImage").is_file()
    assert (tmp_path / "bin" / "snipnest").is_file()
    assert (tmp_path / "share" / "snipnest.desktop").is_file()


def test_работник_без_запроса_не_падает(tmp_path) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "snipnest.installer", "--root-worker"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )

    assert completed.returncode != 0
    report = json.loads(completed.stdout)
    assert not report["ok"]
