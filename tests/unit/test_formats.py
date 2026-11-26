"""Форматы сохранения: что приложение предлагает выбрать владельцу.

Требования, которые закрывают эти проверки:

* R3 — требования: список форматов картинки и видео, умолчания, поиск по id;
* R4 — бизнес-правила: умолчания прежние, выбора качества видео нет.
"""

from __future__ import annotations

from snipnest.formats import (
    AUDIO_FORMATS,
    DEFAULT_AUDIO_FORMAT,
    DEFAULT_IMAGE_FORMAT,
    DEFAULT_VIDEO_FORMAT,
    IMAGE_FORMATS,
    VIDEO_FORMATS,
    FormatKind,
    SaveFormat,
    audio_format_by_id,
    image_format_by_id,
    video_format_by_id,
)


def test_форматы_картинки_перечислены() -> None:
    """R3: картинку можно сохранить как есть, в JPEG, PNG или WebP."""
    assert [fmt.id for fmt in IMAGE_FORMATS] == ["original", "jpg", "png", "webp"]
    assert [fmt.extension for fmt in IMAGE_FORMATS] == ["", "jpg", "png", "webp"]


def test_форматы_видео_перечислены() -> None:
    """R3: видео — три контейнера, «только звук» и раздельные файлы."""
    assert [fmt.id for fmt in VIDEO_FORMATS] == ["mp4", "webm", "mkv", "audio", "separate"]


def test_форматы_звука_перечислены() -> None:
    """R3: для «только звук» — свой список форматов."""
    assert [fmt.id for fmt in AUDIO_FORMATS] == ["mp3", "m4a", "opus", "flac", "wav"]


def test_умолчания_прежние() -> None:
    """R4: картинка — как скачано, видео — MP4 со звуком."""
    assert DEFAULT_IMAGE_FORMAT == "original"
    assert DEFAULT_VIDEO_FORMAT == "mp4"
    assert DEFAULT_AUDIO_FORMAT == "mp3"


def test_поиск_формата_по_идентификатору() -> None:
    """R3: формат ищется по id, неизвестного id нет."""
    assert image_format_by_id("webp") is not None
    assert video_format_by_id("webm") is not None
    assert audio_format_by_id("flac") is not None
    assert image_format_by_id("tiff") is None
    assert video_format_by_id("1080p") is None
    assert audio_format_by_id("aiff") is None


def test_выбора_качества_видео_нет() -> None:
    """R6: ручной выбор разрешения и качества — вне задачи."""
    assert all("1080" not in fmt.title for fmt in VIDEO_FORMATS)
    assert all("720" not in fmt.title for fmt in VIDEO_FORMATS)


def test_формат_по_умолчанию_для_картинки_ничего_не_перекодирует() -> None:
    """R4: «как скачано» — пустое расширение, перекодировки нет."""
    chosen = image_format_by_id(DEFAULT_IMAGE_FORMAT)
    assert chosen is not None
    assert chosen.extension == ""


def test_выбор_владельца_хранит_вид_и_форматы() -> None:
    """R3: выбор — это вид (картинка или видео) и сами форматы."""
    chosen = SaveFormat(
        kind=FormatKind.VIDEO,
        video=video_format_by_id("webm"),  # type: ignore[arg-type]
        audio=audio_format_by_id("opus"),  # type: ignore[arg-type]
    )
    assert chosen.kind is FormatKind.VIDEO
    assert chosen.video.id == "webm"
    assert chosen.audio.id == "opus"
