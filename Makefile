.PHONY: help lint typecheck test test-unit test-live oracle ci install-deps

PY ?= uv run

help:
	@echo "lint        ruff check + format --check"
	@echo "typecheck   mypy --strict"
	@echo "test        unit-тесты (без сети)"
	@echo "test-live   тесты с реальной загрузкой из Pinterest"
	@echo "oracle      оракул задачи: тесты + драйвер знаменателя + desktop-проверка"
	@echo "ci          lint + typecheck + test + oracle"

lint:
	$(PY) ruff check src tests
	$(PY) ruff format --check src tests

typecheck:
	$(PY) mypy

test:
	$(PY) pytest tests -m "not live"

test-unit:
	$(PY) pytest tests/unit

test-live:
	$(PY) pytest tests -m live

oracle:
	$(PY) pytest tests -m "not live"
	$(PY) python tests/spec_mini/run_denominator.py

ci: lint typecheck test oracle

install-deps:
	uv sync
