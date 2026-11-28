"""Границы сборки: версия, архитектура, форматы артефактов и запрет сети.

Требования, которые закрывают эти проверки:

* R1 — бизнес-контекст: программа должна доходить до машины пользователя
  готовым артефактом, а не только исходниками;
* R2 — стейкхолдеры: приложение остаётся личным локальным инструментом;
* R5 — нефункциональные требования: версия 0.2.3, архитектура только amd64;
* R6 — границы: другие архитектуры, Windows и macOS не входят.
"""

from __future__ import annotations

from pathlib import Path

import snipnest
from snipnest.settings import CONFIG_DIR

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src" / "snipnest"
PACKAGING_DIR = REPO_ROOT / "packaging"

#: Сетевые клиенты, которых в приложении быть не должно: загрузку делает
#: внешняя программа (curl, pip), само приложение никуда не ходит.
FORBIDDEN_IMPORTS = (
    "requests",
    "httpx",
    "aiohttp",
    "urllib.request",
    "http.client",
    "socket",
    "asyncio",
)


def test_версия_приложения_соответствует_выпуску() -> None:
    assert snipnest.__version__ == "0.2.3"


def test_есть_сборщики_всех_трёх_артефактов() -> None:
    """R1: программа доходит до машины пользователя бинарником, AppImage и deb."""
    for script in ("build-onefile.sh", "build-appimage.sh", "build-deb.sh"):
        assert (PACKAGING_DIR / script).is_file(), f"нет сборщика {script}"


def test_приложение_не_ходит_в_сеть_само() -> None:
    """R2: загрузку делает внешняя программа, в приложении сетевых клиентов нет."""
    for path in sorted(SRC_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for name in FORBIDDEN_IMPORTS:
            assert f"import {name}" not in text, f"{path.name} импортирует {name}"


def test_приложение_остаётся_локальным_инструментом() -> None:
    assert CONFIG_DIR.is_relative_to(Path.home())


def test_сборка_рассчитана_только_на_amd64() -> None:
    """R5: архитектура сборки — только amd64."""
    script = (PACKAGING_DIR / "build-deb.sh").read_text(encoding="utf-8")

    assert "amd64" in script
    assert "arm64" not in script


def test_другие_платформы_не_входят() -> None:
    """R6: Windows, macOS и flatpak в задачу не входят."""
    files = sorted(PACKAGING_DIR.glob("*.sh"))

    assert files
    for path in files:
        text = path.read_text(encoding="utf-8").lower()
        assert "flatpak" not in text
        assert "snapcraft" not in text
