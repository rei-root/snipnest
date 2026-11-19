"""Установка компонентов: pip-пакеты, архивы и проверка контрольной суммы."""

from __future__ import annotations

import hashlib
import os
import stat
import zipfile
from pathlib import Path

from snipnest.components.catalog import ComponentKind, ComponentSpec
from snipnest.components.installer import ComponentInstaller

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
    description="JS-рантайм для скриптов задачи",
    kind=ComponentKind.ARCHIVE,
    binary="deno",
    url="https://example.invalid/deno.zip",
    sha256="0" * 64,
)


def _fake_python(tmp_path: Path) -> Path:
    """Поддельный интерпретатор: делает вид, что поставил пакет."""
    script = tmp_path / "fake-python"
    script.write_text(
        "#!/bin/sh\n"
        'target=""\n'
        'for arg in "$@"; do\n'
        '  case "$arg" in\n'
        "    --target) next=1 ;;\n"
        '    *) if [ "$next" = "1" ]; then target="$arg"; next=0; fi ;;\n'
        "  esac\n"
        "done\n"
        'mkdir -p "$target/gallery_dl"\n'
        'printf "VERSION = 1.32.20\\n" > "$target/gallery_dl/__init__.py"\n'
        "exit 0\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _zip_with_binary(tmp_path: Path) -> Path:
    archive = tmp_path / "deno.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("deno", "#!/bin/sh\necho 2.9.8\n")
    return archive


def _downloader_of(archive: Path):
    """Поддельная загрузка: кладёт содержимое архива в целевой файл."""

    def download(url: str, target: Path) -> None:
        target.write_bytes(archive.read_bytes())

    return download


def test_установка_питоновского_пакета_создаёт_каталог_компонента(tmp_path) -> None:
    root = tmp_path / "components"
    installer = ComponentInstaller(python=_fake_python(tmp_path), user_root=root)

    result = installer.install(GALLERY_DL)

    assert result.ok, result.message
    assert (root / "gallery-dl" / "gallery_dl" / "__init__.py").exists()


def test_установка_питоновского_пакета_создаёт_запускаемый_файл(tmp_path) -> None:
    root = tmp_path / "components"
    installer = ComponentInstaller(python=_fake_python(tmp_path), user_root=root)

    installer.install(GALLERY_DL)

    launcher = root / "gallery-dl" / "bin" / "gallery-dl"
    assert launcher.exists()
    mode = stat.S_IMODE(launcher.stat().st_mode)
    assert mode & stat.S_IXUSR


def test_запускаемый_файл_вызывает_нужный_модуль(tmp_path) -> None:
    root = tmp_path / "components"
    installer = ComponentInstaller(python=_fake_python(tmp_path), user_root=root)

    installer.install(GALLERY_DL)

    body = (root / "gallery-dl" / "bin" / "gallery-dl").read_text(encoding="utf-8")
    assert "-m gallery_dl" in body
    assert "PYTHONPATH" in body


def test_установка_архива_распаковывает_исполняемый_файл(tmp_path) -> None:
    root = tmp_path / "components"
    archive = _zip_with_binary(tmp_path)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    spec = ComponentSpec(
        id="deno",
        title="deno",
        description="JS-рантайм",
        kind=ComponentKind.ARCHIVE,
        binary="deno",
        url="https://example.invalid/deno.zip",
        sha256=digest,
    )
    installer = ComponentInstaller(user_root=root, downloader=_downloader_of(archive))

    result = installer.install(spec)

    assert result.ok, result.message
    launcher = root / "deno" / "bin" / "deno"
    assert launcher.exists()
    assert os.access(launcher, os.X_OK)


def test_несовпавшая_контрольная_сумма_останавливает_установку(tmp_path) -> None:
    root = tmp_path / "components"
    archive = _zip_with_binary(tmp_path)
    installer = ComponentInstaller(
        user_root=root,
        downloader=_downloader_of(archive),
    )

    result = installer.install(DENO)

    assert not result.ok
    assert "сумм" in result.message.lower() or "sha" in result.message.lower()
    assert not (root / "deno" / "bin" / "deno").exists()


def test_сбой_загрузки_не_оставляет_каталог_компонента(tmp_path) -> None:
    root = tmp_path / "components"

    def broken_download(url: str, target: Path) -> None:
        raise OSError("сеть недоступна")

    installer = ComponentInstaller(user_root=root, downloader=broken_download)

    result = installer.install(DENO)

    assert not result.ok
    assert not (root / "deno" / "bin" / "deno").exists()
