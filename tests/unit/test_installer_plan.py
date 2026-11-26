"""План установки: что и куда кладём."""

from __future__ import annotations

from pathlib import Path

import snipnest
from snipnest.installer.detect import Family
from snipnest.installer.plan import Mode, build_plan, image_name, release_url


def _plan(mode: Mode, tmp_path: Path | None = None):
    """План установки для теста."""
    return build_plan(
        mode,
        Family.DEBIAN,
        version=snipnest.__version__,
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
    name = image_name(snipnest.__version__, "2.38")

    assert name == f"snipnest-{snipnest.__version__}-linux-glibc-2.38-x86_64.AppImage"


def test_адрес_релиза_ведёт_на_тег_версии() -> None:
    url = release_url(snipnest.__version__)

    assert url.endswith(f"/v{snipnest.__version__}")


def test_план_показывает_куда_что_кладётся() -> None:
    plan = _plan(Mode.SYSTEM)

    destinations = plan.destinations()

    assert len(destinations) == 4
    assert any("/opt/snipnest" in path for path, _ in destinations)
    assert any("/usr/local/bin/snipnest" in path for path, _ in destinations)
