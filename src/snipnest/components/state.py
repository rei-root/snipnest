"""Состояние компонентов: что установлено и показывался ли мастер."""

from __future__ import annotations

import json
from pathlib import Path

from ..settings import CONFIG_DIR

__all__ = ["ComponentState", "STATE_FILE"]

STATE_FILE = CONFIG_DIR / "components.json"


class ComponentState:
    """Что приложение знает о своих компонентах.

    Файл небольшой и не секретный: в нём отметка «мастер уже показывали»
    и версии установленных компонентов.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else STATE_FILE
        self.wizard_done: bool = False
        self.installed: dict[str, str] = {}
        self.load()

    @property
    def path(self) -> Path:
        """Путь к файлу состояния."""
        return self._path

    def load(self) -> None:
        """Прочитать состояние. Битый файл — не ошибка."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        if not isinstance(data, dict):
            return
        wizard_done = data.get("wizard_done")
        if isinstance(wizard_done, bool):
            self.wizard_done = wizard_done
        installed = data.get("installed")
        if isinstance(installed, dict):
            self.installed = {
                str(key): str(value) for key, value in installed.items() if isinstance(value, str)
            }

    def save(self) -> None:
        """Записать состояние."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {"wizard_done": self.wizard_done, "installed": self.installed}
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def mark_wizard_done(self) -> None:
        """Мастер уже показывали — больше не показываем при старте."""
        self.wizard_done = True

    def mark_installed(self, component_id: str, version: str) -> None:
        """Запомнить установленный компонент."""
        self.installed[component_id] = version
