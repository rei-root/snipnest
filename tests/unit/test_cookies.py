"""Источники cookies для YouTube: браузеры в системе и файл cookies.txt.

Приложение cookies не читает и не хранит: оно только говорит yt-dlp, откуда
их взять.
"""

from __future__ import annotations

from pathlib import Path

from snipnest.cookies import detect_browser_sources, file_source


def make_home(tmp_path: Path) -> Path:
    """Домашний каталог с двумя профилями Firefox и каталогом Chrome."""
    firefox = tmp_path / ".mozilla" / "firefox"
    for profile in ("abc.default-release", "def.default-esr"):
        directory = firefox / profile
        directory.mkdir(parents=True)
        (directory / "cookies.sqlite").write_bytes(b"")
    chrome = tmp_path / ".config" / "google-chrome"
    chrome.mkdir(parents=True)
    return tmp_path


def test_находятся_профили_firefox(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    sources = detect_browser_sources(home)
    labels = [source.label for source in sources]
    assert "Firefox (abc.default-release)" in labels
    assert "Firefox (def.default-esr)" in labels


def test_значение_для_yt_dlp_содержит_профиль(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    sources = detect_browser_sources(home)
    values = [source.browser for source in sources]
    assert "firefox:abc.default-release" in values
    assert "firefox:def.default-esr" in values


def test_находится_браузер_без_профилей(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    sources = detect_browser_sources(home)
    assert "chrome" in [source.browser for source in sources]


def test_неустановленные_браузеры_не_предлагаются(tmp_path: Path) -> None:
    sources = detect_browser_sources(tmp_path)
    assert sources == []


def test_профиль_без_cookies_sqlite_не_считается(tmp_path: Path) -> None:
    firefox = tmp_path / ".mozilla" / "firefox" / "empty.profile"
    firefox.mkdir(parents=True)
    assert detect_browser_sources(tmp_path) == []


def test_источник_из_файла() -> None:
    source = file_source("/home/sato/cookies.txt")
    assert source.path == "/home/sato/cookies.txt"
    assert source.browser == ""
    assert "cookies.txt" in source.label


def test_источник_из_файла_без_пути() -> None:
    source = file_source("")
    assert source.path == ""
