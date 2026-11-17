# Задание исполнителю: задача 001-pinterest-gui-wrapper

## Где работать

Воркдерево: `/home/sato/Документы/gallery-dl-gui-wt/work-001-code` (ветка `work/001-code`, checkout сделан).

НЕ работай в `/home/sato/Документы/gallery-dl-gui` — это дерево оркестратора.
Все команды — из каталога воркдерева.

## Цель

Написать код приложения Gallary Downloader — GUI-обёртки над gallery-dl:

1. Одно поле ссылки; приложение определяет, картинка это или альбом.
2. Скачивает картинку или целый альбом, вызывая системный бинарник `gallery-dl`.
3. Показывает прогресс, скорость, счётчик «скачано X из Y», список файлов.
4. По завершении — итог: скачано / пропущено / ошибок.
5. Показывает папку сохранения, позволяет менять, выбор запоминается между запусками.
6. Несколько загрузок одновременно, каждая независимо.
7. Не падает при неверной ссылке, недоступной сети, отсутствии gallery-dl.
8. Drag-and-drop ссылки из браузера в окно.
9. Лог вывода gallery-dl в сворачиваемой области.
10. Токен/cookie Pinterest вставляется в GUI и хранится в системном хранилище (keyring), не в обычном конфиге. Пароль не вводится и не хранится.
11. Ярлык в меню приложений с именем «Gallary Downloader», логотип из `logo/`.

## Оракул (read-only — нельзя менять)

`tests/unit/*.py`, `tests/integration/*.py`, `tests/e2e/*.py`, `tests/spec_mini/run_denominator.py`, `bin/check-desktop-entry.sh`, `docs/ba/spec/app-spec/**`.

Нельзя: редактировать, переименовывать, откатывать, удалять, отключать (`skip`, `only`, `t.Skip`), править конфиг тестов так, что они не запускаются.

Запуск:

```bash
cd /home/sato/Документы/gallery-dl-gui-wt/work-001-code
uv run pytest tests -m "not live"
uv run python tests/spec_mini/run_denominator.py
bash bin/check-desktop-entry.sh
```

Текущее состояние: `49 failed, 3 passed`; знаменатель `проверено: 69` из 89, `ПРОВАЛЕНО обязательств: 20`; desktop — падает на неустановленной иконке.

## Что уже есть

- `pyproject.toml`: PySide6, keyring; dev: pytest, pytest-qt, ruff, mypy. ruff line-length 100, mypy `--strict` по `src/gallary_downloader`.
- `Makefile`: `make lint`, `make typecheck`, `make test`, `make oracle`, `make ci`.
- `src/gallary_downloader/{links,downloader,jobs,settings}.py` — **заглушки с API-контрактом**: сигнатуры и классы заданы, тела бросают `NotImplementedError`. Это твой каркас. Реализацию меняй; структуру API, на которую рассчитаны тесты, не сметай.
- `packaging/gallary-downloader.desktop` — готовый ярлык.
- `logo/gallery-dl-gui-logo.png`, `links.txt` (живые ссылки для ручного прогона).

API-контракт кратко:

- `links.py`: `LinkKind`(PIN/BOARD/UNKNOWN), `LinkInfo(kind,url,pin_id,board_path)`, `classify_link(url)`, `is_valid_link(url)`.
- `downloader.py`: `DownloadEventKind`(FILE_DOWNLOADED/FILE_SKIPPED/LOG/ERROR), `DownloadEvent(kind,path,text)`, `DownloadResult(downloaded,skipped,errors,returncode,files)`, `parse_output_line(line,stream="stdout")`, `find_gallery_dl(explicit)`, `GalleryDlNotFoundError`, `GalleryDlRunner(binary,destination,cookies,on_event)` c `resolve_binary()`, `build_command(url,simulate=False)`, `run(url,simulate=False)`, `count_files(url)`, `cancel()`.
- `jobs.py`: `JobState`(QUEUED/RUNNING/DONE/FAILED/CANCELLED; значения enum = состояниям модели: "в_очереди","выполняется","завершена","ошибка","отменена"), `JobEventKind`, `JobEvent`, `JobProgress(downloaded,skipped,total,bytes_per_second)` c `.label` → "скачано X из Y", `DownloadJob(job_id,url,destination,runner,on_event)` c `can_cancel()`,`can_retry()`,`visible_fields()`,`start()`,`cancel()`,`retry()`,`handle_download_event(event)`, `JobManager(on_event)` c `submit(url,destination)`,`start_all()`.
- `settings.py`: `DEFAULT_DESTINATION`=`~/Изображения/Pinterest`, `KeyringStore`, `FileSecretStore`, `Settings(config_path,secret_store)` c `load()`,`save()`,`token`,`set_token()`,`clear_token()`, поля `destination`,`gallery_dl_path`.

## Уже принятые решения — не переигрывать

