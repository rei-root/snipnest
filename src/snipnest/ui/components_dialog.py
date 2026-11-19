"""Мастер установки компонентов.

Главный пункт дерева — «Обеспечить все компоненты»: одна галочка отмечает
всё сразу. Раскрытие пункта показывает список компонентов, у каждого своя
галочка и своё состояние. Снятие главной галочки снимает все; отметка
части пунктов переводит главный пункт в состояние «частично».
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..components.catalog import COMPONENTS, ComponentSpec
from ..components.finder import ComponentLocation, find_component
from ..components.installer import ComponentInstaller, InstallResult
from ..components.paths import (
    component_dir,
    system_components_root,
    user_components_root,
)

__all__ = ["ComponentsDialog"]

ROOT_TITLE = "Обеспечить все компоненты"
STATUS_INSTALLED = "уже установлен"
STATUS_WILL_DOWNLOAD = "будет скачано"


def _format_size(size: int) -> str:
    """Размер файла для показа человеку."""
    if size <= 0:
        return ""
    return f"{size / (1024 * 1024):.0f} МБ"


class _InstallWorker(QObject):
    """Установка компонентов в отдельном потоке.

    Скачивание ffmpeg занимает минуты, поэтому окно не должно ждать: работа
    идёт в потоке, а события приходят в GUI-поток через сигналы.
    """

    message = Signal(str)
    finished = Signal(list)

    def __init__(self, installer: ComponentInstaller, specs: list[ComponentSpec]) -> None:
        super().__init__()
        self._installer = installer
        self._specs = specs

    def run(self) -> None:
        """Поставить компоненты по очереди."""
        results: list[InstallResult] = []
        for spec in self._specs:
            self.message.emit(f"Устанавливаю {spec.title}…")
            results.append(self._installer.install(spec, self._progress))
        self.finished.emit(results)

    def _progress(self, text: str) -> None:
        """Сообщение о ходе установки."""
        self.message.emit(text)


class ComponentsDialog(QDialog):
    """Диалог со списком компонентов и галочками."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        specs: list[ComponentSpec] | None = None,
        finder: Callable[[ComponentSpec], ComponentLocation | None] | None = None,
        user_root: Path | None = None,
        system_root: Path | None = None,
        installer: ComponentInstaller | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Компоненты Snipnest")
        self.resize(640, 380)

        self._specs = list(specs) if specs is not None else list(COMPONENTS)
        self._user_root = user_root if user_root is not None else user_components_root()
        self._system_root = system_root if system_root is not None else system_components_root()
        self._finder = finder if finder is not None else self._default_finder
        self._installer = installer
        self._updating = False
        self._thread: QThread | None = None
        self._worker: _InstallWorker | None = None

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Отметьте нужные компоненты. Главная галочка отмечает всё сразу; "
            "раскройте список, чтобы выбрать по отдельному.",
            self,
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._tree = QTreeWidget(self)
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Компонент", "Состояние"])
        layout.addWidget(self._tree, 1)

        self._message = QLabel("", self)
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        buttons = QDialogButtonBox(self)
        self._install_button = QPushButton("Установить", self)
        buttons.addButton(self._install_button, QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Close)
        layout.addWidget(buttons)
        buttons.rejected.connect(self.reject)
        self._install_button.clicked.connect(self._on_install_clicked)

        self._build_tree()
        self._tree.itemChanged.connect(self._on_item_changed)

    # -- построение интерфейса ---------------------------------------------

    def _build_tree(self) -> None:
        """Собрать дерево: главный пункт и список компонентов."""
        root = QTreeWidgetItem(self._tree)
        root.setText(0, f"{ROOT_TITLE} ({len(self._specs)})")
        root.setCheckState(0, Qt.CheckState.Checked)
        root.setFlags(root.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self._root = root
        for spec in self._specs:
            item = QTreeWidgetItem(root)
            item.setText(0, spec.title)
            item.setText(1, self._status_text(spec))
            item.setToolTip(0, spec.description)
            item.setData(0, Qt.ItemDataRole.UserRole, spec.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Главная галочка отмечает всё сразу: дети отмечены сразу.
            item.setCheckState(0, Qt.CheckState.Checked)
        self._tree.expandAll()

    def _default_finder(self, spec: ComponentSpec) -> ComponentLocation | None:
        """Найти компонент в каталогах пользователя и пакета."""
        return find_component(spec, user_root=self._user_root, system_root=self._system_root)

    def _status_text(self, spec: ComponentSpec) -> str:
        """Состояние компонента для показа в списке."""
        location = self._finder(spec)
        if location is not None:
            return f"{STATUS_INSTALLED}: {location.path}"
        size = _format_size(spec.size_hint)
        if not size:
            return STATUS_WILL_DOWNLOAD
        return f"{STATUS_WILL_DOWNLOAD}, ~{size}"

    # -- публичный доступ ---------------------------------------------------

    def tree(self) -> QTreeWidget:
        """Дерево компонентов."""
        return self._tree

    def root_item(self) -> QTreeWidgetItem:
        """Главный пункт дерева."""
        return self._root

    def item_for(self, component_id: str) -> QTreeWidgetItem | None:
        """Пункт дерева по идентификатору компонента."""
        for index in range(self._root.childCount()):
            child = self._child(index)
            if child.data(0, Qt.ItemDataRole.UserRole) == component_id:
                return child
        return None

    def _child(self, index: int) -> QTreeWidgetItem:
        """Пункт дерева по номеру."""
        child = self._root.child(index)
        if child is None:
            raise IndexError(f"в дереве нет пункта {index}")
        return child

    def status_for(self, component_id: str) -> str:
        """Состояние компонента по идентификатору."""
        item = self.item_for(component_id)
        return item.text(1) if item is not None else ""

    def set_status(self, component_id: str, text: str) -> None:
        """Обновить состояние компонента."""
        item = self.item_for(component_id)
        if item is not None:
            item.setText(1, text)

    def selected_components(self) -> list[ComponentSpec]:
        """Компоненты с отмеченной галочкой."""
        chosen: list[ComponentSpec] = []
        for index in range(self._root.childCount()):
            child = self._child(index)
            if child.checkState(0) != Qt.CheckState.Checked:
                continue
            component_id = child.data(0, Qt.ItemDataRole.UserRole)
            for spec in self._specs:
                if spec.id == component_id:
                    chosen.append(spec)
        return chosen

    def install_selected(self) -> list[InstallResult]:
        """Установить отмеченные компоненты (без отдельного потока)."""
        results: list[InstallResult] = []
        for spec in self.selected_components():
            result = self._installer_or_default().install(spec, self._set_message)
            results.append(result)
            self._apply_result(spec, result)
        return results

    def start_install(self) -> None:
        """Установить отмеченные компоненты в отдельном потоке.

        Окно остаётся живым: скачивание идёт в потоке, ход установки
        приходит сигналом.
        """
        specs = self.selected_components()
        if not specs:
            self._set_message("Ничего не отмечено")
            return
        self._install_button.setEnabled(False)
        self._thread = QThread(self)
        self._worker = _InstallWorker(self._installer_or_default(), specs)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.message.connect(self._set_message)
        self._worker.finished.connect(self._on_install_finished)
        self._thread.start()

    def _installer_or_default(self) -> ComponentInstaller:
        """Установщик компонентов: заданный или обычный."""
        if self._installer is None:
            self._installer = ComponentInstaller(
                user_root=self._user_root, system_root=self._system_root
            )
        return self._installer

    def _on_install_finished(self, results: list[InstallResult]) -> None:
        """Установка закончилась: показать итог и вернуть кнопку."""
        self._install_button.setEnabled(True)
        for result in results:
            spec = next((item for item in self._specs if item.id == result.component_id), None)
            if spec is not None:
                self._apply_result(spec, result)
        failed = [result for result in results if not result.ok]
        if failed:
            self._set_message(f"Не удалось поставить: {failed[0].message}")
        else:
            self._set_message("Готово")
        if self._thread is not None:
            self._thread.quit()

    def _apply_result(self, spec: ComponentSpec, result: InstallResult) -> None:
        """Показать итог установки в списке."""
        if result.ok:
            self.set_status(spec.id, f"{STATUS_INSTALLED}: {self._target_path(spec)}")
        else:
            self.set_status(spec.id, f"ошибка: {result.message}")

    def _target_path(self, spec: ComponentSpec) -> Path:
        """Каталог, куда встал компонент."""
        return component_dir(spec.id, root=self._user_root)

    # -- работа с галочками ---------------------------------------------------

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Согласовать состояние главного пункта и его детей.

        Qt сам этого не делает: снятие галочки главного пункта не снимает
        галочки детей, а отметка одного ребёнка не переводит главный пункт
        в состояние «частично». Обе стороны считаются здесь.
        """
        if self._updating:
            return
        if item is self._root:
            self._propagate_root_state()
            return
        self._sync_root_state()

    def _propagate_root_state(self) -> None:
        """Главный пункт отмечен — значит отмечены и все дети."""
        state = self._root.checkState(0)
        if state == Qt.CheckState.PartiallyChecked:
            return
        self._updating = True
        for index in range(self._root.childCount()):
            self._child(index).setCheckState(0, state)
        self._updating = False

    def _sync_root_state(self) -> None:
        """Главный пункт отмечен целиком, частично или никак."""
        states = [self._child(index).checkState(0) for index in range(self._root.childCount())]
        if not states:
            return
        if all(state == Qt.CheckState.Checked for state in states):
            state = Qt.CheckState.Checked
        elif all(state == Qt.CheckState.Unchecked for state in states):
            state = Qt.CheckState.Unchecked
        else:
            state = Qt.CheckState.PartiallyChecked
        self._updating = True
        self._root.setCheckState(0, state)
        self._updating = False

    def _on_install_clicked(self) -> None:
        """Кнопка «Установить»: работа идёт в отдельном потоке."""
        self.start_install()

    def _set_message(self, text: str) -> None:
        """Показать строку сообщения."""
        self._message.setText(text)
