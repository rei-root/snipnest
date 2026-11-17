#!/usr/bin/env bash
# Установка ярлыка в меню приложений и лаунчера в PATH.
#
# Делает приложение доступным из меню KDE:
#   - desktop-файл -> ~/.local/share/applications
#   - иконка        -> ~/.local/share/icons/hicolor (все стандартные размеры)
#   - лаунчер       -> ~/.local/bin/gallary-downloader
#
# Лаунчер нужен потому, что desktop-файл вызывает команду по имени
# (Exec=gallary-downloader), а интерпретатор приложения живёт в venv.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_SRC="$ROOT/packaging/gallary-downloader.desktop"
LOGO_SRC="$ROOT/logo/gallery-dl-gui-logo.png"

APPLICATIONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
BIN_DIR="$HOME/.local/bin"

SIZES=(16 24 32 48 64 128 256 512)

echo "Установка Gallary Downloader из $ROOT"

# 1. Desktop-файл: ярлык в меню приложений.
mkdir -p "$APPLICATIONS_DIR"
install -m 0755 "$DESKTOP_SRC" "$APPLICATIONS_DIR/gallary-downloader.desktop"
echo "  ярлык: $APPLICATIONS_DIR/gallary-downloader.desktop"

# 2. Иконка: имя иконки в desktop-файле — gallary-downloader.
if [[ ! -f "$LOGO_SRC" ]]; then
    echo "  ПРОПУЩЕНО: нет логотипа $LOGO_SRC" >&2
else
    for size in "${SIZES[@]}"; do
        target="$ICONS_DIR/${size}x${size}/apps"
        mkdir -p "$target"
        convert "$LOGO_SRC" -resize "${size}x${size}" -strip "PNG32:$target/gallary-downloader.png"
    done
    echo "  иконка: $ICONS_DIR/*/apps/gallary-downloader.png"

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
cat > "$BIN_DIR/gallary-downloader" <<EOF
#!/usr/bin/env bash
# Запуск Gallary Downloader из меню приложений.
set -euo pipefail
APP_DIR="$ROOT"
VENV_PYTHON="\$APP_DIR/.venv/bin/python"
if [[ ! -x "\$VENV_PYTHON" ]]; then
    echo "Gallary Downloader: не найден интерпретатор \$VENV_PYTHON" >&2
    echo "Выполните: cd \"\$APP_DIR\" && uv sync" >&2
    exit 1
fi
export PYTHONPATH="\$APP_DIR/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec "\$VENV_PYTHON" -m gallary_downloader "\$@"
EOF
chmod +x "$BIN_DIR/gallary-downloader"
echo "  лаунчер: $BIN_DIR/gallary-downloader"

# 4. Кэши: меню и иконки перечитывают файлы.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$ICONS_DIR" || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental || true
fi

echo "Готово. Приложение доступно из меню приложений как «Gallary Downloader»."
