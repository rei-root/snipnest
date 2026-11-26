"""Исполнитель yt-dlp: команда, разбор вывода, поиск бинарника."""

from __future__ import annotations

from pathlib import Path

import pytest

from snipnest.downloader import DownloadEventKind
from snipnest.formats import audio_format_by_id, video_format_by_id
from snipnest.ytdlp import (
    YtDlpNotFoundError,
    YtDlpRunner,
    find_ffmpeg,
    find_js_runtime,
    find_yt_dlp,
    overall_percent,
    parse_stream_count,
    parse_ytdlp_line,
)

URL = "https://youtu.be/dQw4w9WgXcQ"


def _make_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\necho 1.0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_поставленный_ffmpeg_передаётся_yt_dlp(monkeypatch, tmp_path: Path) -> None:
    """ffmpeg лежит не в PATH, поэтому путь передаётся явно."""
    binary = _make_executable(tmp_path / "ffmpeg" / "bin" / "ffmpeg")
    monkeypatch.setattr("snipnest.ytdlp.find_component_binary", lambda name: str(binary))

    command = YtDlpRunner(destination=tmp_path).build_command(URL)

    assert "--ffmpeg-location" in command
    assert str(binary) in command


def test_ffmpeg_из_пути_тоже_находится(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("snipnest.ytdlp.find_component_binary", lambda name: None)
    monkeypatch.setattr("snipnest.ytdlp.shutil.which", lambda name: "/usr/bin/ffmpeg")

    assert find_ffmpeg() == "/usr/bin/ffmpeg"


def test_рантайм_из_каталога_компонентов_передаётся_путём(monkeypatch, tmp_path: Path) -> None:
    """Рантайм из мастера установки лежит не в PATH — путь передаётся явно."""
    binary = _make_executable(tmp_path / "deno" / "bin" / "deno")
    monkeypatch.setattr("snipnest.ytdlp.find_component_binary", lambda name: str(binary))
    monkeypatch.setattr("snipnest.ytdlp.shutil.which", lambda name: None)

    assert find_js_runtime() == f"deno:{binary}"


def test_рантайм_из_пути_передаётся_именем(monkeypatch) -> None:
    monkeypatch.setattr("snipnest.ytdlp.find_component_binary", lambda name: None)
    monkeypatch.setattr("snipnest.ytdlp.shutil.which", lambda name: "/usr/bin/deno")

    assert find_js_runtime() == "deno"


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


def _video_format(format_id: str):
    """Формат видео по идентификатору."""
    found = video_format_by_id(format_id)
    assert found is not None
    return found


def _audio_format(format_id: str):
    """Формат звука по идентификатору."""
    found = audio_format_by_id(format_id)
    assert found is not None
    return found


def test_команда_для_mp4_берёт_h264_и_aac() -> None:
    """R3: MP4 — видео H.264 со звуком AAC."""
    runner = YtDlpRunner(destination=Path("/tmp/out"), video_format=_video_format("mp4"))

    command = runner.build_command(URL)

    selector = command[command.index("-f") + 1]
    assert "ext=mp4" in selector
    assert "ext=m4a" in selector
    assert command[command.index("--merge-output-format") + 1] == "mp4"


def test_команда_для_webm_берёт_vp9_и_opus() -> None:
    """R3: WebM — видео VP9 со звуком Opus."""
    runner = YtDlpRunner(destination=Path("/tmp/out"), video_format=_video_format("webm"))

    command = runner.build_command(URL)

    selector = command[command.index("-f") + 1]
    assert "ext=webm" in selector
    assert command[command.index("--merge-output-format") + 1] == "webm"


def test_команда_для_mkv_берёт_любые_кодеки() -> None:
    """R3: MKV — контейнер, который берёт любые доступные кодеки."""
    runner = YtDlpRunner(destination=Path("/tmp/out"), video_format=_video_format("mkv"))

    command = runner.build_command(URL)

    assert command[command.index("--merge-output-format") + 1] == "mkv"


def test_команда_только_звука_извлекает_аудио() -> None:
    """R3: «только звук» — звуковой поток переводится в выбранный формат."""
    runner = YtDlpRunner(
        destination=Path("/tmp/out"),
        video_format=_video_format("audio"),
        audio_format=_audio_format("flac"),
    )

    command = runner.build_command(URL)

    assert "-x" in command
    assert command[command.index("--audio-format") + 1] == "flac"
    assert "--merge-output-format" not in command


def test_раздельные_файлы_скачиваются_двумя_запусками() -> None:
    """R3: «видео и звук отдельно» — видеопоток и звуковой поток отдельно."""
    runner = YtDlpRunner(destination=Path("/tmp/out"), video_format=_video_format("separate"))

    steps = runner.build_steps(URL)

    assert len(steps) == 2
    assert steps[0].command[steps[0].command.index("-f") + 1] == "bv*"
    assert steps[1].command[steps[1].command.index("-f") + 1] == "ba"


def test_раздельные_файлы_получают_разные_имена() -> None:
    """R4: расширения потоков могут совпасть, поэтому имена различаются."""
    runner = YtDlpRunner(destination=Path("/tmp/out"), video_format=_video_format("separate"))

    steps = runner.build_steps(URL)

    templates = [step.command[step.command.index("-o") + 1] for step in steps]
    assert templates[0] != templates[1]
    assert "(видео)" in templates[0]
    assert "(звук)" in templates[1]


def test_счётчик_файлов_у_раздельных_файлов_два() -> None:
    """R3: раздельные файлы — два файла на диске."""
    runner = YtDlpRunner(destination=Path("/tmp/out"), video_format=_video_format("separate"))

    assert runner.count_files(URL) == 2


def test_счётчик_файлов_у_обычного_видео_один() -> None:
    """R4: умолчание прежнее — одна ссылка даёт один файл."""
    runner = YtDlpRunner(destination=Path("/tmp/out"))

    assert runner.count_files(URL) == 1
