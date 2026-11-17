# Gallary Downloader

GUI-обёртка над [gallery-dl](https://github.com/mikf/gallery-dl) для скачивания
изображений из Pinterest без терминала.

Приложение вызывает уже установленный в системе бинарник `gallery-dl` и
показывает ход загрузки: прогресс, скорость, счётчик «скачано X из Y», список
файлов и итог (скачано / пропущено / ошибок).

## Возможности

- одно поле ссылки: приложение само определяет, картинка это или альбом;
- несколько загрузок одновременно, каждая независимо;
- drag-and-drop ссылки из браузера в окно;
- выбор папки сохранения, выбор запоминается между запусками;
- лог вывода `gallery-dl` для диагностики (сворачиваемая область);
- токен Pinterest хранится в системном хранилище (keyring), пароль не вводится;
- кнопка «Открыть Pinterest» — открывает сайт в браузере;
- кнопка «Путь к gallery-dl» — если бинарник не найден в PATH;
- ярлык в меню приложений: **Gallary Downloader**.

## Устройство

```
src/gallary_downloader/
├── links.py       разбор ссылки: картинка или альбом
├── downloader.py  запуск внешнего бинарника gallery-dl, разбор его вывода
├── jobs.py        состояния загрузки, права, видимость, прогресс
├── manager.py     список загрузок и параллельный запуск
├── settings.py    папка сохранения и токен в системном хранилище
├── sources.py     слой источников: Pinterest (расширяемо на YouTube, TikTok)
└── ui/            интерфейс на PySide6
    ├── app.py          запуск приложения
    ├── window.py       главное окно
    ├── controls.py     поле ссылки, папка сохранения, кнопки
    ├── panel.py        список загрузок и файлы выбранной загрузки
    ├── presenter.py    правила показа события загрузки
    ├── controller.py   очередь, потоки, отмена и повтор
    ├── bridge.py       перенос событий из рабочего потока в GUI-поток
    ├── dnd.py          приём ссылки, перетащенной из браузера
    ├── logarea.py      сворачиваемая область лога
    ├── dialogs.py      диалоги (токен, выбор папки, путь к бинарнику)
    └── settings_actions.py  операции над настройками
```

Загрузка идёт в отдельном потоке; события попадают в GUI-поток через
сигналы Qt, поэтому окно не подвисает.

### Окружение запуска gallery-dl

Приложение запускает `gallery-dl` с очищенным окружением: из `PATH`
убирается каталог venv самого приложения, а `PYTHONHOME` и `PYTHONPATH`
сбрасываются.

Причина: многие установки `gallery-dl` — это bash-обёртки вида
`exec python3 .../gallery_dl/__main__.py`. Если первым в `PATH` стоит
`bin` venv приложения, то `python3` указывает на venv, где нет `requests`,
и бинарник падает с `ModuleNotFoundError` вместо скачивания. Системный
Python при этом остаётся доступен, поэтому `/usr/bin/gallery-dl` с
закреплённым shebang работает как раньше.

### Расширение на другие источники

UI не знает про Pinterest: он спрашивает реестр источников, какой из них
умеет работать со ссылкой. Чтобы добавить YouTube или TikTok, достаточно
написать подкласс `DownloadSource` и зарегистрировать его:

```python
from gallary_downloader.sources import DownloadSource, SourceKind, SourceRegistry

class YouTubeSource(DownloadSource):
    kind = SourceKind.YOUTUBE
    title = "YouTube"

    def matches(self, url: str) -> bool:
        return url.startswith("https://youtu.be/")

registry = SourceRegistry()
registry.register(YouTubeSource())
```

Правки в UI не нужны.

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

или

```bash
uv run python -m gallary_downloader
```

Ярлык в меню приложений ставится так:

```bash
bash packaging/install-desktop-entry.sh
```

Скрипт делает три вещи:

- копирует `packaging/gallary-downloader.desktop` в `~/.local/share/applications`
  (ярлык в меню приложений);
- ставит иконку `logo/gallery-dl-gui-logo.png` в
  `~/.local/share/icons/hicolor/*/apps/gallary-downloader.png` во всех
  стандартных размерах и копирует `index.theme` темы hicolor — без него
  локальный каталог перекрывает системный, и иконка не находится;
- создаёт лаунчер `~/.local/bin/gallary-downloader`, потому что ярлык
  вызывает команду по имени (`Exec=gallary-downloader`), а интерпретатор
  приложения живёт в venv и в `PATH` меню не попадает.

После этого приложение доступно из меню приложений как
**Gallary Downloader**.

Если каталог проекта переехал, лаунчер надо переустановить: он зашивает
путь к проекту.

## Разработка

```bash
make lint        # ruff check + format --check
make typecheck   # mypy --strict
make test        # unit-тесты, без сети
make test-live   # тесты с реальной загрузкой из Pinterest
make oracle      # оракул задачи: тесты + драйвер знаменателя
make ci          # всё вместе
```

Тесты интерфейса идут на платформе `offscreen`, если в системе нет
графической сессии (`DISPLAY` и `WAYLAND_DISPLAY` не заданы). Файл
`conftest.py` в корне задаёт это условие.

## Лицензия

MIT
