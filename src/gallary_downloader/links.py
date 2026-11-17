"""Определение типа ссылки Pinterest: одиночная картинка или альбом.

Модуль чистый: ни одной сетевой проверки, только разбор URL.
"""

from __future__ import annotations

import enum

__all__ = ["LinkKind", "LinkInfo", "classify_link", "is_valid_link"]


class LinkKind(enum.Enum):
    """Тип ссылки Pinterest."""

    PIN = "pin"
    BOARD = "board"
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


def classify_link(url: str) -> LinkInfo:
    """Определить, что за ссылка: картинка (pin) или альбом (board)."""
    raise NotImplementedError


def is_valid_link(url: str) -> bool:
    """True, если строка похожа на ссылку Pinterest."""
    raise NotImplementedError
