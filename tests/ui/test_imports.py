"""Регрессия: модули должны импортироваться независимо от порядка."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

MODULES = ("gallary_downloader.manager", "gallary_downloader.jobs", "gallary_downloader.ui")


def test_изоляционный_импорт_модулей() -> None:
    root = Path(__file__).parents[2]
    src = root / "src"
    for module in MODULES:
        result = subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            cwd=root,
            env={"PYTHONPATH": str(src), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{module}: {result.stderr}"
