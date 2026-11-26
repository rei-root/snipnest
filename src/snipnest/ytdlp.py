"""Обёртка над внешним бинарником yt-dlp: загрузка видео с YouTube.

Модуль не знает про Qt: он запускает процесс, читает его вывод и превращает
поток строк в события загрузки. UI подписывается на эти события.

Видео и звук YouTube приходят отдельными потоками, поэтому yt-dlp их
склеивает (нужен ffmpeg), а готовый файл приложение узнаёт по пути,
который yt-dlp пишет через ``--print-to-file after_move:``.

Формат сохранения выбирает владелец: контейнер видео, извлечение звука или
раздельные файлы. От выбора зависит, одним запуском скачивается ролик или
двумя, — поэтому загрузка идёт шагами.
"""

from __future__ import annotations

import dataclasses
import re
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path

from .binaries import build_child_env, find_component_binary, find_yt_dlp
from .downloader import DownloadEvent, DownloadEventKind, DownloadResult
from .formats import DEFAULT_AUDIO, DEFAULT_VIDEO, AudioFormat, VideoFormat

__all__ = [
    "AUDIO_QUALITY",
    "DownloadStep",
    "OUTPUT_TEMPLATE",
    "SEPARATE_AUDIO_TEMPLATE",
    "SEPARATE_VIDEO_TEMPLATE",
    "VIDEO_FORMAT",
    "YtDlpNotFoundError",
    "YtDlpRunner",
    "find_ffmpeg",
    "find_js_runtime",
    "find_yt_dlp",
    "overall_percent",
    "parse_stream_count",
    "parse_ytdlp_line",
]

#: Имя файла: название ролика и его идентификатор.
OUTPUT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"

#: Имена раздельных файлов: расширения видеопотока и звукового потока могут
#: совпасть, а совпавшие имена перезаписали бы друг друга.
SEPARATE_VIDEO_TEMPLATE = "%(title)s [%(id)s] (видео).%(ext)s"
SEPARATE_AUDIO_TEMPLATE = "%(title)s [%(id)s] (звук).%(ext)s"

#: Лучшее доступное качество с предпочтением mp4 (H.264 и AAC): такой файл
#: проигрывается везде. Если mp4 нет — берётся любой доступный формат.
VIDEO_FORMAT = DEFAULT_VIDEO.selector

#: Качество перекодировки звука: 0 — лучшее, 10 — худшее.
AUDIO_QUALITY = "0"

#: JS-рантаймы, которыми yt-dlp решает челленджеры YouTube. deno включён
#: по умолчанию, остальные — только по флагу ``--js-runtimes``.
JS_RUNTIMES = ("deno", "node", "quickjs")

#: Строка прогресса yt-dlp: процент, размер и скорость.
_PERCENT_RE = re.compile(r"^\[download\]\s+(?P<percent>\d{1,3}(?:\.\d+)?)%")
_SPEED_RE = re.compile(r"at\s+(?P<speed>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z]+)/s")

#: Файл уже скачан: качать его не нужно.
_ALREADY_RE = re.compile(r"^\[download\]\s+(?P<path>.+?)\s+has already been downloaded$")

#: Информационная строка со списком потоков ролика. Идентификаторы перечислены
#: через «+» (склейка) или через пробел (отдельные файлы).
_STREAMS_RE = re.compile(
    r"^\[info\].*Downloading\s+(?P<count>\d+)\s+format\(s\):\s*"
    r"(?P<formats>[\w.+-]+(?:[\s+][\w.+-]+)*)\s*$"
)

#: Множители скорости: yt-dlp печатает двоичные единицы.
_SPEED_UNITS = {
    "b": 1,
    "kib": 1024,
    "mib": 1024**2,
    "gib": 1024**3,
    "tib": 1024**4,
    "kb": 1000,
    "mb": 1000**2,
    "gb": 1000**3,
    "tb": 1000**4,
}


class YtDlpNotFoundError(RuntimeError):
    """Бинарник yt-dlp не найден."""


