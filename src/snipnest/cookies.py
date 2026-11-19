"""Источники cookies для YouTube: браузеры в системе и файл cookies.txt.

Приложение cookies не читает и не хранит: оно только говорит yt-dlp, откуда
их взять — из браузера владельца или из файла, который владелец выгрузил сам.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

__all__ = [
    "BROWSERS",
    "CookieSource",
    "detect_browser_sources",
    "file_source",
]

#: Браузеры, которые умеет читать yt-dlp: имя для него, название для
#: человека и путь к каталогу профиля относительно домашнего каталога.
BROWSERS: tuple[tuple[str, str, str], ...] = (
    ("firefox", "Firefox", ".mozilla/firefox"),
    ("chrome", "Google Chrome", ".config/google-chrome"),
    ("chromium", "Chromium", ".config/chromium"),
    ("brave", "Brave", ".config/BraveSoftware/Brave-Browser"),
    ("edge", "Microsoft Edge", ".config/microsoft-edge"),
    ("opera", "Opera", ".config/opera"),
    ("vivaldi", "Vivaldi", ".config/vivaldi"),
)


@dataclasses.dataclass(frozen=True)
class CookieSource:
    """Источник cookies: что приложение отдаст yt-dlp.

    ``browser`` — значение для ``--cookies-from-browser`` (для Firefox с
    профилем это ``firefox:<профиль>``), ``path`` — значение для ``--cookies``.
    """

    label: str
    browser: str = ""
    path: str = ""


def _firefox_sources(directory: Path) -> list[CookieSource]:
    """Профили Firefox: у каждого свой каталог с cookies.sqlite.

    Профиль указывать надо: без него yt-dlp берёт самый свежий cookies.sqlite
    из всех профилей, и вход может оказаться не в том.
    """
    if not directory.is_dir():
        return []
    result: list[CookieSource] = []
    for profile in sorted(directory.iterdir()):
        if profile.is_dir() and (profile / "cookies.sqlite").is_file():
            result.append(
                CookieSource(
                    label=f"Firefox ({profile.name})",
                    browser=f"firefox:{profile.name}",
                )
            )
    return result


def detect_browser_sources(home: Path | None = None) -> list[CookieSource]:
    """Источники cookies из браузеров, найденных в системе."""
    base = home if home is not None else Path.home()
    sources: list[CookieSource] = []
    for name, title, relative in BROWSERS:
        directory = base / relative
        if name == "firefox":
            sources.extend(_firefox_sources(directory))
        elif directory.is_dir():
            sources.append(CookieSource(label=title, browser=name))
    return sources


def file_source(path: str) -> CookieSource:
    """Источник cookies из файла в формате Netscape."""
    label = "Файл cookies.txt"
    if path:
        label = f"Файл cookies.txt ({Path(path).name})"
    return CookieSource(label=label, path=path)
