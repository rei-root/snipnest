#!/usr/bin/env bash
# Общие куски сборки: корень проекта, переносимый Python, appimagetool.
#
# Источник для всех скриптов сборки: packaging/build-*.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$ROOT/build"
DIST="$ROOT/dist"
DOWNLOADS="$BUILD/downloads"

RUNTIME_DIR="$BUILD/runtime/python"
RUNTIME_PYTHON="$RUNTIME_DIR/bin/python3"

#: Переносимый CPython: приложение запускает им Python-компоненты.
PYTHON_VERSION="3.12.16"
PYTHON_BUILD="20261110"
PYTHON_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PYTHON_BUILD}/cpython-${PYTHON_VERSION}+${PYTHON_BUILD}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"

#: Сборщик AppImage. Образ не подписан: для этого нужен ключ.
APPIMAGETOOL="$BUILD/appimagetool"
APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"

log() {
    printf '%s\n' "$*"
}

fail() {
    printf 'ОШИБКА: %s\n' "$*" >&2
    exit 1
}

#: Скачать файл, если его ещё нет.
fetch() {
    local url="$1" target="$2"
    if [[ -s "$target" ]]; then
        return 0
    fi
    mkdir -p "$(dirname "$target")"
    log "Скачиваю $url"
    curl -fsSL --retry 3 --retry-delay 2 -o "$target" "$url" \
        || fail "не удалось скачать $url"
}

#: Разложить переносимый Python в build/runtime/python.
ensure_runtime() {
    if [[ -x "$RUNTIME_PYTHON" ]]; then
        return 0
    fi
    local archive="$DOWNLOADS/cpython.tar.gz"
    fetch "$PYTHON_URL" "$archive"
    log "Распаковываю переносимый Python $PYTHON_VERSION"
    rm -rf "$BUILD/runtime"
    mkdir -p "$RUNTIME_DIR"
    tar -xzf "$archive" -C "$RUNTIME_DIR" --strip-components=1
    [[ -x "$RUNTIME_PYTHON" ]] || fail "в переносимом Python нет интерпретатора"
}

#: Подготовить сборщик AppImage. Без FUSE образ распаковывается.
APPIMAGETOOL_RUN=""
ensure_appimagetool() {
    fetch "$APPIMAGETOOL_URL" "$APPIMAGETOOL"
    chmod +x "$APPIMAGETOOL"
    if "$APPIMAGETOOL" --version >/dev/null 2>&1; then
        APPIMAGETOOL_RUN="$APPIMAGETOOL"
        return 0
    fi
    local dir="$BUILD/appimagetool-extracted"
    if [[ ! -x "$dir/squashfs-root/AppRun" ]]; then
        rm -rf "$dir"
        mkdir -p "$dir"
        (cd "$dir" && "$APPIMAGETOOL" --appimage-extract >/dev/null) \
            || fail "не удалось распаковать appimagetool"
    fi
    APPIMAGETOOL_RUN="$dir/squashfs-root/AppRun"
}

#: Собрать приложение PyInstaller. layout: onefile или onedir.
build_pyinstaller() {
    local layout="$1"
    local distpath="$DIST"
    if [[ "$layout" == "onedir" ]]; then
        distpath="$BUILD/onedir"
    fi
    mkdir -p "$distpath"
    log "PyInstaller: $layout"
    (cd "$ROOT" && SNIPNEST_LAYOUT="$layout" uv run pyinstaller packaging/snipnest.spec \
        --distpath "$distpath" \
        --workpath "$BUILD/pyinstaller-$layout" \
        --noconfirm --clean >/dev/null)
}

#: Поставить иконки в каталог иконок (для .deb и AppImage).
install_icons() {
    local target="$1"
    local sizes=(16 24 32 48 64 128 256 512)
    local resizer=""
    if command -v magick >/dev/null 2>&1; then
        resizer="magick"
    elif command -v convert >/dev/null 2>&1; then
        resizer="convert"
    fi
    if [[ -z "$resizer" ]]; then
        log "ПРЕДУПРЕЖДЕНИЕ: нет ImageMagick — иконки копируются в одном размере"
        mkdir -p "$target/256x256/apps"
        cp "$ROOT/logo/snipnest.png" "$target/256x256/apps/snipnest.png"
        return 0
    fi
    for size in "${sizes[@]}"; do
        mkdir -p "$target/${size}x${size}/apps"
        "$resizer" "$ROOT/logo/snipnest.png" -resize "${size}x${size}" -strip \
            "PNG32:$target/${size}x${size}/apps/snipnest.png"
    done
}
