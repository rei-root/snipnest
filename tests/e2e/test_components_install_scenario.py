"""E2E: мастер установки ставит именно ту версию, что закреплена в каталоге.

Тест офлайн: вместо настоящего pip запускается заглушка, которая записывает
свои аргументы — так видно, какую версию приложение просит поставить.

Требования, которые закрывают эти проверки:

* R3 — требования: мастер ставит закреплённую версию yt-dlp.
"""

from __future__ import annotations

from pathlib import Path

from snipnest.components.catalog import component_by_id
from snipnest.components.installer import ComponentInstaller


def test_мастер_ставит_закреплённую_версию_yt_dlp(tmp_path: Path) -> None:
    """R3: закреплённая версия доезжает до владельца тем пакетом, что в каталоге."""
    recorded = tmp_path / "pip-args.txt"
    stub_python = tmp_path / "python"
    stub_python.write_text(
        f'#!/bin/sh\necho "$@" > "{recorded}"\nexit 0\n',
        encoding="utf-8",
    )
    stub_python.chmod(0o755)

    spec = component_by_id("yt-dlp")
    assert spec is not None
    installer = ComponentInstaller(python=stub_python, user_root=tmp_path / "components")

    result = installer.install(spec)

    assert result.ok, result.message
    assert "yt-dlp==2026.11.23" in recorded.read_text(encoding="utf-8")
