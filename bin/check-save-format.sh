#!/usr/bin/env bash
# Оракул задачи 010-save-format: формат сохранения выбирается и применяется.
#
# Возвращает 0 тогда и только тогда, когда критерии выполнены. Печатает
# упавший критерий и причину.
#
# Критерии проверяются тестами задачи: каталог форматов, команда yt-dlp для
# каждого варианта, перевод картинки в выбранный формат, выбор в окне и
# сценарий целиком — файл на диске в том формате, который выбрал владелец.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

TESTS=(
  tests/unit/test_formats.py
  tests/unit/test_ytdlp.py
  tests/unit/test_downloader.py
  tests/ui/test_imaging.py
  tests/ui/test_format_selector.py
  tests/ui/test_window_format.py
  tests/e2e/test_format_scenario.py
)

if ! uv run pytest "${TESTS[@]}" -q --tb=line; then
  echo "КРИТЕРИЙ НЕ ВЫПОЛНЕН: формат сохранения выбирается и применяется" >&2
  exit 1
fi

echo "OK: формат сохранения выбирается и применяется"
