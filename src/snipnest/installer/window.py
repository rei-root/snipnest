"""Окно установщика.

Человек видит, что определила система, что будет поставлено и куда, может
снять галочки с лишних зависимостей и нажимает «Установить». Работа идёт в
отдельном потоке: скачивание образа занимает время, окно не должно висеть.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .dependencies import dependencies_for, package_command, package_names
from .detect import Family, detect_family, glibc_version, version_at_least
from .download import fetch_image
from .elevate import pkexec_available, run_privileged
from .plan import InstallPlan, Mode, build_plan
from .worker import InstallReport, InstallRequest, StepResult, run_install

__all__ = ["InstallerContext", "InstallerWindow", "make_context"]

WINDOW_TITLE = "Snipnest — установщик"


@dataclass(frozen=True)
class InstallerContext:
    """Всё, что установщик знает о системе и о себе."""

    version: str
    family: Family
    glibc: str
    min_glibc: str
    release_url: str

    def glibc_ok(self) -> bool:
        """Годится ли glibc для приложения."""
        return version_at_least(self.glibc, self.min_glibc)


def make_context(version: str, min_glibc: str, release_url: str) -> InstallerContext:
    """Собрать сведения о системе по умолчанию."""
    return InstallerContext(
        version=version,
        family=detect_family(),
        glibc=glibc_version(),
        min_glibc=min_glibc,
        release_url=release_url,
    )


class _InstallWorker(QObject):
    """Установка в отдельном потоке."""

    message = Signal(str)
    progress = Signal(int)
    finished = Signal(object)

    def __init__(self, context: InstallerContext, mode: Mode, dependency_ids: list[str]) -> None:
        super().__init__()
        self._context = context
        self._mode = mode
        self._dependency_ids = dependency_ids

    def run(self) -> None:
        """Скачать образ и поставить его."""
        try:
            self._install()
        except OSError as error:
            self.finished.emit(
                InstallReport(ok=False, steps=[_failed_step("скачивание", str(error))])
            )

    def _install(self) -> None:
        """Скачать образ, затем поставить его (с правами или без)."""
        plan = build_plan(
            self._mode,
            self._context.family,
            version=self._context.version,
            glibc=self._context.min_glibc,
        )
        self.message.emit(f"Качаю образ приложения ({plan.image_name})…")
        self.progress.emit(10)
        with tempfile.TemporaryDirectory(prefix="snipnest-installer-") as tmp:
            fetch_image(self._context.release_url, plan.image_name, Path(tmp))
            self.progress.emit(60)
            packages = package_names(self._context.family, self._dependency_ids)
            command = package_command(self._context.family, packages)
            request = InstallRequest(
                image_path=str(Path(tmp) / plan.image_name),
                image_name=plan.image_name,
                app_dir=str(plan.app_dir),
                bin_dir=str(plan.bin_dir),
                desktop_dir=str(plan.desktop_dir),
                icons_dir=str(plan.icons_dir),
                packages=tuple(packages),
                package_command=tuple(command),
            )
            self.message.emit("Ставлю приложение…")
            self.progress.emit(80)
            if plan.needs_root or packages:
                report = run_privileged(request)
            else:
                report = run_install(request)
        self.progress.emit(100)
        self.finished.emit(report)


def _failed_step(name: str, message: str) -> StepResult:
    """Шаг, который не получился."""
    return StepResult(name, False, message)


class InstallerWindow(QWidget):
    """Окно установщика."""

    def __init__(self, context: InstallerContext | None = None) -> None:
        super().__init__()
        self._context = context or make_context("0.2.0", "2.38", "")
        self._thread: QThread | None = None
        self._worker: _InstallWorker | None = None
        self.setWindowTitle(WINDOW_TITLE)
        self._build()

    # --- построение ---------------------------------------------------------

    def _build(self) -> None:
        """Собрать окно."""
        layout = QVBoxLayout(self)

        self._system_label = QLabel(self._system_text())
        self._system_label.setWordWrap(True)
        layout.addWidget(self._system_label)

        mode_box = QGroupBox("Куда поставить")
        mode_layout = QVBoxLayout(mode_box)
        self._system_radio = QRadioButton("Для всех пользователей (нужны права администратора)")
        self._user_radio = QRadioButton("Только для себя (без прав администратора)")
        self._system_radio.setChecked(True)
        self._modes = QButtonGroup(self)
        self._modes.addButton(self._system_radio)
        self._modes.addButton(self._user_radio)
        mode_layout.addWidget(self._system_radio)
        mode_layout.addWidget(self._user_radio)
        layout.addWidget(mode_box)
        self._system_radio.toggled.connect(self._refresh)
        self._user_radio.toggled.connect(self._refresh)

        self._plan_label = QLabel()
        self._plan_label.setWordWrap(True)
        layout.addWidget(self._plan_label)

        self._dependencies = QTreeWidget()
        self._dependencies.setHeaderLabels(["Зависимость", "Пакет"])
        layout.addWidget(self._dependencies)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._status = QLabel("Готов к установке.")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        buttons = QHBoxLayout()
        self._install_button = QPushButton("Установить")
        self._install_button.clicked.connect(self._start)
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        buttons.addStretch(1)
        buttons.addWidget(self._install_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self._refresh()

    # --- состояние ----------------------------------------------------------

    def system_text(self) -> str:
        """Строка о системе — что установщик определил."""
        return self._system_label.text()

    def plan_text(self) -> str:
        """Текст плана установки: что и куда кладётся."""
        return self._plan_label.text()

    def dependency_widget(self) -> QTreeWidget:
        """Дерево зависимостей с галочками."""
        return self._dependencies

    def status_text(self) -> str:
        """Текущее состояние установки."""
        return self._status.text()

    def install_button(self) -> QPushButton:
        """Кнопка установки."""
        return self._install_button

    def set_mode(self, mode: Mode) -> None:
        """Выбрать режим установки."""
        self._system_radio.setChecked(mode is Mode.SYSTEM)
        self._user_radio.setChecked(mode is Mode.USER)

    def worker_thread(self) -> QThread | None:
        """Поток, в котором идёт установка."""
        return self._thread

    def install(self, dependencies: list[str]) -> None:
        """Начать установку: работа идёт в отдельном потоке."""
        self._install_button.setEnabled(False)
        self._progress.setValue(0)
        self._run(self._plan().needs_root, dependencies)

    def _system_text(self) -> str:
        """Строка о системе."""
        context = self._context
        glibc = context.glibc or "неизвестно"
        text = f"Система: {context.family.title}, glibc {glibc} (нужен не ниже {context.min_glibc})"
        if not context.glibc_ok():
            text += " — на этой системе приложение не запустится"
        if not pkexec_available():
            text += "; pkexec в системе нет — доступна установка только для себя"
        return text

    def _mode(self) -> Mode:
        """Выбранный режим установки."""
        return Mode.SYSTEM if self._system_radio.isChecked() else Mode.USER

    def _plan(self) -> InstallPlan:
        """План установки для текущего режима."""
        return build_plan(
            self._mode(),
            self._context.family,
            version=self._context.version,
            glibc=self._context.min_glibc,
        )

    def _refresh(self) -> None:
        """Обновить план и список зависимостей."""
        plan = self._plan()
        lines = ["Будет поставлено:"]
        lines.extend(f"  {path} — {what}" for path, what in plan.destinations())
        self._plan_label.setText("\n".join(lines))
        self._fill_dependencies()
        self._install_button.setEnabled(self._context.glibc_ok())

    def _fill_dependencies(self) -> None:
        """Пересобрать список зависимостей с галочками."""
        self._dependencies.clear()
        for dependency in dependencies_for(self._context.family):
            item = QTreeWidgetItem([dependency.title, dependency.package_for(self._context.family)])
            item.setData(0, 0, dependency.id)
            item.setCheckState(0, Qt.CheckState.Checked)
            self._dependencies.addTopLevelItem(item)

    def selected_dependencies(self) -> list[str]:
        """Идентификаторы отмеченных зависимостей."""
        selected: list[str] = []
        for index in range(self._dependencies.topLevelItemCount()):
            item = self._dependencies.topLevelItem(index)
            if item is None or item.checkState(0) != Qt.CheckState.Checked:
                continue
            identifier = item.data(0, 0)
            if identifier:
                selected.append(str(identifier))
        return selected

    # --- установка ----------------------------------------------------------

    def _start(self) -> None:
        """Начать установку."""
        if not self._context.glibc_ok():
            QMessageBox.warning(
                self,
                WINDOW_TITLE,
                f"На этой системе glibc {self._context.glibc or 'неизвестно'}, "
                f"а программа собрана под {self._context.min_glibc} и новее не запустится.",
            )
            return
        plan = self._plan()
        dependencies = self.selected_dependencies()
        answer = QMessageBox.question(
            self,
            WINDOW_TITLE,
            "Будет поставлено:\n"
            + "\n".join(f"  {path}" for path, _ in plan.destinations())
            + (f"\n\nЗависимости: {', '.join(dependencies)}" if dependencies else ""),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.install(dependencies)

    def _run(self, needs_root: bool, dependencies: list[str]) -> None:
        """Запустить установку в отдельном потоке."""
        self._thread = QThread(self)
        self._worker = _InstallWorker(self._context, self._mode(), dependencies)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.message.connect(self._status.setText)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.finished.connect(self._finished)
        self._thread.start()

    def _finished(self, report: InstallReport) -> None:
        """Показать итог установки."""
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        self._install_button.setEnabled(True)
        if report.ok:
            self._status.setText("Готово. Приложение доступно как snipnest.")
            QMessageBox.information(self, WINDOW_TITLE, "Установка завершена.")
            return
        lines = [step.message or step.name for step in report.steps if not step.ok]
        detail = "\n".join(lines) or "установка не удалась"
        self._status.setText(detail)
        QMessageBox.warning(self, WINDOW_TITLE, f"Установка не удалась:\n{detail}")
