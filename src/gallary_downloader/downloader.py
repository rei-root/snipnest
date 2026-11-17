"""Обёртка над внешним бинарником gallery-dl.

Модуль не знает про Qt: он запускает процесс, читает его вывод и превращает
поток строк в события загрузки. UI подписывается на эти события.
"""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Callable
from pathlib import Path

__all__ = [
    "DownloadEvent",
    "DownloadEventKind",
    "DownloadResult",
    "GalleryDlRunner",
    "GalleryDlNotFoundError",
    "parse_output_line",
    "find_gallery_dl",
]


class GalleryDlNotFoundError(RuntimeError):
    """Бинарник gallery-dl не найден."""


class DownloadEventKind(enum.Enum):
    """События загрузки, которые видит UI."""

    FILE_DOWNLOADED = "file_downloaded"
    FILE_SKIPPED = "file_skipped"
    LOG = "log"
    ERROR = "error"


@dataclasses.dataclass(frozen=True)
class DownloadEvent:
    """Одно событие загрузки."""

    kind: DownloadEventKind
    path: str | None = None
    text: str = ""


@dataclasses.dataclass(frozen=True)
class DownloadResult:
    """Итог одной загрузки."""

    downloaded: int
    skipped: int
    errors: int
    returncode: int
    files: tuple[str, ...]


def parse_output_line(line: str, stream: str = "stdout") -> DownloadEvent:
    """Разобрать строку вывода gallery-dl.

    gallery-dl пишет в stdout пути скачанных файлов, а путь уже
    существующего файла — с префиксом ``#``. В stderr идёт отладка и
    сообщения об ошибках; они файлами не являются.
    """
    raise NotImplementedError


def find_gallery_dl(explicit: str | None = None) -> str | None:
    """Найти бинарник gallery-dl: явный путь, потом PATH."""
    raise NotImplementedError


class GalleryDlRunner:
    """Запускает gallery-dl и раздаёт события подписчикам.

    Запускается в отдельном потоке: UI не должен ждать сеть.
    """

    def __init__(
        self,
        binary: str | None = None,
        destination: Path | None = None,
        cookies: str | None = None,
        on_event: Callable[[DownloadEvent], None] | None = None,
    ) -> None:
        self._binary = binary
        self._destination = destination
        self._cookies = cookies
        self._on_event = on_event

    def resolve_binary(self) -> str:
        """Путь к бинарнику; бросает GalleryDlNotFoundError, если не найден."""
        raise NotImplementedError

    def build_command(self, url: str, *, simulate: bool = False) -> list[str]:
        """Команда запуска gallery-dl для указанной ссылки."""
        raise NotImplementedError

    def run(self, url: str, *, simulate: bool = False) -> DownloadResult:
        """Запустить загрузку и дождаться конца. Возвращает итог."""
        raise NotImplementedError

    def count_files(self, url: str) -> int:
        """Сколько файлов gallery-dl соберётся скачать по ссылке."""
        raise NotImplementedError

    def cancel(self) -> bool:
        """Остановить текущий процесс. True, если он был и остановлен."""
        raise NotImplementedError
