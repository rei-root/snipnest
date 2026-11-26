"""План установки: что и куда кладём."""

from __future__ import annotations

from pathlib import Path

from snipnest.installer.detect import Family
from snipnest.installer.plan import Mode, build_plan, image_name, release_url


def _plan(mode: Mode, tmp_path: Path | None = None):
    """План установки для теста."""
    return build_plan(
        mode,
        Family.DEBIAN,
        version="0.2.0",
        glibc="2.38",
        home=tmp_path,
    )


def test_системная_установка_идёт_в_opt() -> None:
    plan = _plan(Mode.SYSTEM)

    assert plan.app_dir == Path("/opt/snipnest")
    assert plan.launcher_path == Path("/usr/local/bin/snipnest")
    assert plan.desktop_path == Path("/usr/share/applications/snipnest.desktop")
    assert plan.needs_root


def test_домашняя_установка_идёт_в_local() -> None:
    plan = _plan(Mode.USER, Path("/home/человек"))

    assert plan.app_dir == Path("/home/человек/.local/opt/snipnest")
    assert plan.launcher_path == Path("/home/человек/.local/bin/snipnest")
    assert plan.desktop_path == Path("/home/человек/.local/share/applications/snipnest.desktop")
    assert not plan.needs_root


def test_имя_образа_содержит_версию_glibc_и_архитектуру() -> None:
    name = image_name("0.2.0", "2.38")

    assert name == "snipnest-0.2.0-linux-glibc-2.38-x86_64.AppImage"


def test_адрес_релиза_ведёт_на_тег_версии() -> None:
    url = release_url("0.2.0")

    assert url.endswith("/v0.2.0")


def test_план_показывает_куда_что_кладётся() -> None:
    plan = _plan(Mode.SYSTEM)

    destinations = plan.destinations()

    assert len(destinations) == 4
    assert any("/opt/snipnest" in path for path, _ in destinations)
    assert any("/usr/local/bin/snipnest" in path for path, _ in destinations)
