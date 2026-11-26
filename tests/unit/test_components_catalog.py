"""Каталог компонентов: пять компонентов, у каждого свой способ установки."""

from __future__ import annotations

from snipnest.components.catalog import (
    COMPONENTS,
    ComponentKind,
    ComponentSpec,
    component_by_id,
)


def _version_parts(version: str) -> tuple[int, ...]:
    """Версия как набор чисел: «2026.11.23» → (2026, 11, 23)."""
    return tuple(int(part) for part in version.split("."))


def _pinned_version(spec: ComponentSpec) -> str:
    """Версия, закреплённая за компонентом."""
    return spec.packages[0].split("==")[-1]


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


def test_закреплённая_версия_yt_dlp_не_ниже_исправленной() -> None:
    """R3: в 2026.11.23 исправлен n challenge — на прежней версии форматов нет.

    YouTube отдаёт ролику только картинки, а yt-dlp пишет «Requested format is
    not available»: сломанная версия молча ломает загрузку видео. Откат на неё
    должен падать здесь, а не на приёме у владельца.
    """
    spec = component_by_id("yt-dlp")
    assert spec is not None
    assert _version_parts(_pinned_version(spec)) >= (2026, 11, 23)


def test_версия_скриптов_задачи_остаётся_прежней() -> None:
    """R3: yt-dlp 2026.11.23 работает со скриптами 0.8.0 — менять их не нужно."""
    spec = component_by_id("yt-dlp-ejs")
    assert spec is not None
    assert spec.packages == ("yt-dlp-ejs==0.8.0",)
