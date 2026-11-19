"""Тесты определения типа ссылки Pinterest."""

from __future__ import annotations

import pytest

from snipnest.links import LinkKind, classify_link, is_valid_link


@pytest.mark.parametrize(
    "url",
    [
        "https://www.pinterest.ru/pin/978758931539448360/",
        "https://www.pinterest.com/pin/978758931539448360/sent/",
        "https://ru.pinterest.com/pin/12345/",
    ],
)
def test_прямая_ссылка_на_картинку(url: str) -> None:
    info = classify_link(url)
    assert info.kind is LinkKind.PIN
    assert info.pin_id is not None


@pytest.mark.parametrize(
    "url",
    [
        "https://www.pinterest.ru/formaruslan59/персонажи-аниме/",
        "https://www.pinterest.com/user/board-name/",
    ],
)
def test_прямая_ссылка_на_альбом(url: str) -> None:
    info = classify_link(url)
    assert info.kind is LinkKind.BOARD
    assert info.board_path is not None


@pytest.mark.parametrize(
    "url",
    [
        "https://pin.it/63u8RKqUi",
        "https://pin.it/1XDOXXNny",
    ],
)
def test_короткая_ссылка_не_различается_по_виду(url: str) -> None:
    """Вид короткой ссылки определяет сам gallery-dl, а не разбор URL."""
    info = classify_link(url)
    assert info.kind is LinkKind.UNKNOWN


def test_мусор_не_является_ссылкой() -> None:
    assert classify_link("просто текст").kind is LinkKind.UNKNOWN
    assert classify_link("https://example.com/pin/1/").kind is LinkKind.UNKNOWN


def test_проверка_валидности_ссылки() -> None:
    assert is_valid_link("https://pin.it/63u8RKqUi")
    assert is_valid_link("https://www.pinterest.ru/pin/1/")
    assert not is_valid_link("https://example.com/")
    assert not is_valid_link("")
    assert not is_valid_link("pin.it/63u8RKqUi")


def test_пробелы_вокруг_ссылки_отбрасываются() -> None:
    info = classify_link("  https://www.pinterest.ru/pin/978758931539448360/  ")
    assert info.kind is LinkKind.PIN
