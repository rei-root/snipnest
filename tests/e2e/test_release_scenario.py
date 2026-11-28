"""E2E: релиз собран из версии пакета.

Тест офлайн: запускается та же проверка релиза, что и оракул задачи, —
arteфакты и сеть не нужны.

Требования, которые закрывают эти проверки:

* R3 — требования: версия пакета, имена артефактов и адрес релиза собраны
  из одной версии, прежней версии нигде не осталось;
* AC1 — критерии приёмки: релиз 0.2.3 собран из версии пакета.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK = REPO_ROOT / "bin" / "check-release-version.sh"


def test_проверка_релиза_проходит() -> None:
    """R3, AC1: релиз собран из версии пакета."""
    result = subprocess.run(
        ["bash", str(CHECK)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
