"""Семейство дистрибутива и версия glibc.

Система определяется по /etc/os-release — так же, как это делает systemd.
Больше ничего не нужно: установщик работает на машине, где ещё ничего не
поставлено.
"""

from __future__ import annotations

import enum
import re
import shutil
import subprocess
from pathlib import Path

__all__ = [
    "Family",
    "detect_family",
    "glibc_version",
    "os_release_path",
    "read_os_release",
]

#: Файл, в котором дистрибутив пишет своё имя.
OS_RELEASE_PATH = Path("/etc/os-release")


class Family(enum.Enum):
    """Семейство дистрибутива."""

    DEBIAN = "debian"
    ARCH = "arch"
    RHEL = "rhel"
    SUSE = "suse"
    GENTOO = "gentoo"
    ALPINE = "alpine"
    UNKNOWN = "unknown"

    @property
    def title(self) -> str:
        """Название семейства для показа человеку."""
        return _FAMILY_TITLES[self]


_FAMILY_TITLES: dict[Family, str] = {
    Family.DEBIAN: "debian-based",
    Family.ARCH: "arch-based",
    Family.RHEL: "rhel-based",
    Family.SUSE: "suse-based",
    Family.GENTOO: "gentoo",
    Family.ALPINE: "alpine",
    Family.UNKNOWN: "неизвестная система",
}

#: Признаки семейств в ID и ID_LIKE.
_FAMILY_MARKERS: tuple[tuple[Family, tuple[str, ...]], ...] = (
    (Family.DEBIAN, ("debian", "ubuntu", "mint", "kali", "raspbian")),
    (Family.ARCH, ("arch", "manjaro", "endeavour", "cachyos")),
    (Family.RHEL, ("fedora", "rhel", "centos", "rocky", "alma", "ol")),
    (Family.SUSE, ("suse", "opensuse", "sles", "tumbleweed")),
    (Family.GENTOO, ("gentoo", "funtoo")),
    (Family.ALPINE, ("alpine",)),
)

_VERSION_PATTERN = re.compile(r"(\d+(?:\.\d+)*)")


def os_release_path() -> Path:
    """Путь к файлу с описанием системы."""
    return OS_RELEASE_PATH


def read_os_release(path: Path | None = None) -> dict[str, str]:
    """Прочитать /etc/os-release (или подставной файл) в словарь."""
    target = path or os_release_path()
    values: dict[str, str] = {}
    if not target.is_file():
        return values
    for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"')
    return values


def detect_family(path: Path | None = None) -> Family:
    """Семейство дистрибутива по /etc/os-release."""
    values = read_os_release(path)
    haystack = f" {values.get('ID', '')} {values.get('ID_LIKE', '')} ".lower()
    for family, markers in _FAMILY_MARKERS:
        if any(marker in haystack for marker in markers):
            return family
    return Family.UNKNOWN


def glibc_version() -> str:
    """Версия glibc системы — пустая строка, если узнать не удалось."""
    if shutil.which("getconf") is not None:
        completed = subprocess.run(
            ["getconf", "GNU_LIBC_VERSION"],
            capture_output=True,
            text=True,
            check=False,
        )
        found = _VERSION_PATTERN.search(completed.stdout)
        if found:
            return found.group(1)
    if shutil.which("ldd") is not None:
        completed = subprocess.run(
            ["ldd", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        found = _VERSION_PATTERN.search(completed.stdout)
        if found:
            return found.group(1)
    return ""


def version_at_least(version: str, minimum: str) -> bool:
    """Версия не меньше минимальной (пустая минимальная — любую подходит)."""
    if not minimum:
        return True
    if not version:
        return False
    parts_version = [int(part) for part in version.split(".") if part.isdigit()]
    parts_minimum = [int(part) for part in minimum.split(".") if part.isdigit()]
    return parts_version >= parts_minimum
