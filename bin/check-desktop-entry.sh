#!/usr/bin/env bash
# Оракул задачи 002: desktop-файл ярлыка под новым именем (класс B).
#
# Возвращает 0 тогда и только тогда, когда критерии выполнены. Печатает имя
# упавшего критерия и причину.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP="$ROOT/packaging/snipnest.desktop"
LOGO="$ROOT/logo/snipnest.png"
ICON_NAME="snipnest"

# Прежнее имя собирается из частей: сам оракул не должен содержать его в
# виде текста — иначе проверка «старого имени нет в дереве» нашла бы его
# здесь.
LEGACY_NAME=gall"ary-downloader"

APPLICATIONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"
BIN_DIR="$HOME/.local/bin"

FAILED=0

fail() {
    echo "КРИТЕРИЙ НЕ ВЫПОЛНЕН: $1 — $2" >&2
    FAILED=1
}

if [[ ! -f "$DESKTOP" ]]; then
    fail "desktop-файл существует" "нет файла $DESKTOP"
else
    for key in "Name=Snipnest" "Type=Application" "Exec=snipnest" "Icon=snipnest"; do
        if ! grep -qF -- "$key" "$DESKTOP"; then
            fail "desktop-файл содержит '$key'" "строка не найдена"
        fi
    done
    if ! grep -qE '^Categories=.*Network' "$DESKTOP"; then
        fail "desktop-файл в категории Network" "категория Network не указана"
    fi
fi

if [[ ! -f "$LOGO" ]]; then
    fail "логотип приложения на месте" "нет файла $LOGO"
fi

# Иконка должна быть установлена либо собираться из логотипа.
ICON_FOUND=0
for dir in \
    "$ICONS_DIR" \
    "/usr/share/icons/hicolor" \
    "/usr/share/pixmaps"; do
    [[ -d "$dir" ]] || continue
    if find "$dir" \( -name "${ICON_NAME}.png" -o -name "${ICON_NAME}.svg" \) 2>/dev/null | grep -q .; then
        ICON_FOUND=1
        break
    fi
done
if [[ "$ICON_FOUND" -eq 0 ]]; then
    fail "иконка $ICON_NAME установлена" "не найдена в ~/.local/share/icons, /usr/share/icons, /usr/share/pixmaps"
fi

# Лаунчер должен указывать на живой интерпретатор: иначе ярлык в меню есть,
# а приложение не запускается (как было после переезда проекта).
LAUNCHER="$BIN_DIR/snipnest"
if [[ ! -f "$LAUNCHER" ]]; then
    fail "лаунчер установлен" "нет файла $LAUNCHER"
else
    LAUNCHER_APP_DIR="$(sed -n 's/^APP_DIR="\(.*\)"$/\1/p' "$LAUNCHER" | head -1)"
    if [[ -z "$LAUNCHER_APP_DIR" ]]; then
        fail "лаунчер указывает на каталог проекта" "в $LAUNCHER нет строки APP_DIR"
    elif [[ ! -x "$LAUNCHER_APP_DIR/.venv/bin/python" ]]; then
        fail "лаунчер указывает на живой интерпретатор" \
            "нет $LAUNCHER_APP_DIR/.venv/bin/python — переустановите лаунчер: bash packaging/install-desktop-entry.sh"
    fi
fi

# Прежние следы в системе должны быть убраны: в меню приложений не должно
# остаться двух записей, а старая иконка не должна показываться.
if [[ -e "$APPLICATIONS_DIR/${LEGACY_NAME}.desktop" ]]; then
    fail "прежний ярлык удалён" "на месте $APPLICATIONS_DIR/${LEGACY_NAME}.desktop"
fi
if [[ -e "$BIN_DIR/$LEGACY_NAME" ]]; then
    fail "прежний лаунчер удалён" "на месте $BIN_DIR/$LEGACY_NAME"
fi
LEGACY_ICON_FOUND=0
for dir in "$ICONS_DIR" "/usr/share/icons/hicolor" "/usr/share/pixmaps"; do
    [[ -d "$dir" ]] || continue
    if find "$dir" -name "${LEGACY_NAME}.png" 2>/dev/null | grep -q .; then
        LEGACY_ICON_FOUND=1
        break
    fi
done
if [[ "$LEGACY_ICON_FOUND" -ne 0 ]]; then
    fail "прежняя иконка удалена" "на месте ${LEGACY_NAME}.png в $ICONS_DIR"
fi

if [[ "$FAILED" -eq 0 ]]; then
    echo "OK: desktop-файл и иконка на месте"
fi
exit "$FAILED"
