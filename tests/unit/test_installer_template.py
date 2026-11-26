"""Шаблон установщика: в нём нет пути, который apt не понимает.

Проверяется исходник скрипта, а не его поведение: путь, который установщик
передаёт apt, строится в одном месте, и ошибка в нём видна сразу.
"""

from __future__ import annotations

from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / "packaging" / "installer" / "snipnest-installer.sh"


def test_в_шаблоне_нет_префикса_точка_перед_путём_к_пакету() -> None:
    """«./» перед абсолютным путём даёт «.//tmp/…» — apt такой файл не берёт."""
    body = TEMPLATE.read_text(encoding="utf-8")

    assert '"./$file"' not in body
    assert '"./$stage"' not in body
    assert '"./$package"' not in body


def test_в_шаблоне_есть_абсолютный_путь_для_apt() -> None:
    """apt принимает абсолютный путь к пакету как есть."""
    body = TEMPLATE.read_text(encoding="utf-8")

    assert "apt_path" in body
    assert "/*) printf" in body


def test_в_шаблоне_есть_запасной_путь_через_dpkg() -> None:
    """Если apt-get не справился, пакет ставится через dpkg."""
    body = TEMPLATE.read_text(encoding="utf-8")

    assert "dpkg -i" in body


def test_в_справке_сказано_про_исполняемый_бит() -> None:
    """Файл из релиза приходит без исполняемого бита — про chmod +x надо сказать."""
    body = TEMPLATE.read_text(encoding="utf-8")

    assert "chmod +x" in body
