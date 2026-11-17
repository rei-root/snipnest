"""Интеграционные тесты: разбор вывода настоящего gallery-dl."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from gallary_downloader.downloader import GalleryDlRunner, parse_output_line

pytestmark = pytest.mark.skipif(
    shutil.which("gallery-dl") is None,
    reason="gallery-dl не установлен в системе",
)


def test_настоящий_бинарник_печатает_версию() -> None:
    result = subprocess.run(
        ["gallery-dl", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip()


def test_настоящий_бинарник_на_несуществующем_бинарнике_даёт_ошибку(tmp_path) -> None:
    runner = GalleryDlRunner(destination=tmp_path)
    result = runner.run("https://pin.it/THIS_LINK_DOES_NOT_EXIST_12345")
    assert result.returncode != 0
    assert result.errors >= 1


def test_настоящий_бинарник_на_пустой_ссылке_не_скачивает(tmp_path) -> None:
    runner = GalleryDlRunner(destination=tmp_path)
    result = runner.run("", simulate=True)
    assert result.returncode != 0


def test_разбор_реальной_строки_вывода() -> None:
    event = parse_output_line("# pinterest/pin_1.jpg\n")
    assert event.path == "pinterest/pin_1.jpg"


def test_счётчик_файлов_на_несуществующей_ссылке_падает(tmp_path) -> None:
    """На битой ссылке gallery-dl возвращает ненулевой код, а не исключение."""
    runner = GalleryDlRunner(destination=tmp_path)
    result = runner.run("https://pin.it/THIS_LINK_DOES_NOT_EXIST_12345", simulate=True)
    assert result.returncode != 0
    assert result.downloaded == 0


def test_путь_назначения_используется(tmp_path) -> None:
    runner = GalleryDlRunner(destination=tmp_path)
    command = runner.build_command("https://pin.it/abc")
    assert str(Path(tmp_path)) in command
