"""Поиск установленных компонентов: каталог пользователя, пакет системы, PATH."""

from __future__ import annotations

from pathlib import Path

from snipnest.components.catalog import ComponentKind, ComponentSpec
from snipnest.components.finder import find_component, find_component_by_id

GALLERY_DL = ComponentSpec(
    id="gallery-dl",
    title="gallery-dl",
    description="Скачивание из Pinterest",
    kind=ComponentKind.PIP,
    binary="gallery-dl",
    module="gallery_dl",
    packages=("gallery-dl==1.32.20",),
)

DENO = ComponentSpec(
    id="deno",
    title="deno",
    description="JS-рантайм",
    kind=ComponentKind.ARCHIVE,
    binary="deno",
    url="https://example.invalid/deno.zip",
    sha256="0" * 64,
)


def _make_pip_component(root: Path, component_id: str, module: str) -> None:
    package = root / component_id / module
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")


def _make_binary_component(root: Path, component_id: str, binary: str) -> Path:
    folder = root / component_id / "bin"
    folder.mkdir(parents=True)
    path = folder / binary
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    return path


def test_компонент_найден_в_каталоге_пользователя(tmp_path) -> None:
    user_root = tmp_path / "user"
    system_root = tmp_path / "system"
    _make_pip_component(user_root, "gallery-dl", "gallery_dl")

    location = find_component(GALLERY_DL, user_root=user_root, system_root=system_root)

    assert location is not None
    assert location.source == "user"
    assert location.path == user_root / "gallery-dl" / "gallery_dl"


def test_каталог_системы_используется_когда_нет_пользовательского(tmp_path) -> None:
    user_root = tmp_path / "user"
    system_root = tmp_path / "system"
    _make_pip_component(system_root, "gallery-dl", "gallery_dl")

    location = find_component(GALLERY_DL, user_root=user_root, system_root=system_root)

    assert location is not None
    assert location.source == "system"


def test_пользовательский_каталог_важнее_системного(tmp_path) -> None:
    user_root = tmp_path / "user"
    system_root = tmp_path / "system"
    _make_pip_component(user_root, "gallery-dl", "gallery_dl")
    _make_pip_component(system_root, "gallery-dl", "gallery_dl")

    location = find_component(GALLERY_DL, user_root=user_root, system_root=system_root)

    assert location is not None
    assert location.source == "user"


def test_бинарный_компонент_найден_по_файлу(tmp_path) -> None:
    user_root = tmp_path / "user"
    system_root = tmp_path / "system"
    expected = _make_binary_component(user_root, "deno", "deno")

    location = find_component(DENO, user_root=user_root, system_root=system_root)

    assert location is not None
    assert location.source == "user"
    assert location.path == expected


def test_компонент_не_найден_в_пустых_каталогах(tmp_path) -> None:
    location = find_component(
        DENO,
        user_root=tmp_path / "user",
        system_root=tmp_path / "system",
    )

    assert location is None


def test_поиск_по_идентификатору_берёт_компонент_из_каталога(tmp_path) -> None:
    user_root = tmp_path / "user"
    _make_pip_component(user_root, "gallery-dl", "gallery_dl")

    location = find_component_by_id(
        "gallery-dl", user_root=user_root, system_root=tmp_path / "system"
    )

    assert location is not None
    assert location.source == "user"


def test_поиск_неизвестного_идентификатора_даёт_пусто(tmp_path) -> None:
    location = find_component_by_id(
        "нет-такого",
        user_root=tmp_path / "user",
        system_root=tmp_path / "system",
    )

    assert location is None
