"""Живые тесты: реальный gallery-dl ходит в сеть.

Тесты помечены маркером ``live`` и в оракул не входят: им нужны
установленный gallery-dl и доступ к Pinterest. Список ссылок берётся из
``links.txt`` в корне репозитория.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from gallary_downloader.downloader import GalleryDlRunner, find_gallery_dl
from gallary_downloader.sources import PinterestSource

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(shutil.which("gallery-dl") is None, reason="gallery-dl не установлен"),
]

REPO_ROOT = Path(__file__).resolve().parents[2]
LINKS_FILE = REPO_ROOT / "links.txt"


def _links() -> list[str]:
    if not LINKS_FILE.is_file():
        return []
    result: list[str] = []
    for line in LINKS_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            result.append(stripped.split()[0])
    return result


def test_бинарник_находится() -> None:
    assert find_gallery_dl() is not None


def test_альбом_скачивается_целиком(tmp_path: Path) -> None:
    """Альбом из links.txt: скачаны все картинки, прогресс сходится."""
    links = _links()
    assert links, "links.txt пуст или отсутствует"
    url = links[-1]
    runner = GalleryDlRunner(destination=tmp_path)
    total = runner.count_files(url)
    assert total > 1, "альбом должен содержать несколько картинок"

    result = runner.run(url)
    assert result.returncode == 0
    assert result.downloaded == total
    assert len(result.files) == total
    for path in result.files:
        assert Path(path).is_file()


def test_картинка_скачивается_одним_файлом(tmp_path: Path) -> None:
    """Первая ссылка из links.txt — одиночная картинка."""
    links = _links()
    assert len(links) >= 2, "в links.txt нет второй ссылки"
    url = links[0]
    runner = GalleryDlRunner(destination=tmp_path)
    result = runner.run(url)
    assert result.returncode == 0
    assert result.downloaded == 1
    assert len(result.files) == 1
    assert Path(result.files[0]).is_file()


def test_битая_ссылка_даёт_ошибку_а_не_исключение(tmp_path: Path) -> None:
    runner = GalleryDlRunner(destination=tmp_path)
    result = runner.run("https://pin.it/THIS_LINK_DOES_NOT_EXIST_12345")
    assert result.returncode != 0
    assert result.errors >= 1


def test_картинка_попадает_прямо_в_выбранную_папку(tmp_path: Path) -> None:
    """Выбранная папка — конечная точка: своих подкаталогов не появляется."""
    links = _links()
    url = links[0]
    source = PinterestSource()
    runner = GalleryDlRunner(destination=tmp_path, directory_formats=source.directory_formats)
    result = runner.run(url)
    assert result.returncode == 0
    entries = list(tmp_path.iterdir())
    assert entries, "файл не скачался"
    assert all(entry.is_file() for entry in entries), "появился лишний каталог"


def test_альбом_кладётся_в_одну_папку_с_названием(tmp_path: Path) -> None:
    """У альбома одна папка с названием, файлы лежат в ней."""
    links = _links()
    url = links[-1]
    source = PinterestSource()
    runner = GalleryDlRunner(destination=tmp_path, directory_formats=source.directory_formats)
    total = runner.count_files(url)
    assert total > 1
    result = runner.run(url)
    assert result.returncode == 0
    directories = [entry for entry in tmp_path.iterdir() if entry.is_dir()]
    assert len(directories) == 1, f"ожидалась одна папка альбома, а их {len(directories)}"
    assert list(directories[0].iterdir())
