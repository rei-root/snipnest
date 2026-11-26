"""Зависимости приложения и родной пакетный менеджер системы.

Установщик не привязан к формату пакетов: приложение ставится портативным
образом, а зависимости — тем пакетным менеджером, который стоит в системе.
Список зависимостей один и тот же для всех семейств, а имена пакетов и
сама команда установки — свои.
"""

from __future__ import annotations

from dataclasses import dataclass

from .detect import Family

__all__ = [
    "Dependency",
    "DEPENDENCIES",
    "dependencies_for",
    "package_command",
    "package_names",
]


@dataclass(frozen=True)
class Dependency:
    """Зависимость приложения и пакет, который её ставит."""

    id: str
    title: str
    description: str
    packages: dict[Family, str]

    def package_for(self, family: Family) -> str:
        """Имя пакета в этом семействе; пустая строка — пакета нет."""
        return self.packages.get(family, "")


#: Зависимости, которые умеет ставить пакетный менеджер.
DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency(
        id="gallery-dl",
        title="gallery-dl",
        description="Скачивание картинок из Pinterest",
        packages={
            Family.DEBIAN: "gallery-dl",
            Family.ARCH: "gallery-dl",
            Family.RHEL: "gallery-dl",
            Family.SUSE: "gallery-dl",
            Family.ALPINE: "gallery-dl",
            Family.GENTOO: "dev-util/gallery-dl",
        },
    ),
    Dependency(
        id="yt-dlp",
        title="yt-dlp",
        description="Скачивание видео с YouTube",
        packages={
            Family.DEBIAN: "yt-dlp",
            Family.ARCH: "yt-dlp",
            Family.RHEL: "yt-dlp",
            Family.SUSE: "yt-dlp",
            Family.ALPINE: "yt-dlp",
            Family.GENTOO: "media-video/yt-dlp",
        },
    ),
    Dependency(
        id="ffmpeg",
        title="ffmpeg",
        description="Склейка видео со звуком",
        packages={
            Family.DEBIAN: "ffmpeg",
            Family.ARCH: "ffmpeg",
            Family.RHEL: "ffmpeg",
            Family.SUSE: "ffmpeg",
            Family.ALPINE: "ffmpeg",
            Family.GENTOO: "media-video/ffmpeg",
        },
    ),
)

#: Команда установки пакетов для каждого семейства.
_PACKAGE_COMMANDS: dict[Family, tuple[str, ...]] = {
    Family.DEBIAN: ("apt-get", "install", "-y"),
    Family.RHEL: ("dnf", "install", "-y"),
    Family.ARCH: ("pacman", "-S", "--noconfirm"),
    Family.SUSE: ("zypper", "--non-interactive", "install"),
    Family.ALPINE: ("apk", "add"),
    Family.GENTOO: ("emerge",),
    Family.UNKNOWN: (),
}


def dependencies_for(family: Family) -> tuple[Dependency, ...]:
    """Зависимости, у которых в этом семействе есть пакет."""
    return tuple(dependency for dependency in DEPENDENCIES if dependency.package_for(family))


def package_names(family: Family, dependency_ids: list[str]) -> list[str]:
    """Имена пакетов для выбранных зависимостей — в порядке каталога."""
    wanted = set(dependency_ids)
    names: list[str] = []
    for dependency in dependencies_for(family):
        if dependency.id in wanted:
            names.append(dependency.package_for(family))
    return names


def package_command(family: Family, packages: list[str]) -> list[str]:
    """Команда установки пакетов для семейства.

    Пустая команда — в этом семействе установка пакетов не поддержана.
    """
    head = _PACKAGE_COMMANDS.get(family, ())
    if not head or not packages:
        return []
    return [*head, *packages]
