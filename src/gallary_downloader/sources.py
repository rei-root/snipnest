"""Слой источников: абстракция сайта и конкретная реализация Pinterest.

UI не знает, с какого сайта пришла ссылка. Он спрашивает реестр источников,
какой источник умеет работать со ссылкой, и получает от него готовую
загрузку. Добавление YouTube или TikTok — это новый класс в этом модуле и
одна строка в реестре, правки UI не требуют.
"""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Callable
from pathlib import Path

from .downloader import GalleryDlRunner
from .jobs import DownloadJob, JobEvent
from .links import LinkInfo, LinkKind, classify_link, is_valid_link

__all__ = [
    "SourceKind",
    "SourceInfo",
    "DownloadSource",
    "PinterestSource",
    "SourceRegistry",
    "DEFAULT_SOURCES",
]


class SourceKind(enum.Enum):
    """Вид источника: откуда приходит ссылка."""

    PINTEREST = "pinterest"


@dataclasses.dataclass(frozen=True)
class SourceInfo:
    """Что источник умеет рассказать о ссылке."""

    kind: SourceKind
    title: str
    link_kind: LinkKind
    url: str
    pin_id: str | None = None
    board_path: str | None = None

    @property
    def is_single_image(self) -> bool:
        """True, если ссылка ведёт на одну картинку."""
        return self.link_kind is LinkKind.PIN

    @property
    def is_album(self) -> bool:
        """True, если ссылка ведёт на альбом."""
        return self.link_kind is LinkKind.BOARD


class DownloadSource:
    """Источник загрузок.

    Подкласс отвечает за две вещи: узнать свою ссылку и собрать из неё
    готовую загрузку с нужным исполнителем. Общий код (UI, настройки,
    очерёдность) о таком не знает.
    """

    kind: SourceKind
    title: str

    def matches(self, url: str) -> bool:
        """True, если источник умеет работать с этой ссылкой."""
        raise NotImplementedError

    def describe(self, url: str) -> SourceInfo:
        """Разобрать ссылку и вернуть сведения о ней."""
        raise NotImplementedError

    def build_job(
        self,
        job_id: str,
        url: str,
        destination: str,
        binary: str | None = None,
        cookies: str | None = None,
        on_event: Callable[[JobEvent], None] | None = None,
    ) -> DownloadJob:
        """Собрать загрузку для этой ссылки."""
        raise NotImplementedError


class PinterestSource(DownloadSource):
    """Pinterest: картинка (pin) или альбом (board)."""

    kind = SourceKind.PINTEREST
    title = "Pinterest"

    def matches(self, url: str) -> bool:
        return is_valid_link(url)

    def describe(self, url: str) -> SourceInfo:
        info: LinkInfo = classify_link(url)
        return SourceInfo(
            kind=self.kind,
            title=self.title,
            link_kind=info.kind,
            url=info.url,
            pin_id=info.pin_id,
            board_path=info.board_path,
        )

    def build_job(
        self,
        job_id: str,
        url: str,
        destination: str,
        binary: str | None = None,
        cookies: str | None = None,
        on_event: Callable[[JobEvent], None] | None = None,
    ) -> DownloadJob:
        runner = GalleryDlRunner(
            binary=binary,
            destination=Path(destination),
            cookies=cookies,
        )
        job = DownloadJob(job_id, url, destination, runner, None)
        job.set_runner(runner)
        if on_event is not None:
            job.set_event_sink(on_event)
        return job


class SourceRegistry:
    """Список источников: первый подходящий побеждает."""

    def __init__(self, sources: list[DownloadSource] | None = None) -> None:
        chosen = DEFAULT_SOURCES if sources is None else sources
        self._sources: list[DownloadSource] = list(chosen)

    @property
    def sources(self) -> tuple[DownloadSource, ...]:
        return tuple(self._sources)

    def register(self, source: DownloadSource) -> None:
        """Добавить источник (например, YouTube в будущем)."""
        self._sources.append(source)

    def find(self, url: str) -> DownloadSource | None:
        """Источник, который умеет работать со ссылкой, или None."""
        for source in self._sources:
            if source.matches(url):
                return source
        return None

    def describe(self, url: str) -> SourceInfo | None:
        """Сведения о ссылке от подходящего источника, или None."""
        source = self.find(url)
        if source is None:
            return None
        return source.describe(url)


DEFAULT_SOURCES: list[DownloadSource] = [PinterestSource()]
