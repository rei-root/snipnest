"""Слой источников: абстракция сайта и конкретные реализации.

UI не знает, с какого сайта пришла ссылка. Он спрашивает реестр источников,
какой источник умеет работать со ссылкой, и получает от него готовую
загрузку с нужным исполнителем. Добавление нового источника — это новый
класс в этом модуле и одна строка в реестре, правки UI не требуют.

Источник отвечает и за свой бинарник: Pinterest работает через gallery-dl,
YouTube — через yt-dlp, у каждого свой путь в настройках.
"""

from __future__ import annotations

import dataclasses
import enum
from collections.abc import Callable
from pathlib import Path

from .binaries import find_gallery_dl, find_yt_dlp
from .downloader import DownloadRunner, GalleryDlRunner, ImageConverter
from .formats import SaveFormat
from .jobs import DownloadJob, JobEvent
from .links import LinkInfo, LinkKind, classify_link, is_valid_link
from .settings import Settings
from .youtube import parse_youtube_link
from .ytdlp import YtDlpRunner

__all__ = [
    "SourceKind",
    "SourceInfo",
    "SourceBinary",
    "DownloadSource",
    "PinterestSource",
    "YouTubeSource",
    "SourceRegistry",
    "DEFAULT_SOURCES",
]


class SourceKind(enum.Enum):
    """Вид источника: откуда приходит ссылка."""

    PINTEREST = "pinterest"
    YOUTUBE = "youtube"


@dataclasses.dataclass(frozen=True)
class SourceInfo:
    """Что источник умеет рассказать о ссылке."""

    kind: SourceKind
    title: str
    link_kind: LinkKind
    url: str
    pin_id: str | None = None
    board_path: str | None = None
    video_id: str | None = None

    @property
    def is_single_image(self) -> bool:
        """True, если ссылка ведёт на одну картинку."""
        return self.link_kind is LinkKind.PIN

    @property
    def is_album(self) -> bool:
        """True, если ссылка ведёт на альбом."""
        return self.link_kind is LinkKind.BOARD


@dataclasses.dataclass(frozen=True)
class SourceBinary:
    """Бинарник, которым работает источник.

    ``setting`` — имя настройки с путём к бинарнику: путь, который владелец
    указал сам (пусто — искать в PATH).
    """

    name: str
    setting: str


class DownloadSource:
    """Источник загрузок.

    Подкласс отвечает за две вещи: узнать свою ссылку и собрать из неё
    готовую загрузку с нужным исполнителем. Общий код (UI, настройки,
    очерёдность) о нём не знает.
    """

    kind: SourceKind
    title: str
    binary: SourceBinary

    def matches(self, url: str) -> bool:
        """True, если источник умеет работать с этой ссылкой."""
        raise NotImplementedError

    def describe(self, url: str) -> SourceInfo:
        """Разобрать ссылку и вернуть сведения о ней."""
        raise NotImplementedError

    def directory_formats(self, file_count: int) -> list[str]:
        """Шаблоны каталогов внутри выбранной папки — по числу файлов.

        По умолчанию файлы кладутся прямо в выбранную папку: никаких своих
        подкаталогов приложение не заводит.
        """
        return [""]

    def binary_path(self, settings: Settings) -> str | None:
        """Путь к бинарнику, указанный владельцем в настройках."""
        return getattr(settings, self.binary.setting, "") or None

    def find_binary(self, settings: Settings) -> str | None:
        """Рабочий путь к бинарнику источника или None, если его нет."""
        raise NotImplementedError

    def missing_binary_message(self, settings: Settings) -> str | None:
        """Сообщение о нехватке бинарника или None, если всё в порядке."""
        if self.find_binary(settings) is not None:
            return None
        path = self.binary_path(settings)
        if path:
            return (
                f"{self.binary.name} не найден по пути {path}. "
                "Укажите правильный путь в настройках."
            )
        return (
            f"{self.binary.name} не найден в PATH. "
            "Установите его или укажите путь к бинарнику вручную."
        )

    def build_job(
        self,
        job_id: str,
        url: str,
        destination: str,
        settings: Settings,
        on_event: Callable[[JobEvent], None] | None = None,
        save_format: SaveFormat | None = None,
        converter: ImageConverter | None = None,
    ) -> DownloadJob:
        """Собрать загрузку для этой ссылки.

        Источник сам берёт из настроек всё, что ему нужно: путь к своему
        бинарнику и, если уместно, источник cookies.

        ``save_format`` — выбор владельца: в каком виде сохранять файлы.
        ``converter`` — функция перевода картинки; её знает только слой
        интерфейса, поэтому она подставляется снаружи.
        """
        raise NotImplementedError

    def _finish_job(
        self,
        job_id: str,
        url: str,
        destination: str,
        runner: DownloadRunner,
        on_event: Callable[[JobEvent], None] | None,
    ) -> DownloadJob:
        """Оформить загрузку: подключить исполнителя и подписчика событий."""
        job = DownloadJob(job_id, url, destination, runner, None)
        job.set_runner(runner)
        if on_event is not None:
            job.set_event_sink(on_event)
        return job


