"""Интеграционные тесты: настоящий бинарник yt-dlp.

Сеть здесь не используется: проверяется только то, как приложение работает
с установленным yt-dlp. Живые загрузки — в ``test_live_ytdlp.py``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from snipnest.ytdlp import YtDlpNotFoundError, YtDlpRunner, find_yt_dlp

pytestmark = pytest.mark.skipif(
    shutil.which("yt-dlp") is None,
    reason="yt-dlp не установлен в системе",
)


def test_настоящий_бинарник_печатает_версию() -> None:
    result = subprocess.run(
        ["yt-dlp", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip()


def test_бинарник_находится_в_path() -> None:
    assert find_yt_dlp() is not None


def test_несуществующий_бинарник_даёт_ошибку() -> None:
    runner = YtDlpRunner(binary="/nonexistent/yt-dlp")
    with pytest.raises(YtDlpNotFoundError):
        runner.resolve_binary()


def test_команда_содержит_папку_и_ссылку(tmp_path: Path) -> None:
    runner = YtDlpRunner(destination=tmp_path)
    command = runner.build_command("https://youtu.be/dQw4w9WgXcQ")
    assert str(tmp_path) in command
    assert command[-1] == "https://youtu.be/dQw4w9WgXcQ"


def test_путь_назначения_используется(tmp_path: Path) -> None:
    runner = YtDlpRunner(destination=tmp_path)
    command = runner.build_command("https://youtu.be/dQw4w9WgXcQ")
    assert str(tmp_path) in command
