#!/usr/bin/env bash
# Собрать установщик: dist/snipnest-installer-linux-amd64.bin.
#
# Установщик — один файл на POSIX shell. Приложения внутри нет: установщик
# сам определяет дистрибутив и ставит приложение, скачивая его из релиза.
set -euo pipefail

# shellcheck source=packaging/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

VERSION="$(app_version)"
[[ -n "$VERSION" ]] || fail "не найдена версия в src/snipnest/__init__.py"

GLIBC="$(abi_glibc)"
[[ -n "$GLIBC" ]] || fail "не найдена версия glibc в packaging/abi.txt"

TEMPLATE="$ROOT/packaging/installer/snipnest-installer.sh"
[[ -f "$TEMPLATE" ]] || fail "нет шаблона установщика: $TEMPLATE"

mkdir -p "$DIST"
OUTPUT="$DIST/snipnest-installer-linux-amd64.bin"

sed -e "s|@VERSION@|$VERSION|g" \
    -e "s|@RELEASE_URL@|$(release_url)|g" \
    -e "s|@APPIMAGE_NAME@|$(appimage_name)|g" \
    -e "s|@DEB_NAME@|$(deb_name)|g" \
    -e "s|@MIN_GLIBC@|$GLIBC|g" \
    "$TEMPLATE" > "$OUTPUT"
chmod 755 "$OUTPUT"

# Установщик должен быть настоящим shell-скриптом и запускаться.
sh -n "$OUTPUT" || fail "установщик не проходит проверку синтаксиса"
"$OUTPUT" --help >/dev/null || fail "установщик не печатает справку"

log "Готово: $OUTPUT"
