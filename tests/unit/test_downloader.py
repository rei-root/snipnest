"""Тесты разбора вывода gallery-dl."""

from __future__ import annotations

from snipnest.downloader import (
    DownloadEventKind,
    GalleryDlNotFoundError,
    GalleryDlRunner,
    find_gallery_dl,
    parse_output_line,
)


def test_путь_скачанного_файла() -> None:
    event = parse_output_line("pinterest/pin_1.jpg\n")
    assert event.kind is DownloadEventKind.FILE_DOWNLOADED
    assert event.path == "pinterest/pin_1.jpg"


def test_решётка_означает_пропущенный_файл() -> None:
    event = parse_output_line("# pinterest/pin_1.jpg\n")
    assert event.kind is DownloadEventKind.FILE_SKIPPED
    assert event.path == "pinterest/pin_1.jpg"


def test_отладочная_строка_не_считается_файлом() -> None:
    """Отладка gallery-dl идёт в stderr и файлом не является."""
    event = parse_output_line("[gallery-dl][debug] Starting DownloadJob\n", stream="stderr")
    assert event.kind is DownloadEventKind.LOG
    assert event.path is None


def test_строка_из_stderr_не_считается_файлом() -> None:
    event = parse_output_line("[pinterest][error] NotFoundError\n", stream="stderr")
    assert event.kind is DownloadEventKind.LOG
    assert event.path is None


def test_пустая_строка_не_считается_файлом() -> None:
    event = parse_output_line("   \n")
    assert event.kind is DownloadEventKind.LOG
    assert event.path is None


def test_поиск_бинарника_в_path() -> None:
    assert find_gallery_dl() is not None


def test_явный_путь_к_несуществующему_бинарнику() -> None:
    assert find_gallery_dl("/nonexistent/gallery-dl") is None


def test_отсутствие_бинарника_даёт_понятную_ошибку() -> None:
    runner = GalleryDlRunner(binary="/nonexistent/gallery-dl")
    try:
        runner.resolve_binary()
    except GalleryDlNotFoundError as exc:
        assert "gallery-dl" in str(exc)
    else:
        raise AssertionError("ожидалась GalleryDlNotFoundError")


def test_команда_содержит_папку_и_ссылку(tmp_path) -> None:
    runner = GalleryDlRunner(destination=tmp_path)
    command = runner.build_command("https://pin.it/abc")
    assert "--destination" in command
    assert str(tmp_path) in command
    assert command[-1] == "https://pin.it/abc"


def test_команда_для_подсчёта_файлов_не_скачивает(tmp_path) -> None:
    runner = GalleryDlRunner(destination=tmp_path)
    command = runner.build_command("https://pin.it/abc", simulate=True)
    assert "--simulate" in command
