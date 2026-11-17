#!/usr/bin/env bash
# Оракул задачи 001: desktop-файл ярлыка (класс B).
#
# Возвращает 0 тогда и только тогда, когда критерии выполнены. Печатает имя
# упавшего критерия и причину.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP="$ROOT/packaging/gallary-downloader.desktop"
LOGO="$ROOT/logo/gallery-dl-gui-logo.png"
FAILED=0

fail() {
    echo "КРИТЕРИЙ НЕ ВЫПОЛНЕН: $1 — $2" >&2
    FAILED=1
}

if [[ ! -f "$DESKTOP" ]]; then
    fail "desktop-файл существует" "нет файла $DESKTOP"
else
    for key in "Name=Gallary Downloader" "Type=Application" "Exec=gallary-downloader" "Icon=gallary-downloader"; do
        if ! grep -qF -- "$key" "$DESKTOP"; then
            fail "desktop-файл содержит '$key'" "строка не найдена"
        fi
    done
    if ! grep -qE '^Categories=.*Network' "$DESKTOP"; then
        fail "desktop-файл в категории Network" "категория Network не указана"
    fi
    if ! grep -qE '^Icon=gallary-downloader' "$DESKTOP"; then
        fail "иконка приложения объявлена" "Icon= не задан или другой"
    fi
fi

if [[ ! -f "$LOGO" ]]; then
    fail "логотип приложения на месте" "нет файла $LOGO"
fi

# Иконка должна быть установлена либо собираться из логотипа.
ICON_NAME="gallary-downloader"
ICON_FOUND=0
for dir in \
    "$HOME/.local/share/icons/hicolor" \
    "/usr/share/icons/hicolor" \
    "/usr/share/pixmaps"; do
    [[ -d "$dir" ]] || continue
    if find "$dir" -name "${ICON_NAME}.png" -o -name "${ICON_NAME}.svg" 2>/dev/null | grep -q .; then
        ICON_FOUND=1
        break
    fi
done
if [[ "$ICON_FOUND" -eq 0 ]]; then
    fail "иконка $ICON_NAME установлена" "не найдена в ~/.local/share/icons, /usr/share/icons, /usr/share/pixmaps"
fi

if [[ "$FAILED" -eq 0 ]]; then
    echo "OK: desktop-файл и иконка на месте"
fi
exit "$FAILED"
