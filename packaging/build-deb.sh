#!/usr/bin/env bash
# Собрать пакет .deb: dist/snipnest_<версия>_amd64.deb.
#
# Пакет самодостаточный: внутри программа, Qt, переносимый Python и все
# пять компонентов. После установки приложение работает без сети.
set -euo pipefail

# shellcheck source=packaging/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/src/snipnest/__init__.py")"
[[ -n "$VERSION" ]] || fail "не найдена версия в src/snipnest/__init__.py"

ARCH="amd64"
PREFIX="/usr/lib/snipnest"

ensure_runtime
build_pyinstaller onedir

STAGE="$BUILD/deb-root"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/lib/snipnest" "$STAGE/usr/bin" \
    "$STAGE/usr/share/applications" "$STAGE/usr/share/icons/hicolor"

# 1. Программа и переносимый Python.
cp -a "$BUILD/onedir/snipnest" "$STAGE$PREFIX/app"
# Переносимый Python лежит рядом с программой: app/runtime/python/bin/python3
mkdir -p "$STAGE$PREFIX/app/runtime"
cp -a "$RUNTIME_DIR" "$STAGE$PREFIX/app/runtime/python"

# 2. Лаунчер в /usr/bin.
cat > "$STAGE/usr/bin/snipnest" <<EOF
#!/bin/sh
# Запуск Snipnest из пакета.
exec "$PREFIX/app/snipnest" "\$@"
EOF
chmod +x "$STAGE/usr/bin/snipnest"

# 3. Ярлык и иконки.
cp "$ROOT/packaging/snipnest.desktop" "$STAGE/usr/share/applications/snipnest.desktop"
install_icons "$STAGE/usr/share/icons/hicolor"

# 4. Компоненты внутри пакета.
log "Ставлю компоненты в пакет"
(cd "$ROOT" && uv run python packaging/install-components.py "$STAGE$PREFIX/components" \
    --python "$RUNTIME_PYTHON" \
    --launcher-python "$PREFIX/app/runtime/python/bin/python3" \
    --launcher-root "$PREFIX/components") || fail "не удалось поставить компоненты"

# 5. Метаданные пакета.
cat > "$STAGE/DEBIAN/control" <<EOF
Package: snipnest
Version: $VERSION
Architecture: $ARCH
Maintainer: Snipnest <snipnest@localhost>
Installed-Size: $(du -sk "$STAGE" | cut -f1)
Depends: libc6
Section: net
Priority: optional
Description: Загрузчик картинок и видео
 GUI-обёртка над gallery-dl и yt-dlp: скачивание из Pinterest и видео
 с YouTube. Пакет самодостаточный: программа, Qt, переносимый Python и
 компоненты лежат внутри.
EOF

mkdir -p "$DIST"
OUTPUT="$DIST/snipnest_${VERSION}_${ARCH}.deb"
rm -f "$OUTPUT"
dpkg-deb --build --root-owner-group "$STAGE" "$OUTPUT" >/dev/null

log "Готово: $OUTPUT"
