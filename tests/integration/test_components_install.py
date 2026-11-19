"""Установка компонента по-настоящему: архив распакован, файл запускается."""

from __future__ import annotations

import hashlib
import subprocess
import zipfile
from pathlib import Path

from snipnest.components.catalog import ComponentKind, ComponentSpec
from snipnest.components.finder import find_component
from snipnest.components.installer import ComponentInstaller


def _archive(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "gallery-dl.zip"
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("gallery-dl", "#!/bin/sh\necho gallery-dl 1.32.20\n")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _spec(digest: str) -> ComponentSpec:
    return ComponentSpec(
        id="gallery-dl",
        title="gallery-dl",
        description="Скачивание из Pinterest",
        kind=ComponentKind.ARCHIVE,
        binary="gallery-dl",
        url="https://example.invalid/gallery-dl.zip",
        sha256=digest,
    )


def test_установленный_компонент_запускается(tmp_path) -> None:
    archive, digest = _archive(tmp_path)
    user_root = tmp_path / "user"

    def download(url: str, target: Path) -> None:
        target.write_bytes(archive.read_bytes())

    installer = ComponentInstaller(user_root=user_root, downloader=download)
    result = installer.install(_spec(digest))

    assert result.ok, result.message
    launcher = user_root / "gallery-dl" / "bin" / "gallery-dl"
    completed = subprocess.run(
        [str(launcher)], capture_output=True, text=True, timeout=10, check=False
    )
    assert completed.returncode == 0
    assert "1.32.20" in completed.stdout


def test_установленный_компонент_находится_поиском(tmp_path) -> None:
    archive, digest = _archive(tmp_path)
    user_root = tmp_path / "user"

    def download(url: str, target: Path) -> None:
        target.write_bytes(archive.read_bytes())

    installer = ComponentInstaller(user_root=user_root, downloader=download)
    installer.install(_spec(digest))

    location = find_component(_spec(digest), user_root=user_root, system_root=tmp_path / "system")

    assert location is not None
    assert location.source == "user"
    assert location.path.exists()
