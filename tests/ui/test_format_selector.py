"""Выбор формата сохранения: что приложение предлагает владельцу.

Требования, которые закрывают эти проверки:

* R3 — требования: список форматов зависит от вида ссылки, список звука
  доступен только для варианта «только звук», выбранное возвращается выборкой;
* R8 — последний выбор помнится: при переключении вида ссылки он не теряется.
"""

from __future__ import annotations

from snipnest.formats import FormatKind
from snipnest.ui.format_selector import FormatSelector


def test_для_фото_показываются_форматы_картинки(qtbot) -> None:
    """R3: у картинки — свой список форматов."""
    selector = FormatSelector()
    qtbot.addWidget(selector)

    selector.set_kind(FormatKind.IMAGE)

    assert selector.format_ids() == ["original", "jpg", "png", "webp"]


def test_для_видео_показываются_форматы_видео(qtbot) -> None:
    """R3: у видео — свой список форматов."""
    selector = FormatSelector()
    qtbot.addWidget(selector)

    selector.set_kind(FormatKind.VIDEO)

    assert selector.format_ids() == ["mp4", "webm", "mkv", "audio", "separate"]


def test_список_звука_доступен_только_для_звука(qtbot) -> None:
    """R3: формат звука нужен только варианту «только звук»."""
    selector = FormatSelector()
    qtbot.addWidget(selector)
    selector.set_kind(FormatKind.VIDEO)

    assert selector.audio_enabled() is False

    selector.select_format("audio")

    assert selector.audio_enabled() is True
    assert selector.audio_ids() == ["mp3", "m4a", "opus", "flac", "wav"]


def test_выбранный_формат_возвращается_выборкой(qtbot) -> None:
    """R3: выбор владельца уходит в загрузку как объект формата."""
    selector = FormatSelector()
    qtbot.addWidget(selector)
    selector.set_kind(FormatKind.IMAGE)

    selector.select_format("webp")
    chosen = selector.selected_format()

    assert chosen.kind is FormatKind.IMAGE
    assert chosen.image.id == "webp"


def test_выбор_помнится_между_видами_ссылки(qtbot) -> None:
    """R8: переключение «фото — видео» не сбрасывает выбор."""
    selector = FormatSelector()
    qtbot.addWidget(selector)

    selector.set_kind(FormatKind.IMAGE)
    selector.select_format("png")
    selector.set_kind(FormatKind.VIDEO)
    selector.select_format("webm")

    selector.set_kind(FormatKind.IMAGE)
    assert selector.selected_format().image.id == "png"

    selector.set_kind(FormatKind.VIDEO)
    assert selector.selected_format().video.id == "webm"


def test_выбор_восстанавливается_из_настроек(qtbot) -> None:
    """R8: последний выбор хранится в настройках и возвращается при запуске."""
    selector = FormatSelector()
    qtbot.addWidget(selector)

    selector.set_choices(image_id="webp", video_id="mkv", audio_id="flac")

    selector.set_kind(FormatKind.IMAGE)
    assert selector.selected_format().image.id == "webp"

    selector.set_kind(FormatKind.VIDEO)
    chosen = selector.selected_format()
    assert chosen.video.id == "mkv"
    assert chosen.audio.id == "flac"


def test_смена_выбора_сообщает_об_этом(qtbot) -> None:
    """R8: приложение узнаёт о смене выбора и запоминает его."""
    selector = FormatSelector()
    qtbot.addWidget(selector)

    with qtbot.waitSignal(selector.changed):
        selector.select_format("png")
