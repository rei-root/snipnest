"""Разбор ссылок YouTube: обычное видео, короткая ссылка, Shorts.

Модуль чистый: ни одной сетевой проверки, только разбор URL.
"""

from __future__ import annotations

from snipnest.youtube import YouTubeLinkKind, parse_youtube_link

VIDEO_ID = "dQw4w9WgXcQ"


def test_обычное_видео_распознаётся() -> None:
    link = parse_youtube_link(f"https://www.youtube.com/watch?v={VIDEO_ID}")
    assert link is not None
    assert link.video_id == VIDEO_ID
    assert link.kind is YouTubeLinkKind.VIDEO


def test_короткая_ссылка_распознаётся() -> None:
    link = parse_youtube_link(f"https://youtu.be/{VIDEO_ID}")
    assert link is not None
    assert link.video_id == VIDEO_ID
    assert link.kind is YouTubeLinkKind.VIDEO


def test_шортс_распознаётся() -> None:
    link = parse_youtube_link(f"https://www.youtube.com/shorts/{VIDEO_ID}")
    assert link is not None
    assert link.video_id == VIDEO_ID
    assert link.kind is YouTubeLinkKind.SHORTS


def test_прямая_трансляция_и_вставка_распознаются() -> None:
    live = parse_youtube_link(f"https://www.youtube.com/live/{VIDEO_ID}")
    embed = parse_youtube_link(f"https://www.youtube.com/embed/{VIDEO_ID}")
    assert live is not None
    assert embed is not None
    assert live.video_id == VIDEO_ID
    assert embed.video_id == VIDEO_ID


def test_мобильная_версия_и_плейлист_в_ссылке_распознаются() -> None:
    mobile = parse_youtube_link(f"https://m.youtube.com/watch?v={VIDEO_ID}")
    with_playlist = parse_youtube_link(f"https://www.youtube.com/watch?v={VIDEO_ID}&list=PL123")
    assert mobile is not None
    assert with_playlist is not None
    assert with_playlist.video_id == VIDEO_ID


def test_чужой_сайт_не_распознаётся() -> None:
    assert parse_youtube_link("https://example.com/watch?v=dQw4w9WgXcQ") is None
    assert parse_youtube_link("https://pin.it/abc") is None
    assert parse_youtube_link("https://www.tiktok.com/@user/video/1234567890") is None
    assert parse_youtube_link("") is None


def test_плейлист_не_видео() -> None:
    """Ссылка на плейлист — не видео: плейлисты в задачу не входят."""
    assert parse_youtube_link("https://www.youtube.com/playlist?list=PL123") is None


def test_канал_и_домашняя_страница_не_видео() -> None:
    assert parse_youtube_link("https://www.youtube.com/@somechannel") is None
    assert parse_youtube_link("https://www.youtube.com/") is None