def find_js_runtime() -> str | None:
    """JS-рантайм для yt-dlp: имя или «имя:путь».

    Без рантайма yt-dlp не решает челленджеры YouTube: часть форматов
    пропадает, а извлечение помечается как устаревшее. Рантайм, поставленный
    мастером установки, лежит не в PATH, поэтому путь передаётся явно.
    """
    for name in JS_RUNTIMES:
        if shutil.which(name) is not None:
            return name
        component = find_component_binary(name)
        if component is not None:
            return f"{name}:{component}"
    return None


def find_ffmpeg() -> str | None:
    """Путь к ffmpeg или None.

    ffmpeg нужен yt-dlp для склейки видео со звуком. Поставленный мастером
    лежит не в PATH, поэтому путь передаётся явно.
    """
    component = find_component_binary("ffmpeg")
    if component is not None:
        return component
    return shutil.which("ffmpeg")


def _parse_speed(text: str) -> float | None:
    """Скорость из строки прогресса в байтах в секунду."""
    match = _SPEED_RE.search(text)
    if match is None:
        return None
    unit = _SPEED_UNITS.get(match.group("unit").lower())
    if unit is None:
        return None
    return float(match.group("speed")) * unit


def parse_ytdlp_line(line: str) -> DownloadEvent:
    """Разобрать строку вывода yt-dlp.

    Прогресс приходит отдельными строками (``--newline``), остальное —
    сообщения yt-dlp, которые видны в логе.
    """
    text = line.strip()
    percent_match = _PERCENT_RE.match(text)
    if percent_match is not None:
        return DownloadEvent(
            DownloadEventKind.PROGRESS,
            percent=float(percent_match.group("percent")),
            bytes_per_second=_parse_speed(text),
        )
    already = _ALREADY_RE.match(text)
    if already is not None:
        return DownloadEvent(DownloadEventKind.FILE_SKIPPED, path=already.group("path"))
    return DownloadEvent(DownloadEventKind.LOG, text=text)


def parse_stream_count(line: str) -> int | None:
    """Сколько потоков (видео и звук) скачивается. None, если строки нет.

    При склейке yt-dlp пишет «Downloading 1 format(s): 394+251» — потоков два,
    а формат один. При скачивании по отдельности — «Downloading 2 format(s):
    137 140»: форматов два, и потоков тоже два.
    """
    match = _STREAMS_RE.match(line.strip())
    if match is None:
        return None
    formats = match.group("formats")
    if "+" in formats:
        return len(formats.split("+"))
    return int(match.group("count"))


def overall_percent(streams_total: int, streams_done: int, fraction: float) -> float:
    """Общий процент загрузки в процентах.

    Потоки считаются целиком, текущий — по своей доле: видео и звук идут
    по очереди, и без этого процент прыгал бы назад на втором потоке.
    """
    total = max(1, streams_total)
    done = max(0, min(streams_done, total - 1))
    return (done + min(max(fraction, 0.0), 1.0)) * 100.0 / total


class _StreamState:
    """Ход скачивания: сколько потоков и какой из них идёт сейчас."""

    def __init__(self) -> None:
        self.total = 1
        self.current = 0

    def start_stream(self) -> None:
        """Начался очередной поток."""
        self.current += 1

    @property
    def done(self) -> int:
        """Сколько потоков скачано целиком."""
        return max(0, self.current - 1)


@dataclasses.dataclass(frozen=True)
class DownloadStep:
    """Один запуск yt-dlp: команда без ссылки и без ``--print-to-file``.

    Ссылка и файл, куда yt-dlp пишет путь к готовому файлу, добавляются при
    запуске: у каждого шага свой файл.
    """

    command: list[str]


