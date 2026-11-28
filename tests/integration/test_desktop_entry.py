"""Проверки ярлыка, установщика, иконок и метаданных пакета.

Это проверки класса B: читаются файлы репозитория и состояние git и
сравниваются между собой — поведение проверяется без запуска приложения.

Требования, которые закрывают эти проверки:

* R3 — функциональные требования: ярлык и установщик ставят иконку
  приложения, собранную из нового логотипа;
* R4 — бизнес-правила: иконка одна — векторная, размеры PNG генерируются из
  неё, установка иконок не зависит от ImageMagick.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from snipnest.branding import ICON_SIZES
from snipnest.installer.worker import InstallRequest, install_icons

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "packaging" / "snipnest.desktop"
INSTALLER = ROOT / "packaging" / "install-desktop-entry.sh"
COMMON = ROOT / "packaging" / "common.sh"
PYPROJECT = ROOT / "pyproject.toml"
LOGO = ROOT / "logo" / "snipnest.svg"


def _desktop() -> str:
    return DESKTOP.read_text(encoding="utf-8")


def _install_request(tmp_path: Path) -> InstallRequest:
    """Запрос на установку в отдельный каталог."""
    return InstallRequest(
        image_path="",
        image_name="snipnest",
        app_dir=str(tmp_path),
        bin_dir=str(tmp_path),
        desktop_dir=str(tmp_path),
        icons_dir=str(tmp_path / "icons"),
    )


def test_ярлык_называет_приложение_с_большой_буквы() -> None:
    assert "Name=Snipnest" in _desktop()


def test_ярлык_запускает_команду_из_метаданных_пакета() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")
    entry = re.search(r"^snipnest\s*=\s*\"([^\"]+)\"", pyproject, re.MULTILINE)
    assert entry is not None, "в pyproject.toml нет точки входа snipnest"
    assert entry.group(1).endswith(":main")
    assert "Exec=snipnest" in _desktop()


def test_имя_иконки_совпадает_с_именем_команды() -> None:
    desktop = _desktop()
    assert "Icon=snipnest" in desktop
    assert "StartupWMClass=snipnest" in desktop


def test_установщик_ставит_ярлык_и_иконку_под_новым_именем() -> None:
    installer = INSTALLER.read_text(encoding="utf-8")
    assert "snipnest.desktop" in installer
    assert "snipnest.svg" in installer


def test_логотип_на_месте() -> None:
    assert LOGO.is_file()
    assert LOGO.read_text(encoding="utf-8").lstrip().startswith("<svg")


def test_установщик_ставит_иконки_из_svg(tmp_path: Path) -> None:
    """Установщик кладёт иконки всех стандартных размеров, собранные из SVG."""
    result = install_icons(_install_request(tmp_path))
    assert result.ok, result.message

    for size in ICON_SIZES:
        target = tmp_path / "icons" / f"{size}x{size}" / "apps" / "snipnest.png"
        assert target.is_file(), f"нет иконки {size}×{size}"
        assert target.read_bytes().startswith(b"\x89PNG")


def test_векторная_иконка_ставится_в_scalable(tmp_path: Path) -> None:
    """Векторная иконка кладётся в scalable/apps — её находит тема иконок."""
    result = install_icons(_install_request(tmp_path))
    assert result.ok, result.message

    target = tmp_path / "icons" / "scalable" / "apps" / "snipnest.svg"
    assert target.is_file()
    assert "<svg" in target.read_text(encoding="utf-8")


def test_установка_иконок_не_нужен_imagemagick() -> None:
    """Размеры иконок режутся средствами Qt — внешняя программа не нужна."""
    for script in (INSTALLER, COMMON):
        text = script.read_text(encoding="utf-8")
        assert "magick" not in text, f"{script.name} зовёт ImageMagick"
        assert "convert" not in text, f"{script.name} зовёт ImageMagick"


def test_удалённый_репозиторий_новый() -> None:
    """Репозиторий проекта переведён на snipnest.

    Адрес бывает с ``.git`` и без: ``actions/checkout`` в CI добавляет
    remote как ``https://github.com/<владелец>/<репозиторий>`` — без
    расширения. Проверяем имя репозитория, а не написание адреса.
    """
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert url.rstrip("/").removesuffix(".git").endswith("snipnest")
