"""Установка компонента: скачивание, распаковка, запуск.

Сеть открывает не приложение, а внешняя программа: скачивание идёт через
``curl`` (запасной путь — ``wget``), а Python-пакеты ставит ``pip``
переносимого Python из артефакта. Правило проекта «приложение само никуда
не ходит» остаётся в силе.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .catalog import ComponentKind, ComponentSpec
from .finder import ComponentLocation
from .paths import component_dir, runtime_python, user_components_root, user_runtime_dir

__all__ = ["ComponentInstaller", "InstallResult", "download_file", "ensure_user_runtime"]

Downloader = Callable[[str, Path], None]


@dataclass(frozen=True)
class InstallResult:
    """Что получилось при установке компонента."""

    component_id: str
    ok: bool
    message: str
    location: ComponentLocation | None = None


def download_file(url: str, target: Path) -> None:
    """Скачать файл внешней программой.

    Приложение не открывает сетевых сокетов само: загрузку делает ``curl``,
    а если его нет — ``wget``.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    commands = (
        ["curl", "-fsSL", "--retry", "3", "-o", str(target), url],
        ["wget", "-q", "-O", str(target), url],
    )
    for command in commands:
        if shutil.which(command[0]) is None:
            continue
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode == 0 and target.is_file():
            return
    raise OSError(f"не удалось скачать {url}")


def ensure_user_runtime() -> Path | None:
    """Перенести переносимый Python в домашнюю папку.

    Лаунчер установленного компонента должен ссылаться на постоянный путь:
    внутри AppImage точка монтирования меняется при каждом запуске. Возвращает
    путь к интерпретатору или None, если переносимого Python нет.
    """
    target = user_runtime_dir()
    interpreter = target / "bin" / "python3"
    if interpreter.is_file():
        return interpreter
    source = runtime_python()
    if source is None:
        return None
    try:
        shutil.copytree(source.parent.parent, target, dirs_exist_ok=True)
    except OSError:
        return None
    return interpreter if interpreter.is_file() else None


