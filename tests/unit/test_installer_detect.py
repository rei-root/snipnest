"""Определение системы: семейство дистрибутива и версия glibc."""

from __future__ import annotations

from pathlib import Path

from snipnest.installer.detect import (
    Family,
    detect_family,
    read_os_release,
    version_at_least,
)


def _os_release(tmp_path: Path, body: str) -> Path:
    """Написать подставной /etc/os-release."""
    path = tmp_path / "os-release"
    path.write_text(body, encoding="utf-8")
    return path


def test_debian_опознаётся_по_id(tmp_path) -> None:
    path = _os_release(tmp_path, 'ID=debian\nID_LIKE=""\n')

    assert detect_family(path) is Family.DEBIAN


def test_ubuntu_опознаётся_по_id_like(tmp_path) -> None:
    path = _os_release(tmp_path, 'ID=ubuntu\nID_LIKE="debian"\n')

    assert detect_family(path) is Family.DEBIAN


def test_fedora_опознаётся_как_rhel(tmp_path) -> None:
    path = _os_release(tmp_path, 'ID=fedora\nID_LIKE="rhel fedora"\n')

    assert detect_family(path) is Family.RHEL


def test_arch_опознаётся(tmp_path) -> None:
    path = _os_release(tmp_path, 'ID=arch\nID_LIKE=""\n')

    assert detect_family(path) is Family.ARCH


def test_suse_опознаётся(tmp_path) -> None:
    path = _os_release(tmp_path, 'ID=opensuse-tumbleweed\nID_LIKE="suse"\n')

    assert detect_family(path) is Family.SUSE


def test_alpine_опознаётся(tmp_path) -> None:
    path = _os_release(tmp_path, 'ID=alpine\nID_LIKE=""\n')

    assert detect_family(path) is Family.ALPINE


def test_gentoo_опознаётся(tmp_path) -> None:
    path = _os_release(tmp_path, 'ID=gentoo\nID_LIKE=""\n')

    assert detect_family(path) is Family.GENTOO


def test_неизвестная_система_не_ломает_определение(tmp_path) -> None:
    path = _os_release(tmp_path, 'ID=что-то\nID_LIKE=""\n')

    assert detect_family(path) is Family.UNKNOWN


def test_без_файла_система_неизвестна(tmp_path) -> None:
    assert detect_family(tmp_path / "нет-такого") is Family.UNKNOWN


def test_os_release_читается_в_словарь(tmp_path) -> None:
    path = _os_release(tmp_path, 'NAME="Debian GNU/Linux"\nID=debian\n# комментарий\n')

    values = read_os_release(path)

    assert values["ID"] == "debian"
    assert values["NAME"] == "Debian GNU/Linux"


def test_glibc_сравнивается_с_минимальной() -> None:
    assert version_at_least("2.43", "2.38")
    assert version_at_least("2.38", "2.38")
    assert not version_at_least("2.36", "2.38")


def test_пустая_glibc_не_проходит_проверку() -> None:
    assert not version_at_least("", "2.38")
