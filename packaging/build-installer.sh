#!/usr/bin/env bash
# Собрать установщик: dist/snipnest-installer-linux-amd64.bin.
#
# Установщик — графическая программа на Qt: один файл, внутри Python, Qt и
# код установщика. Приложения внутри нет: установщик сам определяет
# дистрибутив, скачивает образ приложения и ставит его.
set -euo pipefail

# shellcheck source=packaging/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

VERSION="$(app_version)"
[[ -n "$VERSION" ]] || fail "не найдена версия в src/snipnest/__init__.py"

GLIBC="$(abi_glibc)"
[[ -n "$GLIBC" ]] || fail "не найдена версия glibc в packaging/abi.txt"

# Сведения о сборке установщик читает из своего бандла: какую версию
# качать, какой образ подходит системе и откуда его брать.
BUILD_INFO="$BUILD/installer-build-info.json"
mkdir -p "$BUILD"
cat > "$BUILD_INFO" <<EOF
{
  "version": "$VERSION",
  "min_glibc": "$GLIBC",
  "release_url": "$(release_url)"
}
EOF

mkdir -p "$DIST"
NAME="snipnest-installer-linux-amd64"

log "PyInstaller: установщик"
(cd "$ROOT" && \
    SNIPNEST_LAYOUT=onefile \
    SNIPNEST_ENTRY="$ROOT/packaging/installer_entry.py" \
    SNIPNEST_NAME="$NAME" \
    SNIPNEST_INSTALLER=1 \
    SNIPNEST_BUILD_INFO="$BUILD_INFO" \
    uv run pyinstaller packaging/snipnest.spec \
        --distpath "$DIST" \
        --workpath "$BUILD/pyinstaller-installer" \
        --noconfirm --clean >/dev/null)

OUTPUT="$DIST/$NAME.bin"
mv -f "$DIST/$NAME" "$OUTPUT"
chmod 755 "$OUTPUT"

# Собранный установщик должен быть программой, а не скриптом, и должен
# уметь выполнить установку: проверяем его в тестовом каталоге.
if [[ "$(head -c 4 "$OUTPUT")" != $'\x7fELF' ]]; then
    fail "установщик собран" "это не исполняемый файл ELF"
fi

TEST_DIR="$(mktemp -d)"
trap 'rm -rf "$TEST_DIR"' EXIT
printf 'подделка образа\n' > "$TEST_DIR/snipnest.AppImage"
cat > "$TEST_DIR/request.json" <<EOF
{
  "image_path": "$TEST_DIR/snipnest.AppImage",
  "image_name": "snipnest.AppImage",
  "app_dir": "$TEST_DIR/opt",
  "bin_dir": "$TEST_DIR/bin",
  "desktop_dir": "$TEST_DIR/share",
  "icons_dir": "$TEST_DIR/icons",
  "packages": [],
  "package_command": []
}
EOF
"$OUTPUT" --root-worker "$TEST_DIR/request.json" > "$TEST_DIR/report.json" \
    || fail "установщик выполняет установку" "см. отчёт: $(cat "$TEST_DIR/report.json")"
[[ -x "$TEST_DIR/opt/snipnest.AppImage" ]] \
    || fail "установщик выполняет установку" "образ не поставлен"
[[ -x "$TEST_DIR/bin/snipnest" ]] \
    || fail "установщик выполняет установку" "лаунчер не поставлен"

log "Готово: $OUTPUT"
