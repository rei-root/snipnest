"""Определение типа ссылки: картинка или альбом Pinterest, видео YouTube.

Модуль чистый: ни одной сетевой проверки, только разбор URL.
"""

from __future__ import annotations

import enum
import re
from urllib.parse import urlparse

__all__ = ["LinkKind", "LinkInfo", "classify_link", "is_valid_link"]


class LinkKind(enum.Enum):
    """Тип ссылки."""

    PIN = "pin"
    BOARD = "board"
    VIDEO = "video"
    UNKNOWN = "unknown"


class LinkInfo:
    """Разобранная ссылка Pinterest."""

    __slots__ = ("kind", "url", "pin_id", "board_path")

    def __init__(
        self, kind: LinkKind, url: str, pin_id: str | None = None, board_path: str | None = None
    ) -> None:
        self.kind = kind
        self.url = url
        self.pin_id = pin_id
        self.board_path = board_path

    def __repr__(self) -> str:
        return f"LinkInfo(kind={self.kind.name}, url={self.url!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LinkInfo):
            return NotImplemented
        return (
            self.kind == other.kind
            and self.url == other.url
            and self.pin_id == other.pin_id
            and self.board_path == other.board_path
        )


_PIN_PATH = re.compile(r"^/pin/([1-9][0-9]*)(?:/|$)", re.IGNORECASE)
_BOARD_PATH = re.compile(r"^/[^/]+/[^/]+/?$")


def _is_pinterest_host(host: str) -> bool:
    return (
        host == "pin.it"
        or host == "pinterest.com"
        or host.endswith(".pinterest.com")
        or host.endswith(".pinterest.ru")
    )


def classify_link(url: str) -> LinkInfo:
    """Определить, что за ссылка: картинка (pin) или альбом (board)."""
    normalized = url.strip()
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not _is_pinterest_host(host):
        return LinkInfo(LinkKind.UNKNOWN, normalized)

    if host == "pin.it":
        return LinkInfo(LinkKind.UNKNOWN, normalized)

    path = parsed.path
    pin_match = _PIN_PATH.match(path)
    if pin_match is not None:
        return LinkInfo(LinkKind.PIN, normalized, pin_id=pin_match.group(1))

    if path.startswith("/user/") or _BOARD_PATH.match(path):
        return LinkInfo(LinkKind.BOARD, normalized, board_path=path.rstrip("/"))

    return LinkInfo(LinkKind.UNKNOWN, normalized)


def is_valid_link(url: str) -> bool:
    """True, если строка похожа на ссылку Pinterest."""
    normalized = url.strip()
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not _is_pinterest_host(host):
        return False
    return bool(parsed.path.strip("/") or host == "pin.it")
