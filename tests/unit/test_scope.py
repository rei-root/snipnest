"""Проверки границ задачи: что приложение локальное и что в него не входит.

Требования, которые закрывают эти проверки:

* R2 — стейкхолдеры и пользователи: единственный пользователь — владелец,
  приложение личное и локальное, запускается на его машине, скачивание
  делает внешний системный gallery-dl;
* R6 — границы: кроме Pinterest другие соцсети не поддерживаются, в задачу
  не входят видео, поиск, планировщик и авторизация по логину/паролю.
"""

from __future__ import annotations

from pathlib import Path

from gallary_downloader.settings import CONFIG_DIR, DEFAULT_DESTINATION
from gallary_downloader.sources import SourceKind, SourceRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src" / "gallary_downloader"

# Сетевые клиенты и серверные frameworks, которых в приложении быть не должно:
# скачивание делегировано внешнему бинарнику, само приложение никуда не ходит.
FORBIDDEN_IMPORTS = (
    "requests",
    "httpx",
    "aiohttp",
    "urllib.request",
    "http.client",
    "socket",
    "asyncio",
    "flask",
    "fastapi",
    "uvicorn",
)


def test_приложение_локальное_и_однопользовательское() -> None:
    """R2: личный инструмент владельца — локальный, без сервера и без сети."""
    assert CONFIG_DIR.is_relative_to(Path.home())
    assert DEFAULT_DESTINATION.is_relative_to(Path.home())

    for path in sorted(SRC_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for name in FORBIDDEN_IMPORTS:
            assert f"import {name}" not in text, f"{path.name} импортирует {name}"


def test_поддерживается_только_pinterest() -> None:
    """R6: кроме Pinterest другие соцсети в задачу не входят."""
    registry = SourceRegistry()

    assert [source.title for source in registry.sources] == ["Pinterest"]
    assert registry.sources[0].kind is SourceKind.PINTEREST

    for url in (
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.tiktok.com/@user/video/1234567890",
        "https://vk.com/video-1_2",
        "https://example.com/pin/123456/",
    ):
        assert registry.find(url) is None, f"{url} не должен поддерживаться"
