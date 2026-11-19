"""Поставить компоненты Snipnest в каталог.

Скрипт сборки .deb: компоненты должны быть внутри пакета, чтобы после
установки приложение работало без сети.

    uv run python packaging/install-components.py <каталог> \\
        --python <интерпретатор сборки> \\
        --launcher-python <путь в пакете> --launcher-root <корень в пакете>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    """Загрузить модули приложения: из venv или из исходников."""
    try:
        from snipnest.components.catalog import COMPONENTS
        from snipnest.components.installer import ComponentInstaller
    except ImportError:
        sys.path.insert(0, str(ROOT / "src"))
        from snipnest.components.catalog import COMPONENTS
        from snipnest.components.installer import ComponentInstaller
    return COMPONENTS, ComponentInstaller


def main() -> int:
    """Поставить все компоненты каталога. Возвращает код завершения."""
    components, installer_class = _load()
    parser = argparse.ArgumentParser(description="поставить компоненты Snipnest")
    parser.add_argument("target", help="каталог компонентов")
    parser.add_argument("--python", default="", help="интерпретатор для pip")
    parser.add_argument("--launcher-python", default="", help="Python в запускающем файле")
    parser.add_argument(
        "--launcher-root", default="", help="корень компонентов в запускающем файле"
    )
    args = parser.parse_args()

    installer = installer_class(
        python=Path(args.python) if args.python else None,
        user_root=Path(args.target),
        launcher_python=Path(args.launcher_python) if args.launcher_python else None,
        launcher_root=Path(args.launcher_root) if args.launcher_root else None,
    )
    failed = False
    for spec in components:
        result = installer.install(spec, lambda text: print(text, flush=True))
        print(f"{spec.id}: {'ок' if result.ok else 'ошибка — ' + result.message}", flush=True)
        failed = failed or not result.ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
