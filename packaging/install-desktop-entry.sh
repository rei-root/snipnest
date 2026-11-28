#!/usr/bin/env bash
# Установка ярлыка в меню приложений и лаунчера в PATH.
#
# Делает приложение доступным из меню KDE:
#   - desktop-файл -> ~/.local/share/applications
#   - иконка        -> ~/.local/share/icons/hicolor (все стандартные размеры)
#   - лаунчер       -> ~/.local/bin/snipnest
#
# Лаунчер нужен потому, что desktop-файл вызывает команду по имени
# (Exec=snipnest), а интерпретатор приложения живёт в venv.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_SRC="$ROOT/packaging/snipnest.desktop"
LOGO_SRC="$ROOT/logo/snipnest.svg"

APPLICATIONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
BIN_DIR="$HOME/.local/bin"

SIZES=(16 24 32 48 64 128 256 512)

echo "Установка Snipnest из $ROOT"

# 1. Desktop-файл: ярлык в меню приложений.
mkdir -p "$APPLICATIONS_DIR"
install -m 0755 "$DESKTOP_SRC" "$APPLICATIONS_DIR/snipnest.desktop"
echo "  ярлык: $APPLICATIONS_DIR/snipnest.desktop"

# 2. Иконка: имя иконки в desktop-файле — snipnest.
if [[ ! -f "$LOGO_SRC" ]]; then
    echo "  ПРОДУПЩЕНО: нет логотипа $LOGO_SRC" >&2
else
    # Размеры PNG получаются из векторного логотипа средствами Qt: внешняя
    # программа не нужна. Если интерпретатора нет, установка не падает:
    # прежняя иконка остаётся на месте, а лаунчер и ярлык всё равно ставятся.
    VENV_PYTHON="$ROOT/.venv/bin/python"
    if [[ -x "$VENV_PYTHON" ]]; then
        if "$VENV_PYTHON" "$ROOT/packaging/render-icons.py" --out "$ICONS_DIR"; then
            echo "  иконка: $ICONS_DIR/*/apps/snipnest.png"
        else
            echo "  ПРОДУПЩЕНО: не удалось поставить иконки" >&2
        fi
    else
        echo "  ПРОДУПЩЕНО: нет $VENV_PYTHON — иконка не обновлена" >&2
    fi

    # Тема hicolor в локальном каталоге перекрывает системную, поэтому у
    # неё должен быть свой index.theme — иначе иконка не находится.
    if [[ ! -f "$ICONS_DIR/index.theme" ]]; then
        for system in /usr/share/icons/hicolor/index.theme; do
            [[ -f "$system" ]] && cp "$system" "$ICONS_DIR/index.theme" && break
        done
    fi
fi

# 3. Лаунчер: команда из Exec должна находиться в PATH.
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/snipnest" <<EOF
#!/usr/bin/env bash
# Запуск Snipnest из меню приложений.
set -euo pipefail
APP_DIR="$ROOT"
VENV_PYTHON="\$APP_DIR/.venv/bin/python"
if [[ ! -x "\$VENV_PYTHON" ]]; then
    echo "Snipnest: не найден интерпретатор \$VENV_PYTHON" >&2
    echo "Выполните: cd \"\$APP_DIR\" && uv sync" >&2
    exit 1
fi
export PYTHONPATH="\$APP_DIR/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec "\$VENV_PYTHON" -m snipnest "\$@"
EOF
chmod +x "$BIN_DIR/snipnest"
echo "  лаунчер: $BIN_DIR/snipnest"

# 4. Прежние следы: после переименования в меню не должно остаться двух
# записей, а старая иконка не должна показываться. Прежнее имя собирается
# из частей: сам установщик не должен содержать его в виде текста.
LEGACY_NAME=gall"ary-downloader"

rm -f "$APPLICATIONS_DIR/${LEGACY_NAME}.desktop"
rm -f "$BIN_DIR/$LEGACY_NAME"
for size in "${SIZES[@]}"; do
    rm -f "$ICONS_DIR/${size}x${size}/apps/${LEGACY_NAME}.png"
done
echo "  прежние следы убраны: ${LEGACY_NAME}"

# 5. Кэши: меню и иконки перечитывают файлы.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$ICONS_DIR" || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental || true
fi

echo "Готово. Приложение доступно из меню приложений как «Snipnest»."