class PinterestSource(DownloadSource):
    """Pinterest: картинка (pin) или альбом (board)."""

    kind = SourceKind.PINTEREST
    title = "Pinterest"
    binary = SourceBinary("gallery-dl", "gallery_dl_path")

    #: Папка альбома: название доски из данных Pinterest. Модификатор ``?//``
    #: оставляет поле пустым, если доски нет, — тогда файлы лягут прямо в
    #: выбранную папку.
    ALBUM_DIRECTORY = "{board[name]:?//}"

    def matches(self, url: str) -> bool:
        return is_valid_link(url)

    def find_binary(self, settings: Settings) -> str | None:
        return find_gallery_dl(self.binary_path(settings))

    def directory_formats(self, file_count: int) -> list[str]:
        """Картинка — прямо в выбранную папку, альбом — в папку с названием.

        Различаем по числу файлов: его приложение уже знает из
        предварительного прохода, который нужен для счётчика «скачано X из Y».
        """
        if file_count > 1:
            return [self.ALBUM_DIRECTORY]
        return [""]

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
        settings: Settings,
        on_event: Callable[[JobEvent], None] | None = None,
        save_format: SaveFormat | None = None,
        converter: ImageConverter | None = None,
    ) -> DownloadJob:
        image_extension = ""
        if save_format is not None:
            image_extension = save_format.image.extension
        runner = GalleryDlRunner(
            binary=self.binary_path(settings),
            destination=Path(destination),
            directory_formats=self.directory_formats,
            image_extension=image_extension,
            converter=converter,
        )
        return self._finish_job(job_id, url, destination, runner, on_event)


class YouTubeSource(DownloadSource):
    """YouTube: видео — обычное, короткая ссылка или Shorts."""

    kind = SourceKind.YOUTUBE
    title = "YouTube"
    binary = SourceBinary("yt-dlp", "yt_dlp_path")

    def matches(self, url: str) -> bool:
        return parse_youtube_link(url) is not None

    def find_binary(self, settings: Settings) -> str | None:
        return find_yt_dlp(self.binary_path(settings))

    def directory_formats(self, file_count: int) -> list[str]:
        """Видео — прямо в выбранную папку, без своих подкаталогов."""
        return [""]

    def describe(self, url: str) -> SourceInfo:
        link = parse_youtube_link(url)
        video_id = link.video_id if link is not None else ""
        return SourceInfo(
            kind=self.kind,
            title=self.title,
            link_kind=LinkKind.VIDEO,
            url=url,
            video_id=video_id,
        )

    def build_job(
        self,
        job_id: str,
        url: str,
        destination: str,
        settings: Settings,
        on_event: Callable[[JobEvent], None] | None = None,
        save_format: SaveFormat | None = None,
        converter: ImageConverter | None = None,
    ) -> DownloadJob:
        video_format = None
        audio_format = None
        if save_format is not None:
            video_format = save_format.video
            audio_format = save_format.audio
        runner = YtDlpRunner(
            binary=self.binary_path(settings),
            destination=Path(destination),
            cookies_file=settings.cookies_file or None,
            cookies_browser=settings.cookies_browser or None,
            video_format=video_format,
            audio_format=audio_format,
        )
        return self._finish_job(job_id, url, destination, runner, on_event)


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


DEFAULT_SOURCES: list[DownloadSource] = [PinterestSource(), YouTubeSource()]
