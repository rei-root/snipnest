"""Права администратора через polkit.

Пароль спрашивает система: pkexec показывает свой диалог (на KDE — polkit-
агент), а установщик только говорит, что будет сделано.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .worker import InstallReport, InstallRequest, StepResult

__all__ = [
    "PKEXEC",
    "pkexec_available",
    "run_privileged",
    "worker_command",
]

#: Программа, которая спрашивает пароль и выполняет команду от root.
PKEXEC = "pkexec"

#: Коды возврата pkexec: человек закрыл диалог / не разрешил.
EXIT_DISMISSED = 126
EXIT_DENIED = 127

#: Флаг, которым собранный установщик зовёт работника с правами.
WORKER_FLAG = "--root-worker"


def pkexec_available() -> bool:
    """Есть ли в системе pkexec."""
    return shutil.which(PKEXEC) is not None


def worker_command(request_path: Path) -> list[str]:
    """Команда, которая выполнит установку с правами root."""
    if getattr(sys, "frozen", False):
        return [sys.executable, WORKER_FLAG, str(request_path)]
    return [sys.executable, "-m", "snipnest.installer", WORKER_FLAG, str(request_path)]


def _worker_env() -> dict[str, str]:
    """Окружение для работника: под polkit оно пустое."""
    env = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "HOME": "/root",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
    }
    if not getattr(sys, "frozen", False):
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])
    return env


def _parse_report(output: str) -> InstallReport:
    """Разобрать отчёт работника."""
    try:
        raw = json.loads(output)
    except json.JSONDecodeError:
        return InstallReport(
            ok=False,
            steps=[StepResult("установка", False, "работник не ответил понятным отчётом")],
        )
    steps = [
        StepResult(
            name=str(step.get("name", "")),
            ok=bool(step.get("ok")),
            message=str(step.get("message", "")),
        )
        for step in raw.get("steps", [])
    ]
    return InstallReport(ok=bool(raw.get("ok")), steps=steps)


def run_privileged(request: InstallRequest) -> InstallReport:
    """Выполнить установку с правами администратора.

    Возвращает отчёт: если polkit недоступен или человек отказал, отчёт
    говорит об этом, а не роняет установщик.
    """
    program = shutil.which(PKEXEC)
    if program is None:
        return InstallReport(
            ok=False,
            steps=[
                StepResult(
                    "права администратора",
                    False,
                    "в системе нет pkexec — поставьте без прав администратора",
                )
            ],
        )
    with tempfile.TemporaryDirectory(prefix="snipnest-install-") as tmp:
        request_path = Path(tmp) / "request.json"
        request_path.write_text(request.to_json(), encoding="utf-8")
        request_path.chmod(0o644)
        # Путь к pkexec — абсолютный: у polkit действие выбирается по пути
        # программы, а окружение работника намеренно пустое.
        command = [program, *worker_command(request_path)]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                env=_worker_env(),
            )
        except OSError as error:
            return InstallReport(
                ok=False,
                steps=[StepResult("права администратора", False, str(error))],
            )
    if completed.returncode == EXIT_DISMISSED:
        return InstallReport(
            ok=False,
            steps=[
                StepResult("права администратора", False, "пароль не введён — установка отменена")
            ],
        )
    if completed.returncode == EXIT_DENIED:
        detail = (completed.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else "polkit не разрешил запуск"
        return InstallReport(ok=False, steps=[StepResult("права администратора", False, reason)])
    return _parse_report(completed.stdout)
