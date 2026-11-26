"""Настоящий yt-dlp и команда выбора формата: бинарь должен понимать флаги.

Требования, которые закрывают эти проверки:

* R3 — требования: команда, которую собирает приложение, понятна настоящему
  yt-dlp: неизвестного ключа быть не может.

Сеть не нужна: ссылка.file:// не открывается, но ключи команды проверяются
раньше, чем yt-dlp возьмётся за ссылку.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from snipnest.formats import audio_format_by_id, video_format_by_id
from snipnest.ytdlp import YtDlpRunner

pytestmark = pytest.mark.skipif(
    shutil.which("yt-dlp") is None,
    reason="yt-dlp не установлен",
)

#: Ссылка, которую yt-dlp не откроет и в сеть не пойдёт.
LOCAL_URL = "file:///nonexistent/video.mp4"


def test_настоящий_yt_dlp_понимает_флаги_выбора_формата(tmp_path: Path) -> None:
    """R3: ключи извлечения звука знакомы настоящему yt-dlp."""
    runner = YtDlpRunner(
        destination=tmp_path,
        video_format=video_format_by_id("audio"),
        audio_format=audio_format_by_id("flac"),
    )

    result = subprocess.run(
        runner.build_command(LOCAL_URL),
        capture_output=True,
        text=True,
        check=False,
    )

    assert "no such option" not in result.stderr
    assert "unrecognized option" not in result.stderr


def test_настоящий_yt_dlp_понимает_выбор_раздельных_файлов(tmp_path: Path) -> None:
    """R3: оба запуска раздельных файлов понятны настоящему yt-dlp."""
    runner = YtDlpRunner(destination=tmp_path, video_format=video_format_by_id("separate"))

    steps = runner.build_steps(LOCAL_URL)

    assert len(steps) == 2
    for step in steps:
        result = subprocess.run(
            [*step.command, LOCAL_URL],
            capture_output=True,
            text=True,
            check=False,
        )
        assert "no such option" not in result.stderr
        assert "unrecognized option" not in result.stderr
