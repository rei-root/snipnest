"""Общие приспособления тестов.

Установщик проверяется как чёрный ящик, поэтому системные команды в тестах —
подставные: sudo, apt-get и dpkg пишут свои аргументы в лог и возвращают
заданный код. Так тест видит ровно то, что установщик отдал системе.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest

#: Переменная окружения с кодом возврата подставной команды.
_EXIT_VAR = {
    "apt-get": "FAKE_APT_GET_EXIT",
    "dpkg": "FAKE_DPKG_EXIT",
}

_SCRIPT = """#!/bin/sh
printf '=== {name}\\n' >> "{log}"
for arg in "$@"; do printf '%s\\n' "$arg" >> "{log}"; done
last=""
for arg in "$@"; do last="$arg"; done
if [ -n "$last" ] && [ -f "$last" ]; then
    printf 'meta:file-mode %s\\n' "$(stat -c '%a' "$last" 2>/dev/null)" >> "{log}"
    printf 'meta:dir-mode %s\\n' "$(stat -c '%a' "$(dirname "$last")" 2>/dev/null)" >> "{log}"
fi
exit "${{{exit_var}:-0}}"
"""

_SUDO_SCRIPT = """#!/bin/sh
printf '=== sudo\\n' >> "{log}"
for arg in "$@"; do printf '%s\\n' "$arg" >> "{log}"; done
exec "$@"
"""


def _write_script(path: Path, body: str) -> None:
    """Написать исполняемый скрипт подставной команды."""
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


@dataclass
class FakeCommands:
    """Подставные системные команды и лог их вызовов."""

    bin_dir: Path
    log: Path
    exit_codes: dict[str, int] = field(default_factory=dict)

    def env(self) -> dict[str, str]:
        """Окружение для запуска установщика: PATH с подставными командами."""
        env = dict(os.environ)
        env["PATH"] = f"{self.bin_dir}{os.pathsep}{env.get('PATH', '')}"
        for name, code in self.exit_codes.items():
            env[_EXIT_VAR[name]] = str(code)
        return env

    def fail(self, command: str, code: int = 1) -> None:
        """Заставить подставную команду отказать."""
        self.exit_codes[command] = code

    def write(self, name: str, body: str) -> None:
        """Положить в подставные команды ещё одну: она пишет в тот же лог."""
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

    def meta(self, command: str) -> dict[str, str]:
        """Служебные значения, записанные подставной командой."""
        for name, lines in reversed(self._blocks()):
            if name != command:
                continue
            values: dict[str, str] = {}
            for line in lines:
                if not line.startswith("meta:"):
                    continue
                key, _, value = line[len("meta:") :].partition(" ")
                values[key] = value
            return values
        return {}


@pytest.fixture
def fake_commands(tmp_path: Path) -> FakeCommands:
    """Подставные sudo, apt-get и dpkg: пишут аргументы в лог."""
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    _write_script(bin_dir / "sudo", _SUDO_SCRIPT.format(log=log))
    for name in ("apt-get", "dpkg"):
        _write_script(
            bin_dir / name,
            _SCRIPT.format(name=name, log=log, exit_var=_EXIT_VAR[name]),
        )
    return FakeCommands(bin_dir=bin_dir, log=log)