class YtDlpRunner:
    """Запускает yt-dlp и раздаёт события подписчикам.

    Запускается в отдельном потоке: UI не должен ждать сеть.
    """

    #: Имя исполнителя — оно попадает в сообщение об ошибке.
    name = "yt-dlp"

    def __init__(
        self,
        binary: str | None = None,
        destination: Path | None = None,
        cookies_file: str | None = None,
        cookies_browser: str | None = None,
        on_event: Callable[[DownloadEvent], None] | None = None,
        video_format: VideoFormat | None = None,
        audio_format: AudioFormat | None = None,
    ) -> None:
        self._binary = binary
        self._destination = destination
        self._cookies_file = cookies_file
        self._cookies_browser = cookies_browser
        self._on_event = on_event
        self._video_format = video_format or DEFAULT_VIDEO
        self._audio_format = audio_format or DEFAULT_AUDIO
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def set_event_sink(self, on_event: Callable[[DownloadEvent], None] | None) -> None:
        """Подключить подписчика событий после создания исполнителя."""
        self._on_event = on_event

    def resolve_binary(self) -> str:
        """Путь к бинарнику; бросает YtDlpNotFoundError, если не найден."""
        binary = find_yt_dlp(self._binary)
        if binary is None:
            requested = f" по пути {self._binary!r}" if self._binary else ""
            raise YtDlpNotFoundError(f"yt-dlp не найден{requested}")
        return binary

    def _base_command(self) -> list[str]:
        """Общая часть команды: бинарь, путь, cookies."""
        command = [self.resolve_binary(), "--newline", "--no-playlist"]
        runtime = find_js_runtime()
        if runtime is not None:
            command.extend(["--js-runtimes", runtime])
        ffmpeg = find_ffmpeg()
        if ffmpeg is not None:
            command.extend(["--ffmpeg-location", ffmpeg])
        if self._destination is not None:
            command.extend(["--paths", str(self._destination)])
        if self._cookies_browser:
            command.extend(["--cookies-from-browser", self._cookies_browser])
        elif self._cookies_file:
            command.extend(["--cookies", self._cookies_file])
        return command

    def _plan(self) -> list[tuple[list[str], str]]:
        """План загрузки: флаги и шаблон имени для каждого шага."""
        fmt = self._video_format
        if fmt.separate:
            return [
                (["-f", fmt.selector], SEPARATE_VIDEO_TEMPLATE),
                (
                    [
                        "-f",
                        fmt.audio_selector or "ba",
                        "-x",
                        "--audio-format",
                        self._audio_format.extension,
                        "--audio-quality",
                        AUDIO_QUALITY,
                    ],
                    SEPARATE_AUDIO_TEMPLATE,
                ),
            ]
        if fmt.extract_audio:
            return [
                (
                    [
                        "-f",
                        fmt.selector,
                        "-x",
                        "--audio-format",
                        self._audio_format.extension,
                        "--audio-quality",
                        AUDIO_QUALITY,
                    ],
                    OUTPUT_TEMPLATE,
                )
            ]
        flags = ["-f", fmt.selector]
        if fmt.merge_output:
            flags.extend(["--merge-output-format", fmt.merge_output])
        return [(flags, OUTPUT_TEMPLATE)]

    def build_steps(self, url: str) -> list[DownloadStep]:
        """Шаги загрузки: по одному на файл, который получится на диске."""
        steps: list[DownloadStep] = []
        for flags, template in self._plan():
            command = self._base_command()
            command.extend(flags)
            command.extend(["-o", template])
            steps.append(DownloadStep(command))
        return steps

    def build_command(self, url: str, *, path_file: str | Path | None = None) -> list[str]:
        """Команда запуска yt-dlp для указанной ссылки.

        ``path_file`` — файл, в который yt-dlp запишет путь к готовому файлу
        после склейки: имя временного потока и имя результата различаются.

        Раздельные файлы скачиваются двумя запусками: полная картина — в
        :meth:`build_steps`.
        """
        steps = self.build_steps(url)
        command = list(steps[0].command)
        if path_file is not None:
            command.extend(["--print-to-file", "after_move:%(filepath)s", str(path_file)])
        command.append(url)
        return command

    def run(self, url: str) -> DownloadResult:
        """Запустить загрузку и дождаться итога. Возвращает итог."""
        with tempfile.TemporaryDirectory(prefix="snipnest-ytdlp-") as temp_dir:
            steps = self.build_steps(url)
            return self._run(url, steps, Path(temp_dir))

    def _run(self, url: str, steps: list[DownloadStep], temp_dir: Path) -> DownloadResult:
        """Прогнать шаги загрузки по очереди и собрать общий итог."""
        files: list[str] = []
        skipped: list[str] = []
        errors = 0
        returncode = 0
        total_steps = len(steps)
        for index, step in enumerate(steps):
            path_file = temp_dir / f"path-{index}.txt"
            command = [
                *step.command,
                "--print-to-file",
                "after_move:%(filepath)s",
                str(path_file),
                url,
            ]
            step_files, step_skipped, step_errors, step_code = self._run_step(
                command,
                path_file,
                index,
                total_steps,
            )
            files.extend(step_files)
            skipped.extend(step_skipped)
            errors += step_errors
            if step_code != 0:
                returncode = step_code
                break
        return DownloadResult(len(files), len(skipped), errors, returncode, tuple(files))

    def _run_step(
        self,
        command: list[str],
        path_file: Path,
        index: int,
        total_steps: int,
    ) -> tuple[list[str], list[str], int, int]:
        """Один запуск yt-dlp: файлы, пропущенные, ошибки и код возврата."""
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
            return [], [], 1, 1

        with self._lock:
            self._process = process

        state = _StreamState()
        files: list[str] = []
        skipped: list[str] = []
        stdout_thread = threading.Thread(
            target=self._read_stdout,
            args=(process, state, files, skipped, index, total_steps),
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
        else:
            for line in stderr_lines:
                self._emit(DownloadEvent(DownloadEventKind.LOG, text=line))

        final_path = self._read_final_path(path_file)
        if final_path is not None and final_path not in skipped:
            files.append(final_path)
            self._emit(DownloadEvent(DownloadEventKind.FILE_DOWNLOADED, path=final_path))

        return files, skipped, errors, returncode

    def _read_stdout(
        self,
        process: subprocess.Popen[str],
        state: _StreamState,
        files: list[str],
        skipped: list[str],
        index: int,
        total_steps: int,
    ) -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            text = line.strip()
            if not text:
                continue
            if text.startswith("[download] Destination:"):
                state.start_stream()
                self._emit(DownloadEvent(DownloadEventKind.LOG, text=text))
                continue
            streams = parse_stream_count(text)
            if streams is not None:
                state.total = streams
                self._emit(DownloadEvent(DownloadEventKind.LOG, text=text))
                continue
            event = parse_ytdlp_line(text)
            if event.kind is DownloadEventKind.PROGRESS:
                percent = overall_percent(
                    state.total,
                    state.done,
                    (event.percent or 0.0) / 100.0,
                )
                self._emit(
                    DownloadEvent(
                        DownloadEventKind.PROGRESS,
                        percent=self._overall_percent(percent, index, total_steps),
                        bytes_per_second=event.bytes_per_second,
                    )
                )
                continue
            if event.kind is DownloadEventKind.FILE_SKIPPED:
                skipped.append(event.path or "")
            self._emit(event)

    @staticmethod
    def _overall_percent(step_percent: float, index: int, total_steps: int) -> float:
        """Процент загрузки с учётом шагов: шаг — часть общего дела."""
        return (index * 100.0 + step_percent) / total_steps

    def _read_stderr(self, process: subprocess.Popen[str], lines: list[str]) -> None:
        if process.stderr is None:
            return
        for line in process.stderr:
            text = line.strip()
            lines.append(text)
            self._emit(DownloadEvent(DownloadEventKind.LOG, text=text))

    def _read_final_path(self, path_file: Path) -> str | None:
        """Путь к готовому файлу, который записал yt-dlp."""
        try:
            content = path_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        path = content.strip().splitlines()
        if not path or not path[-1].strip():
            return None
        return path[-1].strip()

    def _emit(self, event: DownloadEvent) -> None:
        if self._on_event is not None:
            self._on_event(event)

    def count_files(self, url: str) -> int:
        """Сколько файлов даст ссылка.

        Одна ссылка — одно видео, поэтому предварительный проход не нужен:
        в сеть за лишним запросом не ходим. Раздельные файлы — два: видео
        и звук.
        """
        return 2 if self._video_format.separate else 1

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
