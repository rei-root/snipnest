"""Версии компонентов: что именно закреплено в каталоге.

Требования, которые закрывают эти проверки:

* R1 — бизнес-контекст: YouTube отдаёт ролику только картинки, пока закреплена
  сломанная версия yt-dlp — исправление пришло в 2026.11.23;
* R4 — бизнес-правила: обновляется только yt-dlp, остальные компоненты остаются
  на прежних версиях;
* R6 — границы: провайдер PO-токена в задачу не входит.
"""

from __future__ import annotations

from snipnest.components.catalog import component_by_id


def test_закреплена_версия_с_исправлением_n_challenge() -> None:
    """R1: закреплена ровно та версия, где исправлен n challenge."""
    spec = component_by_id("yt-dlp")
    assert spec is not None
    assert spec.packages[0].split("==")[-1] == "2026.11.23"


def test_версия_gallery_dl_осталась_прежней() -> None:
    """R4, R6: обновляется только yt-dlp — остальные компоненты не трогаем."""
    spec = component_by_id("gallery-dl")
    assert spec is not None
    assert spec.packages == ("gallery-dl==1.32.20",)
