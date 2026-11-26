"""E2E: владелец выбирает формат — и файл остаётся в выбранном формате.

Тест офлайн: вместо настоящих gallery-dl и yt-dlp запускаются заглушки,
которые ведут себя как настоящие по контракту вывода — создают файл в
выбранной папке и отдают путь к готовому файлу.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from snipnest.jobs import JobState  # noqa: E402
from snipnest.settings import FileSecretStore, Settings  # noqa: E402
from snipnest.ui.window import MainWindow  # noqa: E402

PHOTO_URL = "https://pin.it/abc"
VIDEO_URL = "https://youtu.be/dQw4w9WgXcQ"

#: Картинка 1×1 в PNG — настоящий файл, а не заглушка.
PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQ"
    "AAAABJRU5ErkJggg=="
)

STUB_GALLERY_DL = f'''#!/usr/bin/env python3
"""Заглушка gallery-dl: создаёт картинку в выбранной папке."""
import base64
import pathlib
import sys

args = sys.argv[1:]

if "--version" in args:
    print("1.32.20")
    raise SystemExit(0)

destination = pathlib.Path(args[args.index("--destination") + 1])
target = destination / "photo.png"

if "--simulate" in args:
    print("# " + str(target))
    raise SystemExit(0)

target.write_bytes(base64.b64decode("{PNG_BASE64}"))
print(target)
'''

STUB_YT_DLP = '''#!/usr/bin/env python3
"""Заглушка yt-dlp: повторяет контракт вывода настоящего."""
import pathlib
import sys

args = sys.argv[1:]

if "--version" in args:
    print("2026.10.26")
    raise SystemExit(0)

destination = pathlib.Path(args[args.index("--paths") + 1])
template = args[args.index("-o") + 1]
selector = args[args.index("-f") + 1] if "-f" in args else ""
extension = "m4a" if selector.startswith("ba") else "mp4"
name = template.replace("%(title)s", "Test Video").replace("%(id)s", "abc123")
name = name.replace("%(ext)s", extension)
final = destination / name

if "--print-to-file" in args:
    index = args.index("--print-to-file")
    pathlib.Path(args[index + 2]).write_text(str(final), encoding="utf-8")

final.write_bytes(b"fake payload")
print("[info] abc123: Downloading 1 format(s): 137")
print("[download] Destination: " + str(destination / "Test Video [abc123].f137.mp4"))
print("[download] 100.0% of    4.42MiB at    1.00MiB/s ETA 00:00")
'''


def _executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    config = tmp_path / "settings.json"
    result = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    result.destination = str(tmp_path / "downloads")
    result.gallery_dl_path = str(_executable(tmp_path / "gallery-dl-stub", STUB_GALLERY_DL))
    result.yt_dlp_path = str(_executable(tmp_path / "yt-dlp-stub", STUB_YT_DLP))
    Path(result.destination).mkdir(parents=True, exist_ok=True)
    return result


@pytest.fixture
def window(qtbot, settings: Settings) -> MainWindow:
    win = MainWindow(settings)
    qtbot.addWidget(win)
    return win


def _wait_done(window: MainWindow, qtbot) -> str:
    job_id = window.job_ids()[0]
    qtbot.waitUntil(
        lambda: (
            window.row_for(job_id) is not None and window.row_for(job_id).state is JobState.DONE
        ),
        timeout=15000,
    )
    return job_id


def test_фото_остаётся_фотом_без_перекодировки(window: MainWindow, qtbot, settings) -> None:
    """R3: без выбора формата картинка сохраняется как отдал сайт."""
    window.link_text = PHOTO_URL
    window._on_download_clicked()

    _wait_done(window, qtbot)

    entries = sorted(Path(settings.destination).iterdir())
    assert [entry.name for entry in entries] == ["photo.png"]


def test_фото_сохраняется_в_выбранном_формате(window: MainWindow, qtbot, settings) -> None:
    """R3, AC1: выбранный формат — файл в выбранном расширении, и он один."""
    window.link_text = PHOTO_URL
    window.format_selector.select_format("jpg")
    window._on_download_clicked()

    job_id = _wait_done(window, qtbot)

    entries = sorted(Path(settings.destination).iterdir())
    assert [entry.name for entry in entries] == ["photo.jpg"]
    assert entries[0].stat().st_size > 0
    assert window.row_for(job_id).file_names == ["photo.jpg"]


def test_видео_и_звук_раздельными_файлами(window: MainWindow, qtbot, settings) -> None:
    """R3, AC1: «видео и звук отдельно» — два файла, склейки нет."""
    window.link_text = VIDEO_URL
    window.format_selector.select_format("separate")
    window._on_download_clicked()

    job_id = _wait_done(window, qtbot)

    entries = sorted(Path(settings.destination).iterdir())
    assert [entry.name for entry in entries] == [
        "Test Video [abc123] (видео).mp4",
        "Test Video [abc123] (звук).m4a",
    ]
    assert window.row_for(job_id).file_names == [
        "Test Video [abc123] (видео).mp4",
        "Test Video [abc123] (звук).m4a",
    ]
