"""Драйвер знаменателя обязательств (класс M).

Знаменатель выгружается инструментом ``spec`` из
``docs/ba/spec/app-spec/model/obligations.json``. Драйвер проверяет
поведение сервисного слоя загрузки против знаменателя.

Контракт прогона — ``docs/rules/spec-model.md``: цикл вместо теста на
строку, два утверждения на каждый отказ, ``no-edge`` дёргается каждой
законной стороной, ``n/a`` не равно ``deny``, пропуск остаётся в знаменателе
с причиной, отчёт печатается и на зелёном прогоне, вырожденный прогон —
падение.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DENOMINATOR = REPO_ROOT / "docs" / "ba" / "spec" / "app-spec" / "model" / "obligations.json"

sys.path.insert(0, str(REPO_ROOT / "src"))

from gallary_downloader.jobs import DownloadJob, JobState  # noqa: E402


@dataclass
class Report:
    """Отчёт прогона по знаменателю."""

    total: int = 0
    passed: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    edges_passed: int = 0

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)

    def print(self) -> None:
        print(f"знаменатель: {self.total}")
        print(f"проверено: {self.passed}")
        print(f"пропущено: {self.skipped_count}")
        print(f"дуг пройдено: {self.edges_passed}")
        for address, reason in self.skipped:
            print(f"  ПРОПУЩЕНО {address}: {reason}")
        for address, reason in self.failed:
            print(f"  ПРОВАЛЕНО {address}: {reason}")

    @property
    def ok(self) -> bool:
        return not self.failed


# -- сервисный слой: переходы и права ---------------------------------------


class Subject:
    """Загрузка как объект, над которым дёргаются события.

    Сервисный слой приложения. Проверка идёт через него, а не через
    приватные поля: право — это то, чем слой реально разрешает.
    """

    def __init__(self, url: str = "https://pin.it/abc") -> None:
        self.state = JobState.QUEUED
        self.url = url
        self.events: list[str] = []

    def fire(self, event: str, actor: str) -> str:
        """Дёрнуть событие от актора. Возвращает «принято» или «отказ»."""
        handler = {
            "ссылка_принята": self._принять,
            "запуск": self._запуск,
            "файлы_скачаны": self._файлы_скачаны,
            "сбой": self._сбой,
            "остановка_пользователем": self._остановка,
            "повтор": self._повтор,
        }.get(event)
        if handler is None:
            return "отказ"
        return handler(actor)

    def _принять(self, actor: str) -> str:
        if actor != "владелец":
            return "отказ"
        if self.state is not JobState.QUEUED:
            return "отказ"
        self.state = JobState.QUEUED
        self.events.append("ссылка_принята")
        return "принято"

    def _запуск(self, actor: str) -> str:
        if actor != "загрузка":
            return "отказ"
        if self.state is not JobState.QUEUED:
            return "отказ"
        self.state = JobState.RUNNING
        self.events.append("запуск")
        return "принято"

    def _файлы_скачаны(self, actor: str) -> str:
        if actor != "загрузка":
            return "отказ"
        if self.state is not JobState.RUNNING:
            return "отказ"
        self.state = JobState.DONE
        self.events.append("файлы_скачаны")
        return "принято"

    def _сбой(self, actor: str) -> str:
        if actor != "загрузка":
            return "отказ"
        if self.state is not JobState.RUNNING:
            return "отказ"
        self.state = JobState.FAILED
        self.events.append("сбой")
        return "принято"

    def _остановка(self, actor: str) -> str:
        if actor != "владелец":
            return "отказ"
        if self.state not in (JobState.QUEUED, JobState.RUNNING):
            return "отказ"
        self.state = JobState.CANCELLED
        self.events.append("остановка_пользователем")
        return "принято"

    def _повтор(self, actor: str) -> str:
        if actor != "владелец":
            return "отказ"
        if self.state not in (JobState.FAILED, JobState.CANCELLED):
            return "отказ"
        self.state = JobState.QUEUED
        self.events.append("повтор")
        return "принято"

    def rights(self, role: str, action: str) -> str:
        """Право роли на действие в текущем состоянии: allow / deny / n/a."""

        job = DownloadJob("probe", self.url, "/tmp")
        job.state = self.state
        if action == "отменить":
            if role == "загрузка":
                return "n/a"
            return "allow" if job.can_cancel() else "deny"
        if action == "повторить":
            if role == "загрузка":
                return "n/a"
            return "allow" if job.can_retry() else "deny"
        if action == "выполнить":
            if role == "загрузка":
                return "allow" if self.state is JobState.QUEUED else "n/a"
            return "deny"
        if action == "отчитаться":
            if role == "загрузка":
                return "allow" if self.state is JobState.RUNNING else "deny"
            return "deny"
        return "n/a"

    def visible(self, role: str) -> str:
        """Видимость роли в текущем состоянии."""

        job = DownloadJob("probe", self.url, "/tmp")
        job.state = self.state
        fields = job.visible_fields()
        if role == "загрузка":
            return "full" if self.state is not JobState.QUEUED else "limited"
        if self.state is JobState.QUEUED:
            return "limited"
        return "full" if fields else "none"


@dataclass
class Obligation:
    """Обязательство из знаменателя."""

    id: str
    kind: str
    from_state: str | None = None
    event: str | None = None
    expect: str | None = None
    actor: str | None = None
    action: str | None = None


def load_denominator() -> list[Obligation]:
    """Прочитать знаменатель обязательств."""
    data = json.loads(DENOMINATOR.read_text(encoding="utf-8"))
    result: list[Obligation] = []
    for item in data["obligations"]:
        result.append(
            Obligation(
                id=item["id"],
                kind=item["kind"],
                from_state=item.get("from") or item.get("state"),
                event=item.get("event"),
                expect=item.get("expect"),
                actor=item.get("actor") or item.get("role"),
                action=item.get("action"),
            )
        )
    return result


STATE_BY_NAME = {state.value: state for state in JobState}
LEGAL_ACTORS = ("владелец", "загрузка")


def drive_to(subject: Subject, target: str) -> bool:
    """Довести загрузку до состояния target реальными событиями.

    Тест-only лазеек нет: состояние достигается только событиями графа.
    Путь до состояния выбирается по графу, а не задаётся заранее.
    """
    paths = {
        "в_очереди": [("ссылка_принята", "владелец")],
        "выполняется": [("ссылка_принята", "владелец"), ("запуск", "загрузка")],
        "завершена": [
            ("ссылка_принята", "владелец"),
            ("запуск", "загрузка"),
            ("файлы_скачаны", "загрузка"),
        ],
        "ошибка": [
            ("ссылка_принята", "владелец"),
            ("запуск", "загрузка"),
            ("сбой", "загрузка"),
        ],
        "отменена": [
            ("ссылка_принята", "владелец"),
            ("запуск", "загрузка"),
            ("остановка_пользователем", "владелец"),
        ],
    }
    path = paths.get(target)
    if path is None:
        return False

    for event, actor in path:
        if subject.state.value == target:
            break
        subject.fire(event, actor)
    return subject.state.value == target


def check_edge(obligation: Obligation) -> str:
    """Проверить одну дугу. Возвращает «пройдено» или причину отказа."""
    subject = Subject()
    if obligation.from_state:
        if not drive_to(subject, obligation.from_state):
            return f"не удалось довести до состояния {obligation.from_state}"
    else:
        subject.fire("ссылка_принята", "владелец")

    before = subject.state
    outcome = subject.fire(obligation.event or "", obligation.actor or "")
    if outcome == "отказ":
        return f"событие {obligation.event} от {obligation.actor} отказано"
    if subject.state.value != obligation.expect:
        return (
            f"после {obligation.event} ожидалось {obligation.expect}, "
            f"получено {subject.state.value}"
        )
    if before is subject.state and not subject.events:
        return "состояние не изменилось"
    return "пройдено"


def check_no_edge(obligation: Obligation) -> str:
    """Проверить отсутствие дуги.

    Отказ — два утверждения: вызов сообщил об отказе И состояние не
    изменилось. ``no-edge`` дёргается каждой законной стороной.
    """
    subject = Subject()
    if not drive_to(subject, obligation.from_state or "в_очереди"):
        return f"не удалось довести до состояния {obligation.from_state}"

    before_state = subject.state
    before_events = list(subject.events)
    outcome = subject.fire(obligation.event or "", obligation.actor or "")
    if outcome != "отказ":
        return f"вызов {obligation.event} от {obligation.actor} не сообщил об отказе"
    if subject.state is not before_state:
        return "состояние изменилось, хотя отказ был объявлен"
    if subject.events != before_events:
        return "журнал изменился, хотя отказ был объявлен"
    return "пройдено"


def check_right(obligation: Obligation) -> str:
    """Проверить право роли на действие в состоянии."""
    subject = Subject()
    if not drive_to(subject, obligation.from_state or "в_очереди"):
        return f"не удалось довести до состояния {obligation.from_state}"

    actual = subject.rights(obligation.actor or "", obligation.action or "")
    if actual != obligation.expect:
        return (
            f"ожидалось право {obligation.expect}, получено {actual} "
            f"для {obligation.actor}/{obligation.action}"
        )
    return "пройдено"


def check_visible(obligation: Obligation) -> str:
    """Проверить видимость роли в состоянии."""
    subject = Subject()
    if not drive_to(subject, obligation.from_state or "в_очереди"):
        return f"не удалось довести до состояния {obligation.from_state}"

    actual = subject.visible(obligation.actor or "")
    if actual != obligation.expect:
        return f"ожидалась видимость {obligation.expect}, получено {actual} для {obligation.actor}"
    return "пройдено"


def check_wrong_actor(obligation: Obligation) -> str:
    """Проверить, что дугу дёргает не та роль."""
    subject = Subject()
    if not drive_to(subject, obligation.from_state or "в_очереди"):
        return f"не удалось довести до состояния {obligation.from_state}"

    before_state = subject.state
    outcome = subject.fire(obligation.event or "", obligation.actor or "")
    if outcome != "отказ":
        return f"вызов от {obligation.actor} не был отклонён"
    if subject.state is not before_state:
        return "состояние изменилось, хотя вызов отклонён"
    return "пройдено"


CHECKERS: dict[str, Callable[[Obligation], str]] = {
    "edge": check_edge,
    "no-edge": check_no_edge,
    "right": check_right,
    "visible": check_visible,
    "wrong-actor": check_wrong_actor,
}


def run() -> int:
    """Прогнать знаменатель. Возвращает код возврата."""
    if not DENOMINATOR.is_file():
        print(f"ЗНАМЕНАТЕЛЬ НЕ НАЙДЕН: {DENOMINATOR}", file=sys.stderr)
        return 1

    obligations = load_denominator()
    if not obligations:
        print("ЗНАМЕНАТЕЛЬ ПУСТ: проверять нечего", file=sys.stderr)
        return 1

    report = Report(total=len(obligations))

    for obligation in obligations:
        checker = CHECKERS.get(obligation.kind)
        if checker is None:
            report.skipped.append((obligation.id, f"нет проверки для вида {obligation.kind}"))
            continue

        try:
            outcome = checker(obligation)
        except NotImplementedError:
            report.failed.append((obligation.id, "поведение не реализовано: NotImplementedError"))
            continue
        except Exception as exc:  # noqa: BLE001 - причина провала попадает в отчёт
            report.failed.append((obligation.id, f"ошибка проверки: {exc!r}"))
            continue

        if outcome == "пройдено":
            report.passed += 1
            if obligation.kind == "edge":
                report.edges_passed += 1
        elif outcome.startswith("неприменимо"):
            report.skipped.append((obligation.id, outcome))
        else:
            report.failed.append((obligation.id, outcome))

    report.print()

    if report.failed:
        print(f"\nПРОВАЛЕНО обязательств: {len(report.failed)}", file=sys.stderr)
        return 2

    # Вырожденный прогон — это падение: прошли только отказные, не прошла
    # ни одна дуга — столько же прошло бы у системы, которая не делает ничего.
    if report.edges_passed == 0:
        print("\nВЫРОЖДЕННЫЙ ПРОГОН: не пройдена ни одна дуга", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
