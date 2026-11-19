#!/usr/bin/env bash
# Оракул задачи 005: собранные артефакты (бинарник, AppImage, .deb).
#
# Возвращает 0 тогда и только тогда, когда критерии выполнены. Печатает имя
# упавшего критерия и причину.
#
# Артефакты берутся из dist/. Собрать их: make dist-onefile dist-appimage dist-deb
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"

VERSION="$(grep -oP '(?<=^version = ")[^"]+' "$ROOT/pyproject.toml" | head -1)"
if [[ -z "$VERSION" ]]; then
  VERSION="$(grep -oP '(?<=__version__ = ")[^"]+' "$ROOT/src/snipnest/__init__.py" | head -1)"
fi

BINARY="$DIST/snipnest"
APPIMAGE="$DIST/snipnest-${VERSION}-x86_64.AppImage"
DEB="$DIST/snipnest_${VERSION}_amd64.deb"

COMPONENTS=(gallery-dl yt-dlp yt-dlp-ejs deno ffmpeg)

FAILED=0

fail() {
    echo "КРИТЕРИЙ НЕ ВЫПОЛНЕН: $1 — $2" >&2
    FAILED=1
}

# 1. Бинарник: один исполняемый файл.
if [[ ! -x "$BINARY" ]]; then
    fail "бинарник собран" "нет исполняемого файла $BINARY"
else
    version_line="$("$BINARY" --version 2>/dev/null | head -1)"
    if [[ "$version_line" != "snipnest $VERSION" ]]; then
        fail "бинарник печатает версию" "получено '${version_line}', ожидалось 'snipnest $VERSION'"
    fi
fi

# 2. AppImage: образ, внутри AppRun, desktop-файл и иконка.
if [[ ! -f "$APPIMAGE" ]]; then
    fail "appimage собран" "нет файла $APPIMAGE"
else
    extract_dir="$DIST/appimage-extract"
    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"
    (cd "$extract_dir" && "$APPIMAGE" --appimage-extract >/dev/null 2>&1)
    squashfs="$extract_dir/squashfs-root"
    if [[ ! -d "$squashfs" ]]; then
        fail "appimage распаковывается" "не появился каталог squashfs-root"
    else
        for needed in AppRun snipnest.desktop snipnest.png; do
            if [[ ! -e "$squashfs/$needed" ]]; then
                fail "в appimage есть $needed" "нет файла squashfs-root/$needed"
            fi
        done
        if [[ -e "$squashfs/usr/bin/snipnest" && ! -x "$squashfs/usr/bin/snipnest" ]]; then
            fail "в appimage есть исполняемый snipnest" "usr/bin/snipnest не исполняемый"
        fi
    fi
fi

# 3. .deb: метаданные, раскладка и компоненты внутри.
if [[ ! -f "$DEB" ]]; then
    fail "deb собран" "нет файла $DEB"
else
    if ! dpkg-deb --info "$DEB" >/dev/null 2>&1; then
        fail "deb читается" "dpkg-deb --info не отработал"
    fi
    contents="$(dpkg-deb --contents "$DEB" 2>/dev/null)"
    for needed in "./usr/bin/snipnest" "./usr/share/applications/snipnest.desktop"; do
        if ! grep -qF "$needed" <<<"$contents"; then
            fail "в deb есть $needed" "файла нет в списке пакета"
        fi
    done
    if ! grep -qF "./usr/share/icons/hicolor/256x256/apps/snipnest.png" <<<"$contents"; then
        fail "в deb есть иконка 256x256" "файла нет в списке пакета"
    fi
    for component in "${COMPONENTS[@]}"; do
        if ! grep -qF "./usr/lib/snipnest/components/$component/" <<<"$contents"; then
            fail "в deb есть компонент $component" "каталога компонента нет в списке пакета"
        fi
    done

    root_dir="$DIST/deb-root"
    rm -rf "$root_dir"
    mkdir -p "$root_dir"
    if ! dpkg-deb -x "$DEB" "$root_dir" >/dev/null 2>&1; then
        fail "deb распаковывается" "dpkg-deb -x не отработал"
    else
        if [[ ! -x "$root_dir/usr/bin/snipnest" ]]; then
            fail "в распакованном deb есть лаунчер" "нет исполняемого usr/bin/snipnest"
        fi
    fi
fi

if [[ "$FAILED" -eq 0 ]]; then
    echo "OK: артефакты собраны и устроены верно (версия $VERSION)"
fi
exit "$FAILED"
