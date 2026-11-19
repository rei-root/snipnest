"""Мастер установки компонентов: дерево с главной галочкой и списком."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from snipnest.components.catalog import COMPONENTS, ComponentKind, ComponentSpec
from snipnest.components.finder import ComponentLocation
from snipnest.ui.components_dialog import ComponentsDialog

GALLERY_DL = ComponentSpec(
    id="gallery-dl",
    title="gallery-dl",
    description="Скачивание из Pinterest",
    kind=ComponentKind.PIP,
    binary="gallery-dl",
    module="gallery_dl",
    packages=("gallery-dl==1.32.20",),
)

YT_DLP = ComponentSpec(
    id="yt-dlp",
    title="yt-dlp",
    description="Скачивание видео с YouTube",
    kind=ComponentKind.PIP,
    binary="yt-dlp",
    module="yt_dlp",
    packages=("yt-dlp==2026.10.26",),
)


@pytest.fixture
def dialog(qtbot, tmp_path) -> ComponentsDialog:
    """Диалог без найденных компонентов: ничего не установлено."""
    window = ComponentsDialog(
        specs=[GALLERY_DL, YT_DLP],
        finder=lambda spec: None,
        user_root=tmp_path / "user",
        system_root=tmp_path / "system",
    )
    qtbot.addWidget(window)
    return window


def test_в_дереве_виден_главный_пункт(dialog) -> None:
    assert dialog.root_item().text(0).startswith("Обеспечить все компоненты")


def test_главная_галочка_отмечена_по_умолчанию(dialog) -> None:
    assert dialog.root_item().checkState(0) == Qt.CheckState.Checked


def test_под_главным_пунктом_список_компонентов(dialog) -> None:
    root = dialog.root_item()

    assert root.childCount() == 2
    assert root.child(0).text(0) == "gallery-dl"
    assert root.child(1).text(0) == "yt-dlp"


def test_снятие_главной_галочки_снимает_детей(dialog) -> None:
    root = dialog.root_item()

    dialog.root_item().setCheckState(0, Qt.CheckState.Unchecked)

    assert root.child(0).checkState(0) == Qt.CheckState.Unchecked
    assert root.child(1).checkState(0) == Qt.CheckState.Unchecked


def test_отметка_одного_ребёнка_даёт_частичное_состояние_главного_пункта(dialog) -> None:
    root = dialog.root_item()

    root.child(0).setCheckState(0, Qt.CheckState.Unchecked)

    assert root.checkState(0) == Qt.CheckState.PartiallyChecked


def test_компонент_без_отметки_не_выбирается(dialog) -> None:
    dialog.root_item().child(0).setCheckState(0, Qt.CheckState.Unchecked)

    selected = [spec.id for spec in dialog.selected_components()]

    assert selected == ["yt-dlp"]


def test_выбранные_компоненты_возвращаются_по_галочкам(dialog) -> None:
    assert [spec.id for spec in dialog.selected_components()] == ["gallery-dl", "yt-dlp"]


def test_найденный_компонент_помечен_как_уже_установленный(qtbot, tmp_path) -> None:
    found = ComponentLocation(path=Path("/usr/lib/snipnest/components/gallery-dl"), source="system")
    window = ComponentsDialog(
        specs=[GALLERY_DL],
        finder=lambda spec: found,
        user_root=tmp_path / "user",
        system_root=tmp_path / "system",
    )
    qtbot.addWidget(window)

    assert "уже установлен" in window.status_for("gallery-dl")


def test_ненайденный_компонент_помечен_как_будущий_скачивание(qtbot, tmp_path) -> None:
    window = ComponentsDialog(
        specs=[GALLERY_DL],
        finder=lambda spec: None,
        user_root=tmp_path / "user",
        system_root=tmp_path / "system",
    )
    qtbot.addWidget(window)

    assert "скач" in window.status_for("gallery-dl")


def test_по_умолчанию_в_дереве_все_компоненты_каталога(qtbot, tmp_path) -> None:
    window = ComponentsDialog(
        finder=lambda spec: None,
        user_root=tmp_path / "user",
        system_root=tmp_path / "system",
    )
    qtbot.addWidget(window)

    assert window.root_item().childCount() == len(COMPONENTS)
