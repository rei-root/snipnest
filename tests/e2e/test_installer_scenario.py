"""Сценарий установщика: человек выбирает компонент — компонент появляется."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt

from snipnest import binaries
from snipnest.components.catalog import ComponentKind, ComponentSpec
from snipnest.components.installer import ComponentInstaller
from snipnest.ui.components_dialog import ComponentsDialog

GALLERY_DL = ComponentSpec(
    id="gallery-dl",
    title="gallery-dl",
    description="Скачивание из Pinterest",
    kind=ComponentKind.ARCHIVE,
    binary="gallery-dl",
    url="https://example.invalid/gallery-dl.zip",
    sha256="",
)


def _archive(tmp_path: Path) -> Path:
    path = tmp_path / "gallery-dl.zip"
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("gallery-dl", "#!/bin/sh\necho gallery-dl 1.32.20\n")
    return path


def _spec_with_digest(archive: Path) -> ComponentSpec:
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    return ComponentSpec(
        id=GALLERY_DL.id,
        title=GALLERY_DL.title,
        description=GALLERY_DL.description,
        kind=GALLERY_DL.kind,
        binary=GALLERY_DL.binary,
        url=GALLERY_DL.url,
        sha256=digest,
    )


def test_человек_ставит_компонент_и_приложение_его_находит(qtbot, tmp_path, monkeypatch) -> None:
    archive = _archive(tmp_path)
    spec = _spec_with_digest(archive)
    user_root = tmp_path / "user"

    def download(url: str, target: Path) -> None:
        target.write_bytes(archive.read_bytes())

    dialog = ComponentsDialog(
        specs=[spec],
        finder=lambda item: None,
        user_root=user_root,
        system_root=tmp_path / "system",
        installer=ComponentInstaller(user_root=user_root, downloader=download),
    )
    qtbot.addWidget(dialog)

    results = dialog.install_selected()

    assert results, "установка ничего не вернула"
    assert results[0].ok, results[0].message
    installed = user_root / "gallery-dl" / "bin" / "gallery-dl"
    assert installed.exists()

    monkeypatch.setattr(binaries, "component_bin_dirs", lambda: [installed.parent])
    assert binaries.find_gallery_dl() == str(installed)


def test_снятый_с_галочки_компонент_не_ставится(qtbot, tmp_path) -> None:
    archive = _archive(tmp_path)
    spec = _spec_with_digest(archive)
    user_root = tmp_path / "user"

    def download(url: str, target: Path) -> None:
        target.write_bytes(archive.read_bytes())

    dialog = ComponentsDialog(
        specs=[spec],
        finder=lambda item: None,
        user_root=user_root,
        system_root=tmp_path / "system",
        installer=ComponentInstaller(user_root=user_root, downloader=download),
    )
    qtbot.addWidget(dialog)
    dialog.root_item().setCheckState(0, Qt.CheckState.Unchecked)

    results = dialog.install_selected()

    assert results == []
    assert not (user_root / "gallery-dl").exists()


def test_после_установки_статус_меняется(qtbot, tmp_path) -> None:
    archive = _archive(tmp_path)
    spec = _spec_with_digest(archive)
    user_root = tmp_path / "user"

    def download(url: str, target: Path) -> None:
        target.write_bytes(archive.read_bytes())

    dialog = ComponentsDialog(
        specs=[spec],
        finder=lambda item: None,
        user_root=user_root,
        system_root=tmp_path / "system",
        installer=ComponentInstaller(user_root=user_root, downloader=download),
    )
    qtbot.addWidget(dialog)

    dialog.install_selected()

    assert "установлен" in dialog.status_for("gallery-dl")
