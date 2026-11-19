"""Поиск установленного компонента: каталог человека, пакет .deb, PATH."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .catalog import ComponentKind, ComponentSpec, component_by_id
from .paths import component_dir, system_components_root, user_components_root

__all__ = ["ComponentLocation", "find_component", "find_component_by_id"]


@dataclass(frozen=True)
class ComponentLocation:
    """Где нашёлся компонент.

    ``path`` — каталог пакета для Python-компонентов и исполняемый файл
    для бинарных. ``source`` — откуда нашлось: ``user``, ``system`` или
    ``path`` (нашлось в PATH).
    """

    path: Path
    source: str


def _in_root(spec: ComponentSpec, root: Path, source: str) -> ComponentLocation | None:
    """Компонент внутри одного корня компонентов."""
    folder = component_dir(spec.id, root=root)
    if spec.kind is ComponentKind.PIP:
        module_dir = folder / spec.module
        if module_dir.is_dir():
            return ComponentLocation(module_dir, source)
        return None
    binary = folder / "bin" / spec.binary
    if binary.is_file():
        return ComponentLocation(binary, source)
    return None


def find_component(
    spec: ComponentSpec,
    *,
    user_root: Path | None = None,
    system_root: Path | None = None,
) -> ComponentLocation | None:
    """Найти установленный компонент или None, если его нет."""
    roots = (
        (user_root if user_root is not None else user_components_root(), "user"),
        (system_root if system_root is not None else system_components_root(), "system"),
    )
    for root, source in roots:
        location = _in_root(spec, root, source)
        if location is not None:
            return location
    if spec.binary:
        found = shutil.which(spec.binary)
        if found:
            return ComponentLocation(Path(found), "path")
    return None


def find_component_by_id(
    component_id: str,
    *,
    user_root: Path | None = None,
    system_root: Path | None = None,
) -> ComponentLocation | None:
    """Найти компонент по идентификатору."""
    spec = component_by_id(component_id)
    if spec is None:
        return None
    return find_component(spec, user_root=user_root, system_root=system_root)
