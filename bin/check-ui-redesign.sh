#!/usr/bin/env bash
# Оракул задачи 014-ui-redesign: аватарка, меню, тема и оформление.
#
# Возвращает 0 тогда и только тогда, когда критерии выполнены. Печатает имя
# упавшего критерия и причину.
#
# Критерии проверяются тестами задачи: логотип и символ на месте, иконка
# приложения рисуется из SVG, строка меню с нужным составом, кнопки настроек
# переехали в меню, «Открыть Pinterest» удалена, окно настроек открывается из
# меню, тема переключается и помнится, символ перекрашивается по теме, строки
# загрузок и лог появляются плавно — и всё это вместе с линтером, типами и
# знаменателем обязательств.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

TESTS=(
  tests/unit/test_branding.py
  tests/unit/test_settings.py
  tests/ui/test_window_menu.py
  tests/ui/test_theme.py
  tests/ui/test_settings_dialog.py
  tests/ui/test_animations.py
  tests/ui/test_window.py
  tests/integration/test_desktop_entry.py
  tests/e2e/test_ui_scenario.py
)

FAILED=0

fail() {
    echo "КРИТЕРИЙ НЕ ВЫПОЛНЕН: $1 — $2" >&2
    FAILED=1
}

# 1. Логотип и символ на месте, старого растра нет.
if [[ ! -f "$ROOT/logo/snipnest.svg" ]]; then
    fail "логотип приложения на месте" "нет файла logo/snipnest.svg"
fi
if [[ ! -f "$ROOT/logo/snipnest-symbolic.svg" ]]; then
    fail "символ приложения на месте" "нет файла logo/snipnest-symbolic.svg"
fi
if [[ -f "$ROOT/logo/snipnest.png" ]]; then
    fail "иконка приложения одна" "в репозитории остался logo/snipnest.png"
fi

# 2. Меню, тема, настройки, анимации и иконки — тесты задачи.
if ! uv run pytest "${TESTS[@]}" -q --tb=line; then
    fail "меню, тема, настройки и анимации работают" "тесты задачи не зелёные"
fi

# 3. Остальной набор не разъехался.
if ! uv run pytest tests -m "not live" -q --tb=line; then
    fail "весь набор тестов зелёный" "падают тесты вне задачи"
fi

# 4. Линтер и типы.
if ! uv run ruff check src tests; then
    fail "линтер" "ruff нашёл ошибки"
fi
if ! uv run ruff format --check src tests; then
    fail "формат кода" "ruff format нашёл расхождения"
fi
if ! uv run mypy; then
    fail "типы" "mypy нашёл ошибки"
fi

# 5. Знаменатель обязательств модели предметной области.
if ! uv run python tests/spec_mini/run_denominator.py; then
    fail "знаменатель обязательств" "прогон по знаменателю не зелёный"
fi

if [[ "$FAILED" -eq 0 ]]; then
    echo "OK: аватарка, меню, тема и оформление на месте"
fi
exit "$FAILED"