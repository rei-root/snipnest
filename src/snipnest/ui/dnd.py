"""Поддержка drag-and-drop: ссылка из браузера падает в поле ссылки."""

from __future__ import annotations

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QWidget

__all__ = ["DropTargetMixin", "extract_url"]

_URL_PREFIXES = ("http://", "https://")


def extract_url(mime: QMimeData) -> str:
    """Достать первую ссылку из данных перетаскивания."""
    for handle in mime.urls():
        text = handle.toString()
        if text.startswith(_URL_PREFIXES):
            return text
    candidate = mime.text().strip()
    if candidate.startswith(_URL_PREFIXES):
        return candidate
    return ""


class DropTargetMixin:
    """Приём ссылки, перетащенной из браузера.

    Подмешивается в окно: обработчики Qt обязаны называться как в Qt.
    """

    def _accept_dropped_link(self, url: str) -> None:
        """Показать, что ссылка принята. Переопределяется в окне."""

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Принять перетаскивание ссылки из браузера."""
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Вставить перетащенную ссылку в поле."""
        url = extract_url(event.mimeData())
        if not url:
            return
        self._accept_dropped_link(url)
        event.acceptProposedAction()


_ = QWidget
