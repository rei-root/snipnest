#!/usr/bin/env bash
# Собрать AppImage: dist/snipnest-<версия>-x86_64.AppImage.
#
# Образ — один файл: внутри AppDir с программой, переносимым Python,
# desktop-файлом и иконкой.
set -euo pipefail

# shellcheck source=packaging/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/src/snipnest/__init__.py")"
[[ -n "$VERSION" ]] || fail "не найдена версия в src/snipnest/__init__.py"

ensure_runtime
ensure_appimagetool
build_pyinstaller onedir

APPDIR="$BUILD/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib/snipnest"

cp -a "$BUILD/onedir/snipnest" "$APPDIR/usr/lib/snipnest/app"
# Переносимый Python лежит рядом с программой: app/runtime/python/bin/python3
mkdir -p "$APPDIR/usr/lib/snipnest/app/runtime"
cp -a "$RUNTIME_DIR" "$APPDIR/usr/lib/snipnest/app/runtime/python"

cat > "$APPDIR/usr/bin/snipnest" <<'EOF'
#!/bin/sh
# Запуск Snipnest из образа AppImage.
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/../lib/snipnest/app/snipnest" "$@"
EOF
chmod +x "$APPDIR/usr/bin/snipnest"

cp "$ROOT/packaging/snipnest.desktop" "$APPDIR/snipnest.desktop"
cp "$ROOT/logo/snipnest.png" "$APPDIR/snipnest.png"
cp "$ROOT/logo/snipnest.png" "$APPDIR/.DirIcon"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
# Точка входа AppImage: запускает программу из образа.
HERE="$(dirname "$(readlink -f "$0")")"
export PATH="$HERE/usr/bin:${PATH}"
exec "$HERE/usr/bin/snipnest" "$@"
EOF
chmod +x "$APPDIR/AppRun"

mkdir -p "$DIST"
OUTPUT="$DIST/snipnest-${VERSION}-x86_64.AppImage"
rm -f "$OUTPUT"
log "Собираю AppImage"
"$APPIMAGETOOL_RUN" --no-appstream "$APPDIR" "$OUTPUT" >/dev/null
chmod +x "$OUTPUT"

log "Готово: $OUTPUT"
