"""Настоящий yt-dlp и закреплённая версия: приложение не должно взять сломанную.

Требования, которые закрывают эти проверки:

* R3 — требования: тот yt-dlp, который найдёт приложение, не старше
  закреплённой в каталоге компонентов версии.
"""

from __future__ import annotations

import subprocess

from snipnest.binaries import find_yt_dlp
from snipnest.components.catalog import component_by_id


def _version_parts(version: str) -> tuple[int, ...]:
    """Версия как набор чисел: «2026.11.23» → (2026, 11, 23)."""
    return tuple(int(part) for part in version.split("."))


def test_yt_dlp_приложения_не_старше_закреплённого() -> None:
    """R3: на сломанной версии YouTube отдаёт только картинки — видео не идёт."""
    binary = find_yt_dlp()
    assert binary is not None, "yt-dlp не найден в PATH и в компонентах"

    result = subprocess.run(
        [binary, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stdout.strip(), "yt-dlp не ответил версией"

    spec = component_by_id("yt-dlp")
    assert spec is not None
    pinned = spec.packages[0].split("==")[-1]
    assert _version_parts(result.stdout.strip().split()[0]) >= _version_parts(pinned)
