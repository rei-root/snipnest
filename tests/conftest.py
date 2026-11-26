"""Общие приспособления тестов.

Установщик проверяется как чёрный ящик, поэтому системные команды в тестах —
подставные: они пишут свои аргументы в лог и выполняют то, что им велено.
Так тест видит ровно то, что установщик отдал системе.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pytest


def _write_script(path: Path, body: str) -> None:
    """Написать исполняемый скрипт подставной команды."""
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


@dataclass
class FakeCommands:
    """Подставные системные команды и лог их вызовов."""

    bin_dir: Path
    log: Path

    def env(self) -> dict[str, str]:
        """Окружение для запуска установщика: PATH с подставными командами."""
        env = dict(os.environ)
        env["PATH"] = f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}"
        return env

    def write(self, name: str, body: str) -> None:
        """Положить подставную команду: она пишет в тот же лог."""
        _write_script(self.bin_dir / name, body.format(log=self.log))

    def _blocks(self) -> list[tuple[str, list[str]]]:
        """Разобранный лог: список пар «команда, строки»."""
        if not self.log.exists():
            return []
        blocks: list[tuple[str, list[str]]] = []
        current: list[str] | None = None
        for line in self.log.read_text(encoding="utf-8").splitlines():
            if line.startswith("=== "):
                current = []
                blocks.append((line[4:], current))
                continue
            if current is not None:
                current.append(line)
        return blocks

    def arguments(self, command: str) -> list[str]:
        """Аргументы последнего вызова команды."""
        for name, lines in reversed(self._blocks()):
            if name == command:
                return [line for line in lines if not line.startswith("meta:")]
        return []


@pytest.fixture
def fake_commands(tmp_path: Path) -> FakeCommands:
    """Каталог подставных системных команд и лог их вызовов."""
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    return FakeCommands(bin_dir=bin_dir, log=tmp_path / "commands.log")
