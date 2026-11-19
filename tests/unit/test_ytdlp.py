"""Исполнитель yt-dlp: команда, разбор вывода, поиск бинарника."""

from __future__ import annotations

from pathlib import Path

import pytest

from snipnest.downloader import DownloadEventKind
from snipnest.ytdlp import (
    YtDlpNotFoundError,
    YtDlpRunner,
    find_yt_dlp,
    overall_percent,
    parse_stream_count,
    parse_ytdlp_line,
)

URL = "https://youtu.be/dQw4w9WgXcQ"


def test_команда_кладёт_файл_в_выбранную_папку(tmp_path: Path) -> None:
    runner = YtDlpRunner(destination=tmp_path)
    command = runner.build_command(URL)
    assert "--paths" in command
    assert str(tmp_path) in command
    assert command[-1] == URL


def test_команда_не_качает_плейлист() -> None:
    """Одна ссылка — одно видео."""
    command = YtDlpRunner(destination=Path("/tmp/out")).build_command(URL)
    assert "--no-playlist" in command


def test_имя_файла_по_шаблону() -> None:
    command = YtDlpRunner(destination=Path("/tmp/out")).build_command(URL)
    assert "%(title)s [%(id)s].%(ext)s" in command


def test_команда_склеивает_видео_и_звук_в_mp4() -> None:
    command = YtDlpRunner(destination=Path("/tmp/out")).build_command(URL)
    assert "--merge-output-format" in command
    assert "mp4" in command


def test_команда_берёт_лучшее_качество_с_предпочтением_mp4() -> None:
    command = YtDlpRunner(destination=Path("/tmp/out")).build_command(URL)
    formats = command[command.index("-f") + 1]
    assert "mp4" in formats
    assert "m4a" in formats


def test_разбор_строки_прогресса() -> None:
    event = parse_ytdlp_line("[download]  45.2% of   100.00MiB at    5.00MiB/s ETA 00:12")
    assert event.kind is DownloadEventKind.PROGRESS
    assert event.percent == pytest.approx(45.2)
    assert event.bytes_per_second == pytest.approx(5 * 1024 * 1024)


def test_разбор_строки_прогресса_без_скорости() -> None:
    event = parse_ytdlp_line("[download]   0.0% of    4.42MiB at  Unknown B/s ETA Unknown")
    assert event.kind is DownloadEventKind.PROGRESS
    assert event.percent == pytest.approx(0.0)
    assert event.bytes_per_second is None


def test_разбор_строки_уже_скачанного() -> None:
    event = parse_ytdlp_line("[download] /tmp/out/Video [abc].mp4 has already been downloaded")
    assert event.kind is DownloadEventKind.FILE_SKIPPED
    assert event.path == "/tmp/out/Video [abc].mp4"


def test_обычная_строка_идёт_в_лог() -> None:
    event = parse_ytdlp_line("[youtube] abc123: Downloading webpage")
    assert event.kind is DownloadEventKind.LOG
    assert event.text == "[youtube] abc123: Downloading webpage"


def test_число_потоков_из_информационной_строки() -> None:
    assert parse_stream_count("[info] abc123: Downloading 1 format(s): 394+251") == 2
    assert parse_stream_count("[info] abc123: Downloading 1 format(s): 18") == 1
    assert parse_stream_count("[download]  10.0% of 4.42MiB") is None


def test_общий_процент_считается_по_потокам() -> None:
    assert overall_percent(2, 0, 0.5) == pytest.approx(25.0)
    assert overall_percent(2, 1, 0.0) == pytest.approx(50.0)
    assert overall_percent(2, 1, 1.0) == pytest.approx(100.0)
    assert overall_percent(1, 0, 0.5) == pytest.approx(50.0)


def test_поиск_бинарника_в_path() -> None:
    assert find_yt_dlp() is not None


def test_явный_путь_к_несуществующему_бинарнику() -> None:
    assert find_yt_dlp("/nonexistent/yt-dlp") is None


def test_отсутствие_бинарника_даёт_понятную_ошибку() -> None:
    runner = YtDlpRunner(binary="/nonexistent/yt-dlp")
    with pytest.raises(YtDlpNotFoundError) as error:
        runner.resolve_binary()
    assert "yt-dlp" in str(error.value)


def test_счётчик_файлов_у_video_один() -> None:
    """Одна ссылка — один файл: предварительный проход в сеть не ходит."""
    runner = YtDlpRunner(destination=Path("/tmp/out"))
    assert runner.count_files(URL) == 1


def test_команда_с_браузером_добавляет_cookies_from_browser() -> None:
    runner = YtDlpRunner(
        destination=Path("/tmp/out"),
        cookies_browser="firefox:abc.default-release",
    )
    command = runner.build_command(URL)
    assert "--cookies-from-browser" in command
    assert "firefox:abc.default-release" in command


def test_команда_с_файлом_добавляет_cookies() -> None:
    runner = YtDlpRunner(destination=Path("/tmp/out"), cookies_file="/home/sato/cookies.txt")
    command = runner.build_command(URL)
    assert "--cookies" in command
    assert "/home/sato/cookies.txt" in command


def test_без_cookies_флагов_нет() -> None:
    command = YtDlpRunner(destination=Path("/tmp/out")).build_command(URL)
    assert "--cookies" not in command
    assert "--cookies-from-browser" not in command


def test_имя_исполнителя_для_ошибки() -> None:
    assert YtDlpRunner().name == "yt-dlp"
