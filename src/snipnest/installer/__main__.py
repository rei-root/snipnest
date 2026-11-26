"""Точка входа установщика.

Обычно это окно. С ключом ``--root-worker ФАЙЛ`` тот же самый запущенный файл
делает установку с правами администратора: так его зовёт polkit.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .elevate import WORKER_FLAG
from .worker import read_request, run_install

__all__ = ["main"]


def _run_worker(request_path: str) -> int:
    """Выполнить установку с правами и отдать отчёт в stdout."""
    try:
        request = read_request(Path(request_path))
    except (OSError, KeyError, ValueError) as error:
        sys.stdout.write(
            '{"ok": false, "steps": [{"name": "запрос", "ok": false, "message": "'
            + str(error)
            + '"}]}'
        )
        return 1
    report = run_install(request)
    sys.stdout.write(report.to_json())
    return 0 if report.ok else 1


def main(argv: list[str] | None = None) -> int:
    """Точка входа. Возвращает код завершения."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == WORKER_FLAG:
        if len(args) < 2:
            sys.stdout.write(
                '{"ok": false, "steps": [{"name": "запрос", "ok": false, '
                '"message": "не указан файл запроса"}]}'
            )
            return 1
        return _run_worker(args[1])
    # Qt нужен только окну: работник с правами его не трогает.
    from .app import run

    return run()


if __name__ == "__main__":
    sys.exit(main())
