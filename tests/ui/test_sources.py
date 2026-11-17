"""Тесты слоя источников: определение источника по ссылке."""

from __future__ import annotations

from gallary_downloader.links import LinkKind
from gallary_downloader.sources import (
    DownloadSource,
    PinterestSource,
    SourceKind,
    SourceRegistry,
)


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
