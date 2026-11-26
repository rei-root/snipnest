"""Форматы сохранения: что приложение предлагает выбрать владельцу.

Выбор делается до старта загрузки и определяет, что окажется на диске:
картинку — в каком файле она сохранится, видео — в каком контейнере.
"""

from __future__ import annotations

import dataclasses
import enum

__all__ = [
    "AUDIO_FORMATS",
    "AudioFormat",
    "CONVERTIBLE_EXTENSIONS",
    "DEFAULT_AUDIO",
    "DEFAULT_AUDIO_FORMAT",
    "DEFAULT_IMAGE",
    "DEFAULT_IMAGE_FORMAT",
    "DEFAULT_VIDEO",
    "DEFAULT_VIDEO_FORMAT",
    "FormatKind",
    "IMAGE_FORMATS",
    "ImageFormat",
    "SaveFormat",
    "VIDEO_FORMATS",
    "VideoFormat",
    "audio_format_by_id",
    "image_format_by_id",
    "video_format_by_id",
]


class FormatKind(enum.Enum):
    """Что выбирает владелец: формат картинки или формат видео."""

    IMAGE = "image"
    VIDEO = "video"


@dataclasses.dataclass(frozen=True)
class ImageFormat:
    """Формат картинки: расширение файла на диске.

    Пустое расширение — «как скачано»: файл сохраняется без перекодировки.
    """

    id: str
    title: str
    extension: str


@dataclasses.dataclass(frozen=True)
class VideoFormat:
    """Формат видео: как yt-dlp должен скачать ролик.

    ``selector`` — выражение ``-f``. ``merge_output`` — контейнер склейки
    (``--merge-output-format``). ``extract_audio`` — звук вытаскивается из
    ролика (``-x``). ``audio_selector`` — звуковой поток отдельным файлом:
    видео и звук скачиваются двумя запусками.
    """

    id: str
    title: str
    selector: str
    merge_output: str | None = None
    extract_audio: bool = False
    audio_selector: str | None = None

    @property
    def separate(self) -> bool:
        """Видео и звук — отдельными файлами."""
        return self.audio_selector is not None


@dataclasses.dataclass(frozen=True)
class AudioFormat:
    """Формат звука: во что переводить звуковой поток."""

    id: str
    title: str
    extension: str


DEFAULT_IMAGE = ImageFormat("original", "Как скачано (без перекодировки)", "")
DEFAULT_VIDEO = VideoFormat(
    "mp4",
    "MP4 — видео со звуком (H.264 + AAC)",
    "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
    merge_output="mp4",
)
DEFAULT_AUDIO = AudioFormat("mp3", "MP3 (.mp3)", "mp3")

IMAGE_FORMATS: tuple[ImageFormat, ...] = (
    DEFAULT_IMAGE,
    ImageFormat("jpg", "JPEG (.jpg)", "jpg"),
    ImageFormat("png", "PNG (.png)", "png"),
    ImageFormat("webp", "WebP (.webp)", "webp"),
)

VIDEO_FORMATS: tuple[VideoFormat, ...] = (
    DEFAULT_VIDEO,
    VideoFormat(
        "webm",
        "WebM — видео со звуком (VP9 + Opus)",
        "bv*[ext=webm]+ba[ext=webm]/b[ext=webm]/bv*+ba",
        merge_output="webm",
    ),
    VideoFormat(
        "mkv",
        "MKV — видео со звуком (любые кодеки)",
        "bv*+ba/b",
        merge_output="mkv",
    ),
    VideoFormat(
        "audio",
        "Только звук — извлечь из видео",
        "ba/b",
        extract_audio=True,
    ),
    VideoFormat(
        "separate",
        "Видео и звук — отдельными файлами",
        "bv*",
        audio_selector="ba",
    ),
)

AUDIO_FORMATS: tuple[AudioFormat, ...] = (
    DEFAULT_AUDIO,
    AudioFormat("m4a", "M4A (.m4a)", "m4a"),
    AudioFormat("opus", "Opus (.opus)", "opus"),
    AudioFormat("flac", "FLAC (.flac)", "flac"),
    AudioFormat("wav", "WAV (.wav)", "wav"),
)

DEFAULT_IMAGE_FORMAT = DEFAULT_IMAGE.id
DEFAULT_VIDEO_FORMAT = DEFAULT_VIDEO.id
DEFAULT_AUDIO_FORMAT = DEFAULT_AUDIO.id

#: Расширения, которые перекодируются в выбранный формат. GIF сюда не входит:
#: от анимированной картинки остался бы один кадр.
CONVERTIBLE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"})


def image_format_by_id(format_id: str) -> ImageFormat | None:
    """Формат картинки по идентификатору или None, если такого нет."""
    for fmt in IMAGE_FORMATS:
        if fmt.id == format_id:
            return fmt
    return None


def video_format_by_id(format_id: str) -> VideoFormat | None:
    """Формат видео по идентификатору или None, если такого нет."""
    for fmt in VIDEO_FORMATS:
        if fmt.id == format_id:
            return fmt
    return None


def audio_format_by_id(format_id: str) -> AudioFormat | None:
    """Формат звука по идентификатору или None, если такого нет."""
    for fmt in AUDIO_FORMATS:
        if fmt.id == format_id:
            return fmt
    return None


@dataclasses.dataclass(frozen=True)
class SaveFormat:
    """Выбор владельца для одной загрузки.

    Вид выбора (``kind``) известен по ссылке: картинка или видео. Сами
    форматы хранятся объектами — так выбор нельзя испортить неверным id.
    """

    kind: FormatKind = FormatKind.IMAGE
    image: ImageFormat = DEFAULT_IMAGE
    video: VideoFormat = DEFAULT_VIDEO
    audio: AudioFormat = DEFAULT_AUDIO
