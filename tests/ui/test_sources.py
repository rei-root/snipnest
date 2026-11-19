"""Тесты слоя источников: определение источника по ссылке."""

from __future__ import annotations

from snipnest.links import LinkKind
from snipnest.sources import (
    DownloadSource,
    PinterestSource,
    SourceKind,
    SourceRegistry,
    YouTubeSource,
)
from snipnest.ytdlp import YtDlpRunner


def test_источник_pinterest_узнаёт_свою_ссылку() -> None:
    source = PinterestSource()
    assert source.matches("https://pin.it/abc")
    assert source.matches("https://www.pinterest.com/pin/123456/")


def test_источник_pinterest_не_узнаёт_чужую_ссылку() -> None:
    source = PinterestSource()
    assert not source.matches("https://example.com/pin/123456/")


def test_описание_ссылки_определяет_картинку_и_альбом() -> None:
    source = PinterestSource()
    pin = source.describe("https://www.pinterest.com/pin/1234567890/")
    album = source.describe("https://www.pinterest.com/user/vasya/boards/hobbies/")

    assert pin.link_kind is LinkKind.PIN
    assert pin.is_single_image
    assert not pin.is_album

    assert album.link_kind is LinkKind.BOARD
    assert album.is_album
    assert not album.is_single_image


def test_реестр_находит_источник_по_ссылке() -> None:
    registry = SourceRegistry()
    assert registry.find("https://pin.it/abc") is not None
    assert registry.find("https://example.com/") is None


def test_в_реестр_можно_добавить_источник() -> None:
    class OtherSource(DownloadSource):
        kind = SourceKind.PINTEREST
        title = "Другой"

        def matches(self, url: str) -> bool:
            return url.startswith("https://other.example/")

    registry = SourceRegistry([PinterestSource()])
    registry.register(OtherSource())

    found = registry.find("https://other.example/thing")
    assert found is not None
    assert found.title == "Другой"


def test_описание_ссылки_через_реестр() -> None:
    registry = SourceRegistry()
    info = registry.describe("https://www.pinterest.com/pin/42/")
    assert info is not None
    assert info.kind is SourceKind.PINTEREST
    assert info.pin_id == "42"


def test_источник_youtube_узнаёт_свою_ссылку() -> None:
    source = YouTubeSource()
    assert source.matches("https://youtu.be/dQw4w9WgXcQ")
    assert source.matches("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert source.matches("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    assert not source.matches("https://pin.it/abc")


def test_описание_ссылки_youtube_даёт_идентификатор_видео() -> None:
    source = YouTubeSource()
    info = source.describe("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    assert info.kind is SourceKind.YOUTUBE
    assert info.video_id == "dQw4w9WgXcQ"
    assert info.link_kind is LinkKind.VIDEO


def test_задание_видео_собирает_загрузку_с_yt_dlp() -> None:
    source = YouTubeSource()
    job = source.build_job("job-1", "https://youtu.be/dQw4w9WgXcQ", "/tmp/out")
    assert job.url == "https://youtu.be/dQw4w9WgXcQ"
    assert job.destination == "/tmp/out"
    assert isinstance(job.runner, YtDlpRunner)


def test_источник_youtube_не_знает_про_плейлист() -> None:
    source = YouTubeSource()
    assert not source.matches("https://www.youtube.com/playlist?list=PL123")


def test_реестр_находит_youtube_по_ссылке() -> None:
    registry = SourceRegistry()
    found = registry.find("https://youtu.be/dQw4w9WgXcQ")
    assert found is not None
    assert found.kind is SourceKind.YOUTUBE
    assert registry.find("https://www.youtube.com/playlist?list=PL123") is None


def test_раскладка_youtube_кладёт_файл_прямо_в_выбранную_папку() -> None:
    source = YouTubeSource()
    assert source.directory_formats(1) == [""]
    assert source.directory_formats(2) == [""]


def test_описание_короткой_ссылки_youtube() -> None:
    source = YouTubeSource()
    info = source.describe("https://youtu.be/dQw4w9WgXcQ")
    assert info.video_id == "dQw4w9WgXcQ"
    assert info.link_kind is LinkKind.VIDEO
