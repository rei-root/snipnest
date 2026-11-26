"""Тесты разбора вывода gallery-dl."""

from __future__ import annotations

from pathlib import Path

from snipnest.downloader import (
    DownloadEventKind,
    GalleryDlNotFoundError,
    GalleryDlRunner,
    find_gallery_dl,
    parse_output_line,
)

#: Заглушка gallery-dl: создаёт файл в выбранной папке и печатает его путь.
STUB_GALLERY_DL = """#!/usr/bin/env python3
import os
import pathlib
import sys

args = sys.argv[1:]

if "--version" in args:
    print("1.32.20")
    raise SystemExit(0)

destination = pathlib.Path(args[args.index("--destination") + 1])
name = os.environ.get("SNIPNEST_STUB_FILE", "photo.png")
target = destination / name
target.write_bytes(b"payload")
print(target)
"""


def _make_stub(path: Path) -> Path:
    path.write_text(STUB_GALLERY_DL, encoding="utf-8")
    path.chmod(0o755)
    return path


def _renaming_converter(source: Path, extension: str) -> Path | None:
    """Перевод картинки для проверки: файл получает другое расширение."""
    target = source.with_suffix("." + extension)
    source.rename(target)
    return target


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


def test_скачанная_картинка_перекодируется_в_выбранный_формат(tmp_path) -> None:
    """R3: картинка сохраняется в выбранном формате."""
    binary = _make_stub(tmp_path / "gallery-dl-stub")
    runner = GalleryDlRunner(
        binary=str(binary),
        destination=tmp_path,
        image_extension="jpg",
        converter=_renaming_converter,
    )

    result = runner.run("https://pin.it/abc")

    assert result.returncode == 0
    assert [Path(path).suffix for path in result.files] == [".jpg"]


def test_исходный_файл_заменяется_перекодированным(tmp_path) -> None:
    """R4: в папке остаётся один файл — в выбранном формате."""
    binary = _make_stub(tmp_path / "gallery-dl-stub")
    runner = GalleryDlRunner(
        binary=str(binary),
        destination=tmp_path,
        image_extension="jpg",
        converter=_renaming_converter,
    )

    runner.run("https://pin.it/abc")

    assert sorted(entry.name for entry in tmp_path.iterdir() if entry.is_file()) == [
        "gallery-dl-stub",
        "photo.jpg",
    ]


def test_файл_не_картинка_не_перекодируется(tmp_path, monkeypatch) -> None:
    """R4: перекодируются только картинки, видео с Pinterest не трогается."""
    monkeypatch.setenv("SNIPNEST_STUB_FILE", "clip.mp4")
    binary = _make_stub(tmp_path / "gallery-dl-stub")
    runner = GalleryDlRunner(
        binary=str(binary),
        destination=tmp_path,
        image_extension="jpg",
        converter=_renaming_converter,
    )

    result = runner.run("https://pin.it/abc")

    assert [Path(path).suffix for path in result.files] == [".mp4"]


def test_без_выбора_формата_файл_не_трогается(tmp_path) -> None:
    """R4: умолчание прежнее — «как скачано», перекодировки нет."""
    binary = _make_stub(tmp_path / "gallery-dl-stub")
    runner = GalleryDlRunner(binary=str(binary), destination=tmp_path)

    result = runner.run("https://pin.it/abc")

    assert [Path(path).suffix for path in result.files] == [".png"]
