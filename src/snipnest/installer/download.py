"""Скачивание образа приложения и проверка по SHA256SUMS.

Сеть открывает не приложение, а внешняя программа: загрузку делает curl
(запасной путь — wget). Правило проекта «приложение само никуда не ходит»
остаётся в силе и для установщика.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..components.installer import download_file

__all__ = ["fetch_image", "sha256_of"]


def sha256_of(path: Path) -> str:
    """Контрольная сумма файла."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_sum(sums_path: Path, name: str) -> str:
    """Ожидаемая сумма из файла SHA256SUMS."""
    for line in sums_path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        digest, _, file_name = parts[1].partition("*")
        if file_name.strip() == name:
            return digest.strip()
    return ""


def fetch_image(release_url: str, name: str, target: Path) -> None:
    """Скачать образ приложения и проверить его по SHA256SUMS.

    Если файла с суммами нет или суммы не совпали, установка не идёт дальше:
    лучше явное сообщение, чем битый образ.
    """
    image = target / name
    download_file(f"{release_url}/{name}", image)
    sums = target / "SHA256SUMS"
    try:
        download_file(f"{release_url}/SHA256SUMS", sums)
    except OSError:
        raise OSError("не удалось скачать SHA256SUMS — образ не проверен") from None
    expected = _expected_sum(sums, name)
    actual = sha256_of(image)
    if not expected:
        raise OSError(f"в SHA256SUMS нет файла {name} — образ не проверен")
    if expected != actual:
        raise OSError("контрольная сумма образа не совпала: файл повреждён или подменён")