1. gallery-dl — внешний бинарник, приложение его не ставит. Не найден в PATH → сообщение и возможность указать путь руками.
2. Формат вывода gallery-dl (проверено на живой версии 1.32.15): **stdout** — только пути скачанных файлов; путь уже существующего файла с префиксом `# ` = «пропущено»; **stderr** — отладка и ошибки; код возврата 0 = успех, 4 = ошибка (ссылка не найдена). Ненулевой код = сбой, не тихий успех.
3. «Скачано X из Y»: у gallery-dl нет общего счётчика. Y = предварительный проход `gallery-dl --simulate` (для альбома из `links.txt` — 17 файлов, для картинки — 1); X — по мере скачивания.
4. Структуру папок и имена файлов определяет gallery-dl, вмешиваться нельзя (для альбома он сам создаёт подпапку).
5. Коллизии не перезаписываются — поведение gallery-dl по умолчанию.
6. Токен в системном хранилище (keyring); если keyring недоступен — файл с правами 600. Токен не должен попадать в обычный конфиг (проверяется тестом).
7. Несколько загрузок одновременно, без искусственного ограничения числа.
8. UI не подвисает: загрузка в отдельном потоке, события — в GUI-поток через сигналы Qt.
9. Архитектура с расширением: код Pinterest-логики отделён так, чтобы добавление другого источника (YouTube, TikTok) было возможно без переписывания UI. Слой «источники» — абстракция, конкретный источник — Pinterest.
10. Язык интерфейса и документации — русский; имена в коде — английские.

## Карта контекста

- `docs/ba/spec/app-spec/model/transitions.yaml` — граф переходов загрузки.
- `docs/ba/spec/app-spec/model.md` — права, видимость, владельцы полей, обратимость.
- `docs/ba/spec/app-spec/model/obligations.json` — знаменатель (89 обязательств).
- `docs/ba/spec/app-spec/model/exclusions.yaml` — что осознанно не делаем.
- `docs/ba/spec/app-spec/transcripts/T2.md` — дословная запись интервью с владельцем (источник истины).
- `tests/spec_mini/run_denominator.py` — драйвер: показывает ожидаемое поведение сервисного слоя. Это твой контракт по модели.
- `tasks/001-pinterest-gui-wrapper/requirements.yaml` — требования R1–R6, критерий приёмки AC1.

Грабли участка:

- Нельзя объединять потоки (`stderr=subprocess.STDOUT`) — отладочные строки будут посчитаны за файлы. Читать stdout и stderr раздельно.
- `--simulate` печатает пути с префиксом `# ` (перечисление, не скачивание) — учесть при подсчёте Y.
- `--simulate` на битой ссылке возвращает код 4, а не исключение.
- keyring может быть не настроен (`set_password` бросает) — нужен запасной путь.
- PySide6 требует GUI-сессии: тесты с QApplication запускать с `QT_QPA_PLATFORM=offscreen`.
- `mypy --strict`: аннотации везде, включая приватные методы; `Any` запрещён.

## Границы

Менять можно: `src/gallary_downloader/**` (включая новый `ui/`), `pyproject.toml`, `Makefile`, `README.md`, `packaging/**`, `.gitignore`.

Менять нельзя: оракул (список выше) и `docs/ba/spec/**`.

В задачу не входит: видео YouTube/TikTok и другие соцсети (только архитектурная возможность расширения), авторизация по логину/паролю, плейлисты и «сохранённые» Pinterest, поиск по ключевым словам, планировщик, мультиаккаунт, телеграм/бот-интерфейс.

**Не коммитить и не пушить.** Ничего нельзя коммитить, пушить, выполнять `git add -A` в корне воркспейса. Коммитит оркестратор.

## Правила исполнителя

1. Файл оракула — read-only (см. «Оракул»).
2. Готово, когда зелёный оракул **и** весь остальной набор тестов, типы и линтеры. Зелёный оракул при сломанных соседях — не результат.
3. **Зелёным считается код возврата**, а не отсутствие слова `FAIL`. Проверять код возврата и отметку успеха на каждый ожидаемый пакет.
4. Обходить оракул **запрещено**: захардкоженное ожидаемое значение; ветка `if` на входные данные; заглушка, из-за которой реальный путь не исполняется; правка соседних тестов, чтобы «сошлось»; пометка проверки как пропущенной.
5. Модель предметной области **нельзя трогать** ни руками, ни командами `spec`. Это не твоя зона — эскалируй.
6. Свои дополнительные тесты приветствуются.
7. Развилка или неточность оракула → **остановись и верни** `status: escalation` с вопросом и вариантами. Не угадывай.
8. Ничего нельзя коммитить и пушить; `git add -A` в корне воркспейса не выполнять.
9. Правила репозитория: ruff, mypy --strict, ≤300 строк на файл, type hints везде, запрещён `print()` в продовом коде, комментарии в коде — по-английски.
10. **Отчёт:**
    - изменённые файлы и зачем каждый;
    - дословный вывод прогона оракула;
    - дословный вывод полного прогона тестов, типов, линтеров;
    - что НЕ сделано и почему;
    - какие допущения принял;
    - какие эскалации закрыл и как.

## Критерий готовности

```bash
cd /home/sato/Документы/gallery-dl-gui-wt/work-001-code
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy
uv run pytest tests -m "not live"
uv run python tests/spec_mini/run_denominator.py     # 89/89, 0 пропущено, 8/8 дуг
bash bin/check-desktop-entry.sh
```

Desktop-проверка требует установленной иконки; её установку делает оркестратор. Если падает только на этом пункте — это ожидаемо, остальные критерии должны проходить.

Тесты с сетью помечены маркером `live` и в оракул не входят. Живой прогон по `links.txt` сделай вручную и напиши результат в отчёте.

Начни с чтения `tests/spec_mini/run_denominator.py` и `docs/ba/spec/app-spec/model.md` — это твой контракт. Затем `links.py` → `downloader.py` → `jobs.py` → `settings.py` → UI.
