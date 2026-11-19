"""Обёртка над внешним бинарником gallery-dl.

Модуль не знает про Qt: он запускает процесс, читает его вывод и превращает
поток строк в события загрузки. UI подписывается на эти события.
"""

from __future__ import annotations

import dataclasses
import enum
import json
import subprocess
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from .binaries import build_child_env, find_gallery_dl

__all__ = [
    "DirectoryFormats",
    "DownloadEvent",
    "DownloadEventKind",
    "DownloadResult",
    "DownloadRunner",
    "GalleryDlRunner",
    "GalleryDlNotFoundError",
    "build_child_env",
    "flat_directory_formats",
    "parse_output_line",
    "find_gallery_dl",
]

DirectoryFormats = Callable[[int], Sequence[str]]
"""Правило раскладки: число файлов → шаблоны каталогов внутри выбранной папки.

Шаблоны — форматы опции ``directory`` gallery-dl: пустой шаблон кладёт файл
прямо в выбранную папку, непустой — в подкаталог с указанным именем.
"""


def flat_directory_formats(file_count: int) -> list[str]:
    """Раскладка по умолчанию: файлы прямо в выбранной папке.

    Выбранная папка — конечная точка: приложение не заводит своих
    подкаталогов, даже если gallery-dl умеет строить дерево.
    """
    return [""]


class GalleryDlNotFoundError(RuntimeError):
    """Бинарник gallery-dl не найден."""


class DownloadEventKind(enum.Enum):
    """События загрузки, которые видит UI."""

    FILE_DOWNLOADED = "file_downloaded"
    FILE_SKIPPED = "file_skipped"
    PROGRESS = "progress"
    LOG = "log"
    ERROR = "error"


@dataclasses.dataclass(frozen=True)
class DownloadEvent:
    """Одно событие загрузки.

    ``percent`` и ``bytes_per_second`` заполняются только событием прогресса:
    длинный файл (видео) считает процент лучше, чем по числу готовых файлов.
    """

    kind: DownloadEventKind
    path: str | None = None
    text: str = ""
    percent: float | None = None
    bytes_per_second: float | None = None


@dataclasses.dataclass(frozen=True)
class DownloadResult:
    """Итог одной загрузки."""

    downloaded: int
    skipped: int
    errors: int
    returncode: int
    files: tuple[str, ...]


def parse_output_line(line: str, stream: str = "stdout") -> DownloadEvent:
    """Разобрать строку вывода gallery-dl.

    gallery-dl пишет в stdout пути скачанных файлов, а путь уже
    существующего файла — с префиксом ``#``. В stderr идёт отладка и
    сообщения об ошибках; они файлами не являются.
    """
    stripped = line.strip()
    if stream == "stderr":
        return DownloadEvent(DownloadEventKind.LOG, text=stripped)
    if not stripped:
        return DownloadEvent(DownloadEventKind.LOG, text="")
    if stripped.startswith("# "):
        path = stripped[2:].strip()
        return DownloadEvent(DownloadEventKind.FILE_SKIPPED, path=path)
    return DownloadEvent(DownloadEventKind.FILE_DOWNLOADED, path=stripped)


class DownloadRunner(Protocol):
    """Исполнитель загрузки: то, что загрузка умеет вызывать.

    gallery-dl и yt-dlp — разные программы, но загрузка работает с обоими
    одинаково: узнать число файлов, скачать, остановиться.
    """

    def set_event_sink(self, on_event: Callable[[DownloadEvent], None] | None) -> None: ...

    def count_files(self, url: str) -> int: ...

    def run(self, url: str) -> DownloadResult: ...

    def cancel(self) -> bool: ...


