"""Раскладка файлов внутри выбранной папки.

Правило задачи: выбранная папка — конечная точка, а не база для дерева
каталогов. Файл картинки кладётся прямо в неё; для альбома создаётся ровно
одна папка с названием альбома, и файлы альбома лежат в ней.
"""

from __future__ import annotations

from pathlib import Path

from snipnest.downloader import GalleryDlRunner
from snipnest.sources import PinterestSource


def _command_for(file_count: int, tmp_path: Path) -> list[str]:
    """Команда gallery-dl для загрузки с указанным числом файлов."""
    source = PinterestSource()
    runner = GalleryDlRunner(
        destination=tmp_path,
        directory_formats=source.directory_formats,
    )
    return runner.build_command("https://pin.it/abc", file_count=file_count)


def test_картинка_кладётся_прямо_в_выбранную_папку(tmp_path: Path) -> None:
    """Один файл — без подпапок: выбранная папка это конечная точка."""
    command = _command_for(1, tmp_path)
    assert 'directory=[""]' in command


def test_альбом_кладётся_в_одну_папку_с_названием(tmp_path: Path) -> None:
    """Альбом — одна папка с названием доски, имя берёт gallery-dl."""
    command = _command_for(12, tmp_path)
    assert 'directory=["{board[name]:?//}"]' in command


def test_по_умолчанию_файлы_идут_прямо_в_выбранную_папку(tmp_path: Path) -> None:
    """Правило действует всегда: своих подкаталогов приложение не заводит."""
    runner = GalleryDlRunner(destination=tmp_path)
    command = runner.build_command("https://pin.it/abc")
    assert 'directory=[""]' in command


def test_источник_различает_картинку_и_альбом() -> None:
    """Картинка — прямо в папку, альбом — в папку с названием."""
    source = PinterestSource()
    assert source.directory_formats(1) == [""]
    assert source.directory_formats(0) == [""]
    assert source.directory_formats(2) == ["{board[name]:?//}"]


class _FakeGalleryDl:
    """Подделка gallery-dl: на --simulate печатает два файла."""

    def __init__(self, directory: Path) -> None:
        self._path = directory / "gallery-dl"
        self._path.write_text(
            "#!/bin/sh\n"
            'for arg in "$@"; do\n'
            '  if [ "$arg" = "--simulate" ]; then\n'
            '    echo "# photo.jpg"\n'
            '    echo "# photo2.jpg"\n'
            "  fi\n"
            "done\n",
            encoding="utf-8",
        )
        self._path.chmod(0o755)

    @property
    def path(self) -> str:
        return str(self._path)


def test_исполнитель_помнит_число_файлов_из_предварительного_прохода(tmp_path: Path) -> None:
    """Раскладка альбома включается тем же проходом, что считает счётчик."""
    fake = _FakeGalleryDl(tmp_path)
    source = PinterestSource()
    runner = GalleryDlRunner(
        binary=fake.path,
        destination=tmp_path,
        directory_formats=source.directory_formats,
    )

    assert runner.count_files("https://pin.it/abc") == 2
    command = runner.build_command("https://pin.it/abc")
    assert 'directory=["{board[name]:?//}"]' in command
