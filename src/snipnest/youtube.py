"""Разбор ссылок YouTube: какое видео указано в ссылке.

Модуль чистый: ни одной сетевой проверки, только разбор URL. Виды ссылок,
которые понимает приложение: обычное видео (``/watch?v=``), короткая ссылка
(``youtu.be``), Shorts (``/shorts/``), прямая трансляция (``/live/``) и
вставка (``/embed/``).
"""

from __future__ import annotations

import dataclasses
import enum
import re
from urllib.parse import parse_qs, urlparse

__all__ = [
    "YouTubeLink",
    "YouTubeLinkKind",
    "is_youtube_link",
    "parse_youtube_link",
]


class YouTubeLinkKind(enum.Enum):
    """Вид ссылки YouTube."""

    VIDEO = "video"
    SHORTS = "shorts"


@dataclasses.dataclass(frozen=True)
class YouTubeLink:
    """Разобранная ссылка YouTube."""

    kind: YouTubeLinkKind
    url: str
    video_id: str


#: Идентификатор видео на YouTube — ровно 11 символов.
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")

#: Хосты, с которых приходит ссылка на видео.
_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }
)

#: Разделы YouTube, в которых лежит ссылка на видео.
_VIDEO_SECTIONS = frozenset({"shorts", "live", "embed", "v"})


def _video_id_from_query(query: str) -> str:
    """Идентификатор видео из параметра ``v``."""
    values = parse_qs(query).get("v", [])
    return values[0] if values else ""


def parse_youtube_link(url: str) -> YouTubeLink | None:
    """Разобрать ссылку YouTube. None, если это не ссылка на видео."""
    normalized = url.strip()
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in _HOSTS:
        return None

    segments = [part for part in parsed.path.split("/") if part]
    kind = YouTubeLinkKind.VIDEO

    if host in {"youtu.be", "www.youtu.be"}:
        if not segments:
            return None
        video_id = segments[0]
    elif not segments:
        return None
    elif segments[0] == "watch":
        video_id = _video_id_from_query(parsed.query)
    elif segments[0] in _VIDEO_SECTIONS and len(segments) >= 2:
        video_id = segments[1]
        if segments[0] == "shorts":
            kind = YouTubeLinkKind.SHORTS
    else:
        return None

    if not _VIDEO_ID.match(video_id):
        return None
    return YouTubeLink(kind=kind, url=normalized, video_id=video_id)


def is_youtube_link(url: str) -> bool:
    """True, если ссылка ведёт на видео YouTube."""
    return parse_youtube_link(url) is not None
