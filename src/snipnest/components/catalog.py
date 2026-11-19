"""Каталог компонентов: что приложение умеет доустановить и откуда.

Компоненты двух видов:

* :attr:`ComponentKind.PIP` — Python-пакеты: ставятся переносимым Python
  из артефакта в отдельный каталог (``pip install --target``);
* :attr:`ComponentKind.ARCHIVE` — готовые бинарники: скачиваются архивом
  и распаковываются рядом.

Версии зафиксированы: мастер ставит ровно то, что проверено сборкой.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

__all__ = ["COMPONENTS", "ComponentKind", "ComponentSpec", "component_by_id"]


class ComponentKind(enum.Enum):
    """Способ установки компонента."""

    PIP = "pip"
    ARCHIVE = "archive"


@dataclass(frozen=True)
class ComponentSpec:
    """Описание компонента: что это, чем запускается и откуда берётся."""

    id: str
    title: str
    description: str
    kind: ComponentKind
    binary: str = ""
    module: str = ""
    packages: tuple[str, ...] = ()
    url: str = ""
    sha256: str = ""
    size_hint: int = 0
    extra_paths: tuple[str, ...] = ()


GALLERY_DL = ComponentSpec(
    id="gallery-dl",
    title="gallery-dl",
    description="Скачивание из Pinterest",
    kind=ComponentKind.PIP,
    binary="gallery-dl",
    module="gallery_dl",
    packages=("gallery-dl==1.32.20",),
    size_hint=16 * 1024 * 1024,
)

YT_DLP = ComponentSpec(
    id="yt-dlp",
    title="yt-dlp",
    description="Скачивание видео с YouTube",
    kind=ComponentKind.PIP,
    binary="yt-dlp",
    module="yt_dlp",
    packages=("yt-dlp==2026.10.26",),
    size_hint=4 * 1024 * 1024,
    extra_paths=("yt-dlp-ejs",),
)

YT_DLP_EJS = ComponentSpec(
    id="yt-dlp-ejs",
    title="yt-dlp-ejs",
    description="Скрипты задачи YouTube: полный набор форматов",
    kind=ComponentKind.PIP,
    module="yt_dlp_ejs",
    packages=("yt-dlp-ejs==0.8.0",),
    size_hint=1024 * 1024,
)

DENO = ComponentSpec(
    id="deno",
    title="deno",
    description="JS-рантайм для скриптов задачи",
    kind=ComponentKind.ARCHIVE,
    binary="deno",
    url=(
        "https://github.com/denoland/deno/releases/download/v2.9.8/"
        "deno-x86_64-unknown-linux-gnu.zip"
    ),
    sha256="e890975bc2549807bbcc0b584ffafda72cc7c93349dd99c80483dd784f6c4609",
    size_hint=42 * 1024 * 1024,
)

FFMPEG = ComponentSpec(
    id="ffmpeg",
    title="ffmpeg",
    description="Склейка видео со звуком",
    kind=ComponentKind.ARCHIVE,
    binary="ffmpeg",
    url=(
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
        "autobuild-2026-11-19-12-39/ffmpeg-N-129130-gcd39c36377-linux64-gpl.tar.xz"
    ),
    sha256="faeb9f258c7b5f3c39ce173375268db8a365ee2badb5b50208caf5e48362c5d5",
    size_hint=151 * 1024 * 1024,
)

COMPONENTS: tuple[ComponentSpec, ...] = (GALLERY_DL, YT_DLP, YT_DLP_EJS, DENO, FFMPEG)


def component_by_id(component_id: str) -> ComponentSpec | None:
    """Компонент по идентификатору или None, если такого нет."""
    for spec in COMPONENTS:
        if spec.id == component_id:
            return spec
    return None
