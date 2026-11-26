"""Окно установщика: что человек видит и что может снять с галочки."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt, QThread

from snipnest.installer.detect import Family
from snipnest.installer.plan import Mode
from snipnest.installer.window import InstallerContext, InstallerWindow, _InstallWorker


def _context(**overrides) -> InstallerContext:
    """Сведения о системе для теста."""
    values = {
        "version": "0.2.0",
        "family": Family.DEBIAN,
        "glibc": "2.43",
        "min_glibc": "2.38",
        "release_url": "https://example.invalid/releases",
    }
    values.update(overrides)
    return InstallerContext(**values)


@pytest.fixture
def window(qtbot) -> InstallerWindow:
    """Окно установщика на debian-системе."""
    widget = InstallerWindow(_context())
    qtbot.addWidget(widget)
    return widget


def test_в_окне_видно_семейство_системы(window) -> None:
    assert "debian-based" in window.system_text()


def test_в_окне_видно_версию_glibc(window) -> None:
    assert "2.43" in window.system_text()


def test_на_старой_glibc_кнопка_установки_выключена(qtbot) -> None:
    widget = InstallerWindow(_context(glibc="2.30"))
    qtbot.addWidget(widget)

    assert not widget.install_button().isEnabled()


def test_в_плане_видно_куда_кладётся(window) -> None:
    text = window.plan_text()

    assert "/opt/snipnest" in text
    assert "/usr/local/bin/snipnest" in text


def test_в_домашнем_режиме_план_меняется(window) -> None:
    window.set_mode(Mode.USER)

    assert ".local/opt/snipnest" in window.plan_text()


def test_список_зависимостей_с_галочками(window) -> None:
    tree = window.dependency_widget()

    assert tree.topLevelItemCount() == 3
    assert tree.topLevelItem(0).text(0) == "gallery-dl"
    assert tree.topLevelItem(1).text(0) == "yt-dlp"
    assert tree.topLevelItem(2).text(0) == "ffmpeg"


def test_зависимости_отмечены_по_умолчанию(window) -> None:
    tree = window.dependency_widget()

    assert tree.topLevelItem(0).checkState(0) == Qt.CheckState.Checked
    assert window.selected_dependencies() == ["gallery-dl", "yt-dlp", "ffmpeg"]


def test_снятие_галочки_убирает_зависимость(window) -> None:
    tree = window.dependency_widget()

    tree.topLevelItem(1).setCheckState(0, Qt.CheckState.Unchecked)

    assert window.selected_dependencies() == ["gallery-dl", "ffmpeg"]


def test_в_неизвестной_системе_зависимостей_нет(qtbot) -> None:
    widget = InstallerWindow(_context(family=Family.UNKNOWN))
    qtbot.addWidget(widget)

    assert widget.dependency_widget().topLevelItemCount() == 0


def test_работа_идёт_в_отдельном_потоке(window, monkeypatch) -> None:
    """Окно не должно висеть: загрузка и установка идут в отдельном потоке."""
    monkeypatch.setattr(_InstallWorker, "run", lambda self: None)

    window.install([])

    thread = window.worker_thread()
    assert thread is not None
    assert thread is not QThread.currentThread()
    thread.quit()
    thread.wait()
