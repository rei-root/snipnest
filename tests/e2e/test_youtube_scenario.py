"""E2E-тест: сценарий владельца с видео YouTube целиком.

Тест офлайн: вместо настоящего yt-dlp запускается заглушка, которая ведёт
себя как настоящий по контракту вывода — пишет прогресс, создаёт файл в
выбранной папке и отдаёт путь к готовому файлу.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from snipnest.jobs import JobState  # noqa: E402
from snipnest.settings import FileSecretStore, Settings  # noqa: E402
from snipnest.ui.window import MainWindow  # noqa: E402

pytest.importorskip("PySide6")

VIDEO_URL = "https://youtu.be/dQw4w9WgXcQ"
VIDEO_NAME = "Test Video [abc123].mp4"

STUB_YT_DLP = '''#!/usr/bin/env python3
"""Заглушка yt-dlp: повторяет контракт вывода настоящего."""
import os
import pathlib
import sys

args = sys.argv[1:]

if "--version" in args:
    print("2026.10.26")
    raise SystemExit(0)

# Команда целиком — чтобы тест видел, какие флаги дошли до исполнителя.
argv_file = os.environ.get("SNIPNEST_STUB_ARGV")
if argv_file:
    pathlib.Path(argv_file).write_text("\\n".join(args), encoding="utf-8")

destination = pathlib.Path(args[args.index("--paths") + 1])
name = "Test Video [abc123].mp4"
final = destination / name

if "--print-to-file" in args:
    index = args.index("--print-to-file")
    pathlib.Path(args[index + 2]).write_text(str(final), encoding="utf-8")

final.write_bytes(b"fake video payload")
print("[info] abc123: Downloading 1 format(s): 394+251")
print("[download] Destination: " + str(destination / "Test Video [abc123].f394.mp4"))
print("[download]  50.0% of    4.42MiB at    1.00MiB/s ETA 00:02")
print("[download] 100.0% of    4.42MiB at    1.00MiB/s ETA 00:00")
print("[download] Destination: " + str(destination / "Test Video [abc123].f251.webm"))
print("[download]  50.0% of    1.20MiB at    2.00MiB/s ETA 00:01")
print("[download] 100.0% of    1.20MiB at    2.00MiB/s ETA 00:00")
'''


@pytest.fixture
def stub_binary(tmp_path: Path) -> Path:
    """Заглушка yt-dlp: исполняемый файл с тем же контрактом вывода."""
    path = tmp_path / "yt-dlp-stub"
    path.write_text(STUB_YT_DLP, encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def settings(tmp_path: Path, stub_binary: Path) -> Settings:
    config = tmp_path / "settings.json"
    result = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    result.destination = str(tmp_path / "downloads")
    result.yt_dlp_path = str(stub_binary)
    Path(result.destination).mkdir(parents=True, exist_ok=True)
    return result


@pytest.fixture
def window(qtbot, settings: Settings) -> MainWindow:
    win = MainWindow(settings)
    qtbot.addWidget(win)
    return win


def test_видео_попадает_в_выбранную_папку(window: MainWindow, qtbot) -> None:
    """Ссылка, папка, кнопка — и файл лежит в выбранной папке."""
    window.link_text = VIDEO_URL
    window._on_download_clicked()

    assert len(window.job_ids()) == 1
    job_id = window.job_ids()[0]

    qtbot.waitUntil(
        lambda: (
            window.row_for(job_id) is not None and window.row_for(job_id).state is JobState.DONE
        ),
        timeout=15000,
    )

    row = window.row_for(job_id)
    assert row is not None
    assert row.state is JobState.DONE
    assert row.file_names == [VIDEO_NAME]
    assert row.progress_percent == 100


def test_в_выбранной_папке_появился_файл(window: MainWindow, qtbot, settings: Settings) -> None:
    """Выбранная папка — конечная точка: файл один и лежит прямо в ней."""
    window.link_text = VIDEO_URL
    window._on_download_clicked()

    job_id = window.job_ids()[0]
    qtbot.waitUntil(
        lambda: (
            window.row_for(job_id) is not None and window.row_for(job_id).state is JobState.DONE
        ),
        timeout=15000,
    )

    entries = list(Path(settings.destination).iterdir())
    assert [entry.name for entry in entries] == [VIDEO_NAME]
    assert entries[0].is_file()
    assert entries[0].stat().st_size > 0


def test_ошибка_yt_dlp_показывается_в_логе(window: MainWindow, qtbot, monkeypatch) -> None:
    """Ошибка исполнителя доходит до владельца, а не теряется."""
    from snipnest.ytdlp import YtDlpRunner

    def failing_run(self: YtDlpRunner, url: str) -> object:
        from snipnest.downloader import DownloadResult

        return DownloadResult(0, 0, 1, 1, ())

    monkeypatch.setattr(YtDlpRunner, "run", failing_run)

    window.link_text = VIDEO_URL
    window._on_download_clicked()

    job_id = window.job_ids()[0]
    qtbot.waitUntil(
        lambda: (
            window.row_for(job_id) is not None and window.row_for(job_id).state is JobState.FAILED
        ),
        timeout=15000,
    )

    row = window.row_for(job_id)
    assert row is not None
    assert row.state is JobState.FAILED
    assert "Ошибка загрузки" in window.status_text


def test_команда_yt_dlp_получает_cookies_из_браузера(
    window: MainWindow,
    qtbot,
    settings: Settings,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Выбранный браузер доходит до исполнителя флагом --cookies-from-browser."""
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("SNIPNEST_STUB_ARGV", str(argv_file))
    settings.cookies_browser = "firefox:abc.default-release"

    window.link_text = VIDEO_URL
    window._on_download_clicked()

    job_id = window.job_ids()[0]
    qtbot.waitUntil(
        lambda: (
            window.row_for(job_id) is not None and window.row_for(job_id).state is JobState.DONE
        ),
        timeout=15000,
    )

    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert "--cookies-from-browser" in argv
    assert "firefox:abc.default-release" in argv


def test_команда_yt_dlp_получает_файл_cookies(
    window: MainWindow,
    qtbot,
    settings: Settings,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Выбранный файл доходит до исполнителя флагом --cookies."""
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("SNIPNEST_STUB_ARGV", str(argv_file))
    settings.cookies_file = "/home/sato/cookies.txt"

    window.link_text = VIDEO_URL
    window._on_download_clicked()

    job_id = window.job_ids()[0]
    qtbot.waitUntil(
        lambda: (
            window.row_for(job_id) is not None and window.row_for(job_id).state is JobState.DONE
        ),
        timeout=15000,
    )

    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert "--cookies" in argv
    assert "/home/sato/cookies.txt" in argv


def test_без_выбранного_источника_cookies_флагов_нет(
    window: MainWindow,
    qtbot,
    monkeypatch,
    tmp_path: Path,
) -> None:
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("SNIPNEST_STUB_ARGV", str(argv_file))

    window.link_text = VIDEO_URL
    window._on_download_clicked()

    job_id = window.job_ids()[0]
    qtbot.waitUntil(
        lambda: (
            window.row_for(job_id) is not None and window.row_for(job_id).state is JobState.DONE
        ),
        timeout=15000,
    )

    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert "--cookies" not in argv
    assert "--cookies-from-browser" not in argv
