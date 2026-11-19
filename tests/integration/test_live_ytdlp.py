"""Живые тесты: настоящий yt-dlp ходит в сеть.

Тесты помечены маркером ``live`` и в оракул не входят: им нужны
установленный yt-dlp, ffmpeg и доступ к YouTube.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from snipnest.cookies import detect_browser_sources
from snipnest.ytdlp import YtDlpRunner

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(shutil.which("yt-dlp") is None, reason="yt-dlp не установлен"),
]

# «Me at the zoo» — первый ролик на YouTube: открытый доступ, весит меньше мегабайта.
VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
SHORTS_URL = "https://www.youtube.com/shorts/jNQXAC9IVRw"

# Ролик, который без cookies YouTube не отдаёт: проверка бота.
GUARDED_URL = "https://www.youtube.com/watch?v=dgKRqagdjOU"


def _browser() -> str:
    """Первый найденный в системе источник cookies из браузера."""
    sources = detect_browser_sources()
    return sources[0].browser if sources else ""


#: YouTube без cookies отвечает «Sign in to confirm you're not a bot»,
#: поэтому живые загрузки идут с cookies браузера владельца.
BROWSER = _browser()

needs_browser = pytest.mark.skipif(
    not BROWSER,
    reason="в системе нет браузера с cookies: YouTube без них не отдаёт ролик",
)


@needs_browser
def test_видео_скачивается_в_выбранную_папку(tmp_path: Path) -> None:
    runner = YtDlpRunner(destination=tmp_path, cookies_browser=BROWSER)
    result = runner.run(VIDEO_URL)

    assert result.returncode == 0, result.errors
    assert result.downloaded == 1
    assert len(result.files) == 1

    path = Path(result.files[0])
    assert path.is_file()
    assert path.parent == tmp_path
    assert path.stat().st_size > 0

    # Выбранная папка — конечная точка: своих подкаталогов не появляется.
    entries = list(tmp_path.iterdir())
    assert entries
    assert all(entry.is_file() for entry in entries)


@needs_browser
def test_шортс_скачивается_как_обычное_видео(tmp_path: Path) -> None:
    runner = YtDlpRunner(destination=tmp_path, cookies_browser=BROWSER)
    result = runner.run(SHORTS_URL)

    assert result.returncode == 0
    assert result.downloaded == 1
    assert Path(result.files[0]).is_file()


@needs_browser
def test_уже_скачанный_файл_не_качается_заново(tmp_path: Path) -> None:
    runner = YtDlpRunner(destination=tmp_path, cookies_browser=BROWSER)
    first = runner.run(VIDEO_URL)
    assert first.returncode == 0

    second = YtDlpRunner(destination=tmp_path, cookies_browser=BROWSER).run(VIDEO_URL)
    assert second.returncode == 0
    assert second.skipped == 1


def test_недоступный_ролик_даёт_ошибку_а_не_исключение(tmp_path: Path) -> None:
    runner = YtDlpRunner(destination=tmp_path)
    result = runner.run("https://www.youtube.com/watch?v=XXXXXXXXXXX")
    assert result.returncode != 0
    assert result.errors >= 1


@pytest.mark.skipif(not _browser(), reason="в системе нет браузера с cookies")
def test_ролик_с_проверкой_бота_извлекается_с_cookies(tmp_path: Path) -> None:
    """Без cookies YouTube отвечает «Sign in to confirm you're not a bot»."""
    runner = YtDlpRunner(destination=tmp_path, cookies_browser=_browser())
    command = runner.build_command(GUARDED_URL)
    command.append("--simulate")

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr[-400:]
    assert "Sign in to confirm" not in result.stderr
