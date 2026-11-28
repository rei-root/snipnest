"""Установка с правами администратора.

Этот модуль делает то, что нужно сделать с правами root: кладёт образ,
лаунчер, ярлык и иконки и ставит пакеты родным пакетным менеджером.
Он же работает без прав — в домашнем режиме.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .resources import desktop_file_text, icon_bytes, icon_png, icon_sizes

__all__ = [
    "InstallReport",
    "InstallRequest",
    "StepResult",
    "read_request",
    "run_install",
]

#: Путь, который получает программа под polkit: окружение там пустое.
SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

#: Куда класть иконки приложения.
_ICON_NAME = "snipnest.png"
_ICON_VECTOR_NAME = "snipnest.svg"


@dataclass(frozen=True)
class InstallRequest:
    """Что и куда ставить."""

    image_path: str
    image_name: str
    app_dir: str
    bin_dir: str
    desktop_dir: str
    icons_dir: str
    packages: tuple[str, ...] = ()
    package_command: tuple[str, ...] = ()

    def to_json(self) -> str:
        """Запрос в виде JSON — так его передаёт окно работнику с правами."""
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class StepResult:
    """Результат одного шага установки."""

    name: str
    ok: bool
    message: str = ""


@dataclass
class InstallReport:
    """Итог установки."""

    ok: bool
    steps: list[StepResult] = field(default_factory=list)

    def to_json(self) -> str:
        """Отчёт в виде JSON — так его читает окно."""
        return json.dumps(
            {"ok": self.ok, "steps": [asdict(step) for step in self.steps]},
            ensure_ascii=False,
        )


def read_request(path: Path) -> InstallRequest:
    """Прочитать запрос из файла."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return InstallRequest(
        image_path=str(raw["image_path"]),
        image_name=str(raw["image_name"]),
        app_dir=str(raw["app_dir"]),
        bin_dir=str(raw["bin_dir"]),
        desktop_dir=str(raw["desktop_dir"]),
        icons_dir=str(raw["icons_dir"]),
        packages=tuple(str(name) for name in raw.get("packages", ())),
        package_command=tuple(str(part) for part in raw.get("package_command", ())),
    )


def _launcher_text(image: Path) -> str:
    """Текст лаунчера: он запускает установленный образ."""
    return f'#!/bin/sh\n# Запуск Snipnest, установленного установщиком.\nexec "{image}" "$@"\n'


def _desktop_text(launcher: Path) -> str:
    """Текст ярлыка: он указывает на установленный лаунчер."""
    template = desktop_file_text()
    if not template:
        template = (
            "[Desktop Entry]\nType=Application\nName=Snipnest\nExec=snipnest\n"
            "Icon=snipnest\nTerminal=false\nCategories=Network;FileTransfer;\n"
        )
    lines = []
    for line in template.splitlines():
        if line.startswith("Exec="):
            lines.append(f"Exec={launcher}")
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def _write_file(path: Path, content: str | bytes, mode: int) -> None:
    """Написать файл и выставить права."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def install_image(request: InstallRequest) -> StepResult:
    """Положить портативный образ в каталог приложения."""
    source = Path(request.image_path)
    target = Path(request.app_dir) / request.image_name
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o755)
    except OSError as error:
        return StepResult("образ приложения", False, str(error))
    return StepResult("образ приложения", True, str(target))


def install_launcher(request: InstallRequest) -> StepResult:
    """Сделать лаунчер в каталоге бинарников."""
    launcher = Path(request.bin_dir) / "snipnest"
    image = Path(request.app_dir) / request.image_name
    try:
        _write_file(launcher, _launcher_text(image), 0o755)
    except OSError as error:
        return StepResult("лаунчер", False, str(error))
    return StepResult("лаунчер", True, str(launcher))


def install_desktop_entry(request: InstallRequest) -> StepResult:
    """Положить ярлык в меню приложений."""
    desktop = Path(request.desktop_dir) / "snipnest.desktop"
    launcher = Path(request.bin_dir) / "snipnest"
    try:
        _write_file(desktop, _desktop_text(launcher), 0o644)
    except OSError as error:
        return StepResult("ярлык", False, str(error))
    return StepResult("ярлык", True, str(desktop))


def install_icons(request: InstallRequest) -> StepResult:
    """Положить иконки в каталог иконок.

    Ставятся и PNG размеров, которые ищет тема иконок, и векторная иконка.
    """
    data = icon_bytes()
    if not data:
        return StepResult("иконки", True, "в установщике нет иконки — пропущено")
    root = Path(request.icons_dir)
    try:
        for size in icon_sizes():
            _write_file(root / f"{size}x{size}" / "apps" / _ICON_NAME, icon_png(size), 0o644)
        _write_file(root / "scalable" / "apps" / _ICON_VECTOR_NAME, data, 0o644)
    except OSError as error:
        return StepResult("иконки", False, str(error))
    return StepResult("иконки", True, str(root))


def install_packages(request: InstallRequest) -> StepResult:
    """Поставить пакеты родным пакетным менеджером."""
    if not request.packages or not request.package_command:
        return StepResult("зависимости", True, "не выбраны")
    command = [*request.package_command, *request.packages]
    env = {**os.environ, "PATH": SAFE_PATH, "DEBIAN_FRONTEND": "noninteractive"}
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except OSError as error:
        return StepResult("зависимости", False, str(error))
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        reason = detail[-1] if detail else f"код возврата {completed.returncode}"
        return StepResult("зависимости", False, reason)
    return StepResult("зависимости", True, ", ".join(request.packages))


def run_install(request: InstallRequest) -> InstallReport:
    """Выполнить установку по запросу."""
    steps = [
        install_image(request),
        install_launcher(request),
        install_desktop_entry(request),
        install_icons(request),
        install_packages(request),
    ]
    return InstallReport(ok=all(step.ok for step in steps), steps=steps)
