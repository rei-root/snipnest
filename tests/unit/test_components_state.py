"""Состояние компонентов: что установлено и показывался ли мастер."""

from __future__ import annotations

import json

from snipnest.components.state import ComponentState


def test_изначально_мастер_не_показывался(tmp_path) -> None:
    state = ComponentState(tmp_path / "components.json")

    assert not state.wizard_done


def test_отметка_мастера_сохраняется(tmp_path) -> None:
    path = tmp_path / "components.json"
    state = ComponentState(path)
    state.mark_wizard_done()
    state.save()

    assert ComponentState(path).wizard_done


def test_установленные_компоненты_запоминаются(tmp_path) -> None:
    path = tmp_path / "components.json"
    state = ComponentState(path)
    state.mark_installed("gallery-dl", "1.32.20")
    state.save()

    restored = ComponentState(path)
    assert restored.installed["gallery-dl"] == "1.32.20"


def test_битое_состояние_не_ломает_запуск(tmp_path) -> None:
    path = tmp_path / "components.json"
    path.write_text("{ это не json", encoding="utf-8")

    state = ComponentState(path)

    assert not state.wizard_done
    assert state.installed == {}


def test_файл_состояния_читается_как_json(tmp_path) -> None:
    path = tmp_path / "components.json"
    state = ComponentState(path)
    state.mark_wizard_done()
    state.save()

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["wizard_done"] is True
