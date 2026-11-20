.PHONY: help lint typecheck test test-unit test-live oracle ci install-deps \
        dist-installer dist-appimage dist-deb dist check-dist

PY ?= uv run

help:
	@echo "lint        ruff check + format --check"
	@echo "typecheck   mypy --strict"
	@echo "test        unit-тесты (без сети)"
	@echo "test-live   тесты с реальной загрузкой из Pinterest"
	@echo "oracle      оракул задачи: тесты + драйвер знаменателя + desktop-проверка"
	@echo "ci          lint + typecheck + test + oracle"
	@echo "dist        собрать установщик, AppImage и .deb"
	@echo "dist-installer  установщик (dist/snipnest-installer-linux-amd64.bin)"
	@echo "dist-appimage   образ AppImage (dist/snipnest-<версия>-linux-glibc-<версия>-x86_64.AppImage)"
	@echo "dist-deb        пакет .deb (dist/snipnest_<версия>_amd64.deb)"
	@echo "check-dist      проверить собранные артефакты"

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

dist-installer:
	bash packaging/build-installer.sh

dist-appimage:
	bash packaging/build-appimage.sh

dist-deb:
	bash packaging/build-deb.sh

dist: dist-installer dist-appimage dist-deb

check-dist:
	bash bin/check-dist.sh
