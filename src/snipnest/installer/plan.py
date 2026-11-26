"""План установки: что и куда кладём.

Два режима: для всех пользователей (нужны права администратора) и только для
себя (права не нужны). Формат файлов не зависит от режима — установщик
кладёт портативный образ, а не пакет.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path

from .detect import Family

__all__ = [
    "InstallPlan",
    "Mode",
    "build_plan",
    "image_name",
    "release_url",
]

#: Имя образа приложения: версия, платформа, glibc и архитектура.
IMAGE_NAME_TEMPLATE = "snipnest-{version}-linux-glibc-{glibc}-x86_64.AppImage"

#: Имя лаунчера и ярлыка.
LAUNCHER_NAME = "snipnest"
DESKTOP_NAME = "snipnest.desktop"


class Mode(enum.Enum):
    """Куда ставим приложение."""

    SYSTEM = "system"
    USER = "user"

    @property
    def title(self) -> str:
        """Название режима для показа человеку."""
        return {
            Mode.SYSTEM: "Для всех пользователей",
            Mode.USER: "Только для себя",
        }[self]


@dataclass(frozen=True)
class InstallPlan:
    """Куда что кладём."""

    mode: Mode
    family: Family
    app_dir: Path
    bin_dir: Path
    desktop_dir: Path
    icons_dir: Path
    image_name: str

    @property
    def needs_root(self) -> bool:
        """Нужны ли права администратора."""
        return self.mode is Mode.SYSTEM

    @property
    def image_path(self) -> Path:
        """Путь образа после установки."""
        return self.app_dir / self.image_name

    @property
    def launcher_path(self) -> Path:
        """Путь лаунчера."""
        return self.bin_dir / LAUNCHER_NAME

    @property
    def desktop_path(self) -> Path:
        """Путь ярлыка."""
        return self.desktop_dir / DESKTOP_NAME

    def destinations(self) -> list[tuple[str, str]]:
        """Что и куда: пары «путь — назначение» для показа человеку."""
        return [
            (str(self.image_path), "портативный образ приложения"),
            (str(self.launcher_path), "лаунчер"),
            (str(self.desktop_path), "ярлык в меню приложений"),
            (str(self.icons_dir), "иконки"),
        ]


def image_name(version: str, glibc: str) -> str:
    """Имя образа приложения для релиза."""
    return IMAGE_NAME_TEMPLATE.format(version=version, glibc=glibc)


def release_url(version: str) -> str:
    """Адрес релиза, из которого установщик берёт образ."""
    return f"https://github.com/rei-root/snipnest/releases/download/v{version}"


def build_plan(
    mode: Mode,
    family: Family,
    *,
    version: str,
    glibc: str,
    home: Path | None = None,
) -> InstallPlan:
    """План установки для режима и семейства."""
    if mode is Mode.SYSTEM:
        app_dir = Path("/opt/snipnest")
        bin_dir = Path("/usr/local/bin")
        desktop_dir = Path("/usr/share/applications")
        icons_dir = Path("/usr/share/icons/hicolor")
    else:
        base = home or Path.home()
        app_dir = base / ".local" / "opt" / "snipnest"
        bin_dir = base / ".local" / "bin"
        desktop_dir = base / ".local" / "share" / "applications"
        icons_dir = base / ".local" / "share" / "icons" / "hicolor"
    return InstallPlan(
        mode=mode,
        family=family,
        app_dir=app_dir,
        bin_dir=bin_dir,
        desktop_dir=desktop_dir,
        icons_dir=icons_dir,
        image_name=image_name(version, glibc),
    )
