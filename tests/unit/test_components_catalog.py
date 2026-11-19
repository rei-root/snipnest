"""Каталог компонентов: пять компонентов, у каждого свой способ установки."""

from __future__ import annotations

from snipnest.components.catalog import (
    COMPONENTS,
    ComponentKind,
    component_by_id,
)


def test_в_каталоге_пять_компонентов() -> None:
    assert len(COMPONENTS) == 5


def test_идентификаторы_компонентов_уникальны() -> None:
    ids = [spec.id for spec in COMPONENTS]
    assert len(set(ids)) == len(ids)


def test_состав_компонентов_согласован_с_ожиданием() -> None:
    assert [spec.id for spec in COMPONENTS] == [
        "gallery-dl",
        "yt-dlp",
        "yt-dlp-ejs",
        "deno",
        "ffmpeg",
    ]


def test_питоновские_компоненты_ставятся_пакетами() -> None:
    for spec in COMPONENTS:
        if spec.kind is ComponentKind.PIP:
            assert spec.packages, f"{spec.id}: нет ни одного пакета"
            assert spec.module, f"{spec.id}: не указан модуль"
        else:
            assert spec.url.startswith("https://"), f"{spec.id}: нет адреса"
            assert spec.sha256, f"{spec.id}: нет контрольной суммы"


def test_у_бинарных_компонентов_указан_запускаемый_файл() -> None:
    for spec in COMPONENTS:
        if spec.kind is ComponentKind.ARCHIVE:
            assert spec.binary, f"{spec.id}: не указан исполняемый файл"


def test_компонент_находится_по_идентификатору() -> None:
    spec = component_by_id("gallery-dl")
    assert spec is not None
    assert spec.id == "gallery-dl"


def test_неизвестный_компонент_не_находится() -> None:
    assert component_by_id("нет-такого") is None


def test_yt_dlp_видит_каталог_yt_dlp_ejs() -> None:
    """Скрипты задачи лежат рядом: yt-dlp должен импортировать yt_dlp_ejs."""
    spec = component_by_id("yt-dlp")
    assert spec is not None
    assert "yt-dlp-ejs" in spec.extra_paths
