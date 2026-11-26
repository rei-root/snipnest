"""Зависимости и родной пакетный менеджер системы."""

from __future__ import annotations

from snipnest.installer.dependencies import (
    dependencies_for,
    package_command,
    package_names,
)
from snipnest.installer.detect import Family


def test_зависимости_есть_в_каждом_семействе() -> None:
    for family in Family:
        if family is Family.UNKNOWN:
            continue
        assert dependencies_for(family), family


def test_зависимости_это_gallery_dl_yt_dlp_и_ffmpeg() -> None:
    ids = [dependency.id for dependency in dependencies_for(Family.DEBIAN)]

    assert ids == ["gallery-dl", "yt-dlp", "ffmpeg"]


def test_имена_пакетов_для_debian() -> None:
    names = package_names(Family.DEBIAN, ["gallery-dl", "yt-dlp", "ffmpeg"])

    assert names == ["gallery-dl", "yt-dlp", "ffmpeg"]


def test_имена_пакетов_для_gentoo_с_категориями() -> None:
    names = package_names(Family.GENTOO, ["gallery-dl", "yt-dlp"])

    assert names == ["dev-util/gallery-dl", "media-video/yt-dlp"]


def test_невыбранные_зависимости_в_команду_не_попадают() -> None:
    names = package_names(Family.DEBIAN, ["ffmpeg"])

    assert names == ["ffmpeg"]


def test_команда_для_debian_через_apt_get() -> None:
    command = package_command(Family.DEBIAN, ["gallery-dl"])

    assert command == ["apt-get", "install", "-y", "gallery-dl"]


def test_команда_для_fedora_через_dnf() -> None:
    command = package_command(Family.RHEL, ["ffmpeg"])

    assert command == ["dnf", "install", "-y", "ffmpeg"]


def test_команда_для_arch_через_pacman() -> None:
    command = package_command(Family.ARCH, ["yt-dlp"])

    assert command == ["pacman", "-S", "--noconfirm", "yt-dlp"]


def test_команда_для_suse_через_zypper() -> None:
    command = package_command(Family.SUSE, ["gallery-dl"])

    assert command == ["zypper", "--non-interactive", "install", "gallery-dl"]


def test_команда_для_alpine_через_apk() -> None:
    command = package_command(Family.ALPINE, ["ffmpeg"])

    assert command == ["apk", "add", "ffmpeg"]


def test_команда_для_gentoo_через_emerge() -> None:
    command = package_command(Family.GENTOO, package_names(Family.GENTOO, ["yt-dlp"]))

    assert command == ["emerge", "media-video/yt-dlp"]


def test_в_неизвестной_системе_команды_нет() -> None:
    assert package_command(Family.UNKNOWN, ["ffmpeg"]) == []