def _sha256(path: Path) -> str:
    """Контрольная сумма файла."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unpack(archive: Path, destination: Path) -> None:
    """Распаковать архив в каталог."""
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(destination)
        return
    with tarfile.open(archive) as bundle:
        try:
            bundle.extractall(destination, filter="data")
        except TypeError:
            bundle.extractall(destination)


def _find_binary(root: Path, name: str) -> Path | None:
    """Найти исполняемый файл внутри распакованного архива."""
    for path in sorted(root.rglob(name)):
        if path.is_file():
            return path
    return None


def _install_binary(source: Path, target: Path, binary_name: str) -> Path:
    """Положить исполняемый файл в ``bin`` каталога компонента."""
    bin_dir = target / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    if source.parent.name == "bin":
        for item in sorted(source.parent.iterdir()):
            if item.is_file():
                shutil.copy2(item, bin_dir / item.name)
    else:
        shutil.copy2(source, bin_dir / binary_name)
    launcher = bin_dir / binary_name
    launcher.chmod(0o755)
    return launcher


class ComponentInstaller:
    """Ставит компоненты в каталог пользователя.

    ``launcher_python`` и ``launcher_root`` задают пути, которые попадают в
    запускающий файл компонента. При сборке .deb они указывают на места
    внутри пакета, а не на каталог сборки.
    """

    def __init__(
        self,
        *,
        python: Path | None = None,
        user_root: Path | None = None,
        system_root: Path | None = None,
        downloader: Downloader | None = None,
        launcher_python: Path | None = None,
        launcher_root: Path | None = None,
    ) -> None:
        self._python = python
        self._user_root = user_root
        self._system_root = system_root
        self._downloader: Downloader = downloader if downloader is not None else download_file
        self._launcher_python = launcher_python
        self._launcher_root = launcher_root

    @property
    def user_root(self) -> Path:
        """Каталог, куда ставятся компоненты."""
        return self._user_root if self._user_root is not None else user_components_root()

    def _interpreter(self) -> Path | None:
        """Интерпретатор, которым ставится пакет."""
        if self._python is not None:
            return self._python
        runtime = runtime_python()
        if runtime is not None:
            return runtime
        if getattr(sys, "frozen", False):
            return None
        return Path(sys.executable)

    def _launcher_interpreter(self) -> Path | None:
        """Интерпретатор, указанный в запускающем файле компонента."""
        if self._launcher_python is not None:
            return self._launcher_python
        runtime = ensure_user_runtime()
        if runtime is not None:
            return runtime
        return self._interpreter()

    def _launcher_components_root(self) -> Path:
        """Корень компонентов, указанный в запускающем файле."""
        return self._launcher_root if self._launcher_root is not None else self.user_root

    def install(
        self,
        spec: ComponentSpec,
        progress: Callable[[str], None] | None = None,
    ) -> InstallResult:
        """Установить компонент."""
        try:
            if spec.kind is ComponentKind.PIP:
                return self._install_pip(spec, progress)
            return self._install_archive(spec, progress)
        except Exception as exc:  # noqa: BLE001 — установка не должна ронять приложение
            return InstallResult(spec.id, False, f"Ошибка установки: {exc}")

    def install_many(
        self,
        specs: list[ComponentSpec],
        progress: Callable[[str], None] | None = None,
    ) -> list[InstallResult]:
        """Установить несколько компонентов подряд."""
        return [self.install(spec, progress) for spec in specs]

    def _install_pip(
        self,
        spec: ComponentSpec,
        progress: Callable[[str], None] | None,
    ) -> InstallResult:
        """Поставить Python-пакет переносимым Python."""
        python = self._interpreter()
        if python is None:
            return InstallResult(spec.id, False, "В артефакте нет переносимого Python")
        target = component_dir(spec.id, root=self.user_root)
        if progress is not None:
            progress(f"Устанавливаю {spec.title}…")
        target.mkdir(parents=True, exist_ok=True)
        command = [
            str(python),
            "-m",
            "pip",
            "install",
            "--no-cache-dir",
            "--disable-pip-version-check",
            "--target",
            str(target),
            *spec.packages,
        ]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            shutil.rmtree(target, ignore_errors=True)
            lines = (completed.stderr or completed.stdout).strip().splitlines()
            reason = lines[-1] if lines else "неизвестная ошибка pip"
            return InstallResult(spec.id, False, f"pip не поставил пакет: {reason}")
        if spec.binary:
            launcher_python = self._launcher_interpreter()
            if launcher_python is None:
                shutil.rmtree(target, ignore_errors=True)
                return InstallResult(spec.id, False, "В артефакте нет переносимого Python")
            self._write_launcher(spec, target, launcher_python)
        return InstallResult(spec.id, True, "Установлено", ComponentLocation(target, "user"))

    def _write_launcher(self, spec: ComponentSpec, target: Path, python: Path) -> None:
        """Создать запускающий файл компонента."""
        bin_dir = target / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        root = self._launcher_components_root()
        parts = [root / spec.id]
        parts.extend(root / other for other in spec.extra_paths)
        joined = ":".join(str(part) for part in parts)
        launcher = bin_dir / spec.binary
        launcher.write_text(
            "#!/bin/sh\n"
            "# Запускающий файл компонента Snipnest. Создан мастером установки.\n"
            f'PYTHONPATH="{joined}" exec "{python}" -m {spec.module} "$@"\n',
            encoding="utf-8",
        )
        launcher.chmod(0o755)

    def _download(self, spec: ComponentSpec, target: Path) -> None:
        """Скачать архив, взяв из кэша если он там уже есть.

        Кэш лежит в ``~/.cache/snipnest/downloads``: переустановка компонента
        не должна заново качать сто пятьдесят мегабайт.
        """
        cache = Path.home() / ".cache" / "snipnest" / "downloads" / Path(spec.url).name
        if spec.sha256 and cache.is_file() and _sha256(cache) == spec.sha256:
            shutil.copy2(cache, target)
            return
        self._downloader(spec.url, target)
        if spec.sha256 and _sha256(target) == spec.sha256:
            try:
                cache.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, cache)
            except OSError:
                return

    def _install_archive(
        self,
        spec: ComponentSpec,
        progress: Callable[[str], None] | None,
    ) -> InstallResult:
        """Скачать архив, проверить сумму и распаковать."""
        target = component_dir(spec.id, root=self.user_root)
        if progress is not None:
            progress(f"Скачиваю {spec.title}…")
        target.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="snipnest-") as tmp:
            archive = Path(tmp) / Path(spec.url).name
            self._download(spec, archive)
            digest = _sha256(archive)
            if spec.sha256 and digest != spec.sha256:
                shutil.rmtree(target, ignore_errors=True)
                return InstallResult(
                    spec.id,
                    False,
                    "Контрольная сумма не совпала: файл повреждён или подменён",
                )
            extracted = Path(tmp) / "extracted"
            extracted.mkdir()
            _unpack(archive, extracted)
            source = _find_binary(extracted, spec.binary)
            if source is None:
                shutil.rmtree(target, ignore_errors=True)
                return InstallResult(spec.id, False, f"В архиве нет файла {spec.binary}")
            launcher = _install_binary(source, target, spec.binary)
        return InstallResult(spec.id, True, "Установлено", ComponentLocation(launcher, "user"))
