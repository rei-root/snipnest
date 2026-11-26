"""Релиз целиком: по тегу версии CI собирает артефакты и публикует их.

Проверяется та часть релиза, которая в репозитории: что сборка запускается
по тегу, что в релиз попадают установщик, образ и пакет и что текст релиза
рассказывает человеку про графический установщик.
"""

from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "release.yml"


def test_сборка_релиза_запускается_по_тегу() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")

    assert "tags:" in body
    assert '- "v*"' in body


def test_в_релизе_есть_установщик_образ_и_пакет() -> None:
    body = WORKFLOW.read_text(encoding="utf-8")

    assert "dist/snipnest-installer-*.bin" in body
    assert "dist/*.AppImage" in body
    assert "dist/*.deb" in body
    assert "dist/SHA256SUMS" in body


def test_текст_релиза_рассказывает_про_графический_установщик() -> None:
    """Человек читает текст релиза до запуска — он должен знать про chmod и окно."""
    body = WORKFLOW.read_text(encoding="utf-8")

    assert "chmod +x snipnest-installer-linux-amd64.bin" in body
    assert "графическая программа" in body
