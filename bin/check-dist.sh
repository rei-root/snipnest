#!/usr/bin/env bash
# Оракул задач 005 и 006: собранные артефакты (установщик, AppImage, .deb).
#
# Возвращает 0 тогда и только тогда, когда критерии выполнены. Печатает имя
# упавшего критерия и причину.
#
# Артефакты берутся из dist/. Собрать их:
#   make dist-installer dist-appimage dist-deb
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/src/snipnest/__init__.py" | head -1)"
GLIBC="$(sed -n 's/^glibc *//p' "$ROOT/packaging/abi.txt" | tail -1)"

INSTALLER="$DIST/snipnest-installer-linux-amd64.bin"
APPIMAGE="$DIST/snipnest-${VERSION}-linux-glibc-${GLIBC}-x86_64.AppImage"
DEB="$DIST/snipnest_${VERSION}_amd64.deb"

COMPONENTS=(gallery-dl yt-dlp yt-dlp-ejs deno ffmpeg)

FAILED=0

fail() {
    echo "КРИТЕРИЙ НЕ ВЫПОЛНЕН: $1 — $2" >&2
    FAILED=1
}

# 1. Установщик: один исполняемый файл, внутри которого нет приложения.
check_installer() {
    if [[ ! -x "$INSTALLER" ]]; then
        fail "установщик собран" "нет исполняемого файла $INSTALLER"
        return
    fi
    head_line="$(head -1 "$INSTALLER")"
    if [[ "$head_line" != "#!/bin/sh" ]]; then
        fail "установщик написан на POSIX shell" "первая строка: '$head_line'"
    fi
    if ! grep -q "snipnest-installer" "$INSTALLER"; then
        fail "установщик называет себя" "внутри нет строки snipnest-installer"
    fi
    for payload in "_internal" "PySide6" "usr/lib/snipnest/app"; do
        if grep -q "$payload" "$INSTALLER"; then
            fail "в установщике нет приложения" "внутри есть '$payload'"
        fi
    done
    if ! "$INSTALLER" --help >/dev/null 2>&1; then
        fail "установщик печатает справку" "--help не отработал"
    fi
    if ! "$INSTALLER" --version >/dev/null 2>&1; then
        fail "установщик печатает версию" "--version не отработал"
    fi
}

# 2. AppImage: образ с приложением, без установщика. В имени — платформа,
# версия glibc и архитектура.
check_appimage() {
    if [[ ! -f "$APPIMAGE" ]]; then
        fail "appimage собран" "нет файла $APPIMAGE"
        return
    fi
    base="$(basename "$APPIMAGE")"
    if [[ "$base" != snipnest-*-linux-glibc-*-x86_64.AppImage ]]; then
        fail "в имени appimage есть платформа, glibc и архитектура" "имя '$base'"
    fi
    extract_dir="$DIST/appimage-extract"
    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"
    (cd "$extract_dir" && "$APPIMAGE" --appimage-extract >/dev/null 2>&1)
    squashfs="$extract_dir/squashfs-root"
    if [[ ! -d "$squashfs" ]]; then
        fail "appimage распаковывается" "не появился каталог squashfs-root"
        return
    fi
    for needed in AppRun snipnest.desktop snipnest.png; do
        if [[ ! -e "$squashfs/$needed" ]]; then
            fail "в appimage есть $needed" "нет файла squashfs-root/$needed"
        fi
    done
    if [[ -e "$squashfs/usr/bin/snipnest" && ! -x "$squashfs/usr/bin/snipnest" ]]; then
        fail "в appimage есть исполняемый snipnest" "usr/bin/snipnest не исполняемый"
    fi
    if [[ ! -x "$squashfs/usr/lib/snipnest/app/runtime/python/bin/python3" ]]; then
        fail "в appimage есть переносимый Python" "нет runtime/python/bin/python3"
    fi
    # Установщика внутри образа быть не должно: образ — это приложение.
    if find "$squashfs" -name "snipnest-installer*" -print -quit | grep -q .; then
        fail "в appimage нет установщика" "внутри есть файл snipnest-installer*"
    fi
}

# 3. .deb: метаданные, раскладка и компоненты внутри.
check_deb() {
    if [[ ! -f "$DEB" ]]; then
        fail "deb собран" "нет файла $DEB"
        return
    fi
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
        return
    fi
    if [[ ! -x "$root_dir/usr/bin/snipnest" ]]; then
        fail "в распакованном deb есть лаунчер" "нет исполняемого usr/bin/snipnest"
    fi
}

check_installer
check_appimage
check_deb

if [[ "$FAILED" -eq 0 ]]; then
    echo "OK: артефакты собраны и устроены верно (версия $VERSION)"
fi
exit "$FAILED"
