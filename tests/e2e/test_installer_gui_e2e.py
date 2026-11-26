"""Установщик с начала до конца: человек запускает его, и приложение встаёт.

Проверяется путь через polkit: подставной pkexec выполняет команду, как это
делает настоящий, — только без прав администратора.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from snipnest.installer import elevate
from snipnest.installer.worker import InstallRequest

#: Подставной pkexec: пишет свои аргументы в лог и выполняет команду.
FAKE_PKEXEC = (
    "#!/bin/sh\n"
    "printf '=== pkexec\\n' >> \"{log}\"\n"
    'for a in "$@"; do printf \'%s\\n\' "$a" >> "{log}"; done\n'
    'exec "$@"\n'
)


def _request(tmp_path: Path) -> InstallRequest:
    """Запрос на установку в тестовый каталог."""
    image = tmp_path / "snipnest.AppImage"
    image.write_text("подделка образа\n", encoding="utf-8")
    return InstallRequest(
        image_path=str(image),
        image_name="snipnest.AppImage",
        app_dir=str(tmp_path / "opt"),
        bin_dir=str(tmp_path / "bin"),
        desktop_dir=str(tmp_path / "share"),
        icons_dir=str(tmp_path / "icons"),
    )


def _with_fake_pkexec(fake_commands, monkeypatch) -> None:
    """Подложить pkexec и сказать установщику, где его искать."""
    fake_commands.write("pkexec", FAKE_PKEXEC)
    monkeypatch.setenv("PATH", f"{fake_commands.bin_dir}{os.pathsep}{os.environ['PATH']}")


def test_установка_через_polkit_кладёт_приложение(tmp_path, fake_commands, monkeypatch) -> None:
    """Подставной pkexec выполняет работника — файлы оказываются на месте."""
    _with_fake_pkexec(fake_commands, monkeypatch)
    request = _request(tmp_path)

    report = elevate.run_privileged(request)

    assert report.ok, report.steps
    assert (tmp_path / "opt" / "snipnest.AppImage").is_file()
    assert os.access(tmp_path / "bin" / "snipnest", os.X_OK)
    assert (tmp_path / "share" / "snipnest.desktop").is_file()


def test_polkit_вызывается_с_командой_работника(tmp_path, fake_commands, monkeypatch) -> None:
    _with_fake_pkexec(fake_commands, monkeypatch)

    report = elevate.run_privileged(_request(tmp_path))

    assert report.ok, report.steps
    arguments = fake_commands.arguments("pkexec")
    assert "--root-worker" in arguments
    assert any(argument.endswith("request.json") for argument in arguments)


def test_без_polkit_установщик_объясняет_это(tmp_path, monkeypatch) -> None:
    """Нет pkexec — установщик не молчит, а говорит, что делать."""
    empty = tmp_path / "пусто"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    report = elevate.run_privileged(_request(tmp_path))

    assert not report.ok
    assert "pkexec" in report.steps[0].message


def test_отчёт_работника_разбирается(tmp_path, fake_commands, monkeypatch) -> None:
    """Отчёт приходит в окно как JSON — иначе окно не поймёт, что вышло."""
    _with_fake_pkexec(fake_commands, monkeypatch)

    report = elevate.run_privileged(_request(tmp_path))

    parsed = json.loads(report.to_json())
    assert parsed["ok"]
    assert parsed["steps"]
