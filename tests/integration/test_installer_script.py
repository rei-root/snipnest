"""Установщик Snipnest: план установки на разных семействах дистрибутивов.

Установщик — shell-скрипт, поэтому проверяем его как чёрный ящик: собираем
и запускаем с подставленным /etc/os-release и смотрим на план.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "packaging" / "build-installer.sh"
INSTALLER_NAME = "snipnest-installer-linux-amd64.bin"


def _build(tmp_path: Path) -> Path:
    """Собрать установщик во временный каталог."""
    dist = tmp_path / "dist"
    env = {**os.environ, "DIST": str(dist)}
    completed = subprocess.run(
        ["bash", str(BUILD_SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return dist / INSTALLER_NAME


def _os_release(path: Path, distro_id: str, id_like: str = "") -> Path:
    """Написать файл os-release заданного дистрибутива."""
    path.write_text(f'ID={distro_id}\nID_LIKE="{id_like}"\n', encoding="utf-8")
    return path


def _run(
    installer: Path,
    os_release: Path,
    *args: str,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Запустить установщик с подставленным os-release."""
    env = {**os.environ, "SNIPNEST_OS_RELEASE": str(os_release)}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [str(installer), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _package(tmp_path: Path) -> Path:
    """Написать файл пакета: установщику всё равно, что внутри."""
    package = tmp_path / "snipnest_0.2.0_amd64.deb"
    package.write_text("подделка пакета\n", encoding="utf-8")
    return package


def test_установщик_собирается_одним_исполняемым_файлом(tmp_path) -> None:
    installer = _build(tmp_path)

    assert installer.is_file()
    assert os.access(installer, os.X_OK)
    assert installer.read_text(encoding="utf-8").startswith("#!/bin/sh")


def test_в_установщике_нет_приложения(tmp_path) -> None:
    """Внутри установщика нет приложения: только скрипт установки."""
    body = _build(tmp_path).read_text(encoding="utf-8")

    assert "_internal" not in body
    assert "PySide6" not in body
    assert "\x7fELF" not in body


def test_на_debian_ставится_пакет(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "debian")

    result = _run(installer, release, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "apt-get install" in result.stdout
    assert ".deb" in result.stdout


def test_на_arch_образ_кладётся_в_opt(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "/opt/snipnest" in result.stdout
    assert "/usr/local/bin/snipnest" in result.stdout


def test_на_rhel_тот_же_план_образа(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "fedora", "rhel centos")

    result = _run(installer, release, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "/opt/snipnest" in result.stdout


def test_на_неизвестной_системе_берётся_образ(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "что-то-неизвестное")

    result = _run(installer, release, "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "/opt/snipnest" in result.stdout


def test_в_режиме_пользователя_всё_идёт_в_домашний_каталог(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--dry-run", "--user")

    assert result.returncode == 0, result.stderr
    assert ".local/opt/snipnest" in result.stdout
    assert "каталог: /opt/snipnest" not in result.stdout


def test_план_содержит_имя_образа_с_платформой_и_архитектурой(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--dry-run")

    assert "linux-glibc-" in result.stdout
    assert "x86_64.AppImage" in result.stdout


def test_справка_печатается(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--help")

    assert result.returncode == 0
    assert "--user" in result.stdout
    assert "--dry-run" in result.stdout


def test_версия_печатается(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--version")

    assert result.returncode == 0
    assert "snipnest-installer" in result.stdout


def test_неизвестный_ключ_останавливает_установщик(tmp_path) -> None:
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "arch")

    result = _run(installer, release, "--несуществующий")

    assert result.returncode != 0
    assert "неизвестный ключ" in result.stderr


def test_apt_получает_абсолютный_путь_к_пакету(tmp_path, fake_commands) -> None:
    """apt не берёт путь «.//tmp/…» — установщик отдаёт абсолютный путь."""
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "debian")
    package = _package(tmp_path)

    result = _run(
        installer,
        release,
        "--local",
        str(package),
        "--yes",
        env_extra=fake_commands.env(),
    )

    assert result.returncode == 0, result.stderr
    arguments = fake_commands.arguments("apt-get")
    assert arguments[:2] == ["install", "-y"]
    path = arguments[-1]
    assert not path.startswith(".//")
    assert Path(path).is_absolute()
    assert Path(path).suffix == ".deb"


def test_файл_пакета_доступен_служебному_пользователю_apt(tmp_path, fake_commands) -> None:
    """Песочница apt читает файл служебным пользователем: права должны позволять."""
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "debian")
    package = _package(tmp_path)

    result = _run(
        installer,
        release,
        "--local",
        str(package),
        "--yes",
        env_extra=fake_commands.env(),
    )

    assert result.returncode == 0, result.stderr
    meta = fake_commands.meta("apt-get")
    assert meta.get("file-mode") == "644"
    assert meta.get("dir-mode") == "755"


def test_при_отказе_apt_пакет_ставится_через_dpkg(tmp_path, fake_commands) -> None:
    """Не справился apt-get — справляется dpkg."""
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "debian")
    package = _package(tmp_path)
    fake_commands.fail("apt-get")

    result = _run(
        installer,
        release,
        "--local",
        str(package),
        "--yes",
        env_extra=fake_commands.env(),
    )

    assert result.returncode == 0, result.stderr
    assert fake_commands.arguments("dpkg")[:1] == ["-i"]
    assert "через dpkg" in result.stdout


def test_установщик_печатает_чем_поставил(tmp_path, fake_commands) -> None:
    """Человек должен видеть итог: что поставлено и чем."""
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "debian")
    package = _package(tmp_path)

    result = _run(
        installer,
        release,
        "--local",
        str(package),
        "--yes",
        env_extra=fake_commands.env(),
    )

    assert result.returncode == 0, result.stderr
    assert "через apt-get" in result.stdout
    assert "snipnest" in result.stdout


def test_установщик_ставит_только_свой_пакет(tmp_path, fake_commands) -> None:
    """Пакетным менеджером ставится только пакет Snipnest."""
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "debian")
    package = _package(tmp_path)

    result = _run(
        installer,
        release,
        "--local",
        str(package),
        "--yes",
        env_extra=fake_commands.env(),
    )

    assert result.returncode == 0, result.stderr
    arguments = fake_commands.arguments("apt-get")
    assert arguments[:2] == ["install", "-y"]
    assert len(arguments) == 3
    assert Path(arguments[2]).name == "snipnest_0.2.0_amd64.deb"


def test_на_старой_glibc_установщик_не_ставит(tmp_path, fake_commands) -> None:
    """Слишком старая glibc — установщик говорит об этом и ничего не ставит."""
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "debian")
    package = _package(tmp_path)
    fake_commands.write("getconf", "#!/bin/sh\necho 'glibc 2.5'\n")

    result = _run(
        installer,
        release,
        "--local",
        str(package),
        "--yes",
        env_extra=fake_commands.env(),
    )

    assert result.returncode != 0
    assert "glibc" in result.stderr
    assert fake_commands.arguments("apt-get") == []


def test_в_режиме_пользователя_права_не_нужны(tmp_path, fake_commands) -> None:
    """Человеку без прав администратора установщик должен обойтись без sudo."""
    installer = _build(tmp_path)
    release = _os_release(tmp_path / "os-release", "debian")
    image = tmp_path / "snipnest.AppImage"
    image.write_text("подделка образа\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()

    result = _run(
        installer,
        release,
        "--user",
        "--local",
        str(image),
        "--yes",
        env_extra={**fake_commands.env(), "HOME": str(home)},
    )

    assert result.returncode == 0, result.stderr
    assert fake_commands.arguments("sudo") == []
    assert (home / ".local" / "bin" / "snipnest").is_file()