class GalleryDlRunner:
    """Запускает gallery-dl и раздаёт события подписчикам.

    Запускается в отдельном потоке: UI не должен ждать сеть.
    """

    def __init__(
        self,
        binary: str | None = None,
        destination: Path | None = None,
        cookies: str | None = None,
        on_event: Callable[[DownloadEvent], None] | None = None,
        directory_formats: DirectoryFormats = flat_directory_formats,
    ) -> None:
        self._binary = binary
        self._destination = destination
        self._cookies = cookies
        self._on_event = on_event
        self._directory_formats = directory_formats
        self._file_count = 0
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def set_event_sink(self, on_event: Callable[[DownloadEvent], None] | None) -> None:
        """Подключить подписчика событий после создания исполнителя."""
        self._on_event = on_event

    def resolve_binary(self) -> str:
        """Путь к бинарнику; бросает GalleryDlNotFoundError, если не найден."""
        binary = find_gallery_dl(self._binary)
        if binary is None:
            requested = f" по пути {self._binary!r}" if self._binary else ""
            raise GalleryDlNotFoundError(f"gallery-dl не найден{requested}")
        return binary

    def build_command(
        self, url: str, *, simulate: bool = False, file_count: int | None = None
    ) -> list[str]:
        """Команда запуска gallery-dl для указанной ссылки.

        Число файлов для раскладки берётся из предварительного прохода
        (``count_files``); ``file_count`` задаёт его явно.
        """
        count = self._file_count if file_count is None else file_count
        command = [self.resolve_binary()]
        if self._destination is not None:
            command.extend(["--destination", str(self._destination)])
        if self._cookies:
            command.extend(["--cookies", self._cookies])
        formats = list(self._directory_formats(count))
        command.extend(["-o", "directory=" + json.dumps(formats, ensure_ascii=False)])
        if simulate:
            command.append("--simulate")
        command.append(url)
        return command

    def run(self, url: str, *, simulate: bool = False) -> DownloadResult:
        """Запустить загрузку и дождаться итога. Возвращает итог."""
        command = self.build_command(url, simulate=simulate)

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=build_child_env(),
            )
        except OSError as exc:
            event = DownloadEvent(DownloadEventKind.ERROR, text=str(exc))
            self._emit(event)
            return DownloadResult(0, 0, 1, 1, ())

        with self._lock:
            self._process = process

        downloaded = 0
        skipped = 0
        files: list[str] = []
        skipped_paths: list[str] = []
        stdout_files: list[str] = []
        stdout_thread = threading.Thread(
            target=self._read_stdout,
            args=(process, lambda event: self._handle_stdout(event, stdout_files, skipped_paths)),
            daemon=True,
        )
        stdout_thread.start()
        stderr_lines: list[str] = []
        stderr_thread = threading.Thread(
            target=self._read_stderr,
            args=(process, stderr_lines),
            daemon=True,
        )
        stderr_thread.start()
        returncode = process.wait()
        stdout_thread.join()
        stderr_thread.join()
        with self._lock:
            self._process = None

        errors = 0
        if returncode != 0:
            errors = 1
            message = "\n".join(stderr_lines).strip()
            if message:
                self._emit(DownloadEvent(DownloadEventKind.ERROR, text=message))
        elif stderr_lines:
            for line in stderr_lines:
                self._emit(DownloadEvent(DownloadEventKind.LOG, text=line))

        downloaded = len(stdout_files)
        skipped = len(skipped_paths)
        files.extend(stdout_files)
        files.extend(skipped_paths)
        return DownloadResult(downloaded, skipped, errors, returncode, tuple(files))

    def _handle_stdout(
        self, event: DownloadEvent, files: list[str], skipped_paths: list[str]
    ) -> None:
        if event.kind is DownloadEventKind.FILE_DOWNLOADED:
            files.append(event.path or "")
        elif event.kind is DownloadEventKind.FILE_SKIPPED:
            skipped_paths.append(event.path or "")
        self._emit(event)

    def _read_stdout(
        self, process: subprocess.Popen[str], handle: Callable[[DownloadEvent], None]
    ) -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            handle(parse_output_line(line, stream="stdout"))

    def _read_stderr(self, process: subprocess.Popen[str], lines: list[str]) -> None:
        if process.stderr is None:
            return
        for line in process.stderr:
            text = line.strip()
            lines.append(text)
            self._emit(DownloadEvent(DownloadEventKind.LOG, text=text))

    def _emit(self, event: DownloadEvent) -> None:
        if self._on_event is not None:
            self._on_event(event)

    def count_files(self, url: str) -> int:
        """Сколько файлов gallery-dl соберётся скачать по ссылке.

        Число запоминается: по нему выбирается раскладка внутри выбранной
        папки (картинка или альбом).
        """
        result = self.run(url, simulate=True)
        if result.returncode != 0:
            raise RuntimeError(f"не удалось подсчитать файлы для {url!r}")
        total = result.downloaded + result.skipped
        self._file_count = total
        return total

    def cancel(self) -> bool:
        """Остановить текущий процесс. True, если он был и остановлен."""
        with self._lock:
            process = self._process
        if process is None or process.poll() is not None:
            return False
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return True
