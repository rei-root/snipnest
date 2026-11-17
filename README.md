# Gallary Downloader

GUI-обёртка над [gallery-dl](https://github.com/mikf/gallery-dl) для скачивания
изображений из Pinterest без терминала.

Приложение вызывает уже установленный в системе бинарник `gallery-dl` и
показывает ход загрузки: прогресс, скорость, счётчик «скачано X из Y», список
файлов и итог (скачано / пропущено / ошибок).

## Возможности

- одно поле ссылки: приложение само определяет, картинка это или альбом;
- несколько загрузок одновременно;
- drag-and-drop ссылки из браузера в окно;
- выбор папки сохранения, выбор запоминается между запусками;
- лог вывода `gallery-dl` для диагностики;
- токен Pinterest хранится в системном хранилище (keyring), пароль не вводится;
- ярлык в меню приложений: **Gallary Downloader**.

## Требования

- Python 3.11+
- `gallery-dl`, установленный в системе
- KDE / любой графический сеанс Linux

## Установка

```bash
uv sync
```

## Запуск

```bash
uv run gallary-downloader
```

Ярлык в меню приложений ставится так:

```bash
mkdir -p ~/.local/share/applications
cp packaging/gallary-downloader.desktop ~/.local/share/applications/
mkdir -p ~/.local/share/icons/hicolor/256x256/apps
cp logo/gallery-dl-gui-logo.png ~/.local/share/icons/hicolor/256x256/apps/gallary-downloader.png
```

## Разработка

```bash
make lint        # ruff check + format --check
make typecheck   # mypy --strict
make test        # unit-тесты, без сети
make test-live   # тесты с реальной загрузкой из Pinterest
make oracle      # оракул задачи: тесты + драйвер знаменателя
make ci          # всё вместе
```

## Лицензия

MIT
