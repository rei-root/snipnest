#!/usr/bin/env bash
# Оракул задачи 008: установщик — графическая программа, а не shell-скрипт.
#
# Возвращает 0 тогда и только тогда, когда критерии выполнены. Печатает имя
# упавшего критерия и причину.
#
# Собранный установщик нужен для части критериев; если его нет, оракул
# собирает его сам (сборка занимает пару минут).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
INSTALLER="$DIST/snipnest-installer-linux-amd64.bin"

FAILED=0

fail() {
    echo "КРИТЕРИЙ НЕ ВЫПОЛНЕН: $1 — $2" >&2
    FAILED=1
}

# 1. Код установщика есть и это графическая программа.
check_sources() {
    if [[ ! -d "$ROOT/src/snipnest/installer" ]]; then
        fail "код установщика есть" "нет каталога src/snipnest/installer"
        return
    fi
    for module in window.py worker.py elevate.py plan.py dependencies.py detect.py; do
        if [[ ! -f "$ROOT/src/snipnest/installer/$module" ]]; then
            fail "код установщика есть" "нет модуля $module"
        fi
    done
    if [[ ! -f "$ROOT/packaging/installer_entry.py" ]]; then
        fail "код установщика есть" "нет точки входа packaging/installer_entry.py"
    fi
    if [[ -f "$ROOT/packaging/installer/snipnest-installer.sh" ]]; then
        fail "старого shell-установщика нет" "файл packaging/installer/snipnest-installer.sh на месте"
    fi
}

# 2. Сборщик собирает установщик программой, а не скриптом.
check_build_script() {
    local body
    body="$(cat "$ROOT/packaging/build-installer.sh")"
    if [[ "$body" != *"pyinstaller"* ]]; then
        fail "сборщик собирает установщик через PyInstaller" "в сборщике нет pyinstaller"
    fi
    if [[ "$body" != *"installer_entry.py"* ]]; then
        fail "сборщик собирает установщик через PyInstaller" "в сборщике нет своей точки входа"
    fi
    if [[ "$body" == *"snipnest-installer.sh"* ]]; then
        fail "сборщик собирает установщик через PyInstaller" "сборщик ещё собирает shell-скрипт"
    fi
}

# 3. Собранный установщик — программа с Qt внутри.
check_binary() {
    if [[ ! -f "$INSTALLER" ]]; then
        echo "Собираю установщик (это займёт пару минут)…"
        (cd "$ROOT" && bash packaging/build-installer.sh) >/dev/null 2>&1
    fi
    if [[ ! -f "$INSTALLER" ]]; then
        fail "установщик собран" "нет файла $INSTALLER"
        return
    fi
    if [[ "$(head -c 4 "$INSTALLER")" != $'\x7fELF' ]]; then
        fail "установщик собран" "это не исполняемый файл ELF"
        return
    fi
    local qt_strings
    qt_strings="$(strings "$INSTALLER" | grep -c "PySide6" || true)"
    if [[ "$qt_strings" -lt 1 ]]; then
        fail "в установщике есть Qt" "внутри нет PySide6"
    fi
}

# 4. Внутри установщика есть сведения о сборке: версия и адрес релиза.
check_build_info() {
    local output
    output="$(cd "$ROOT" && uv run python - "$INSTALLER" <<'PY' 2>/dev/null
import sys
from PyInstaller.archive.readers import CArchiveReader

reader = CArchiveReader(sys.argv[1])
data = reader.extract("installer-build-info.json").decode("utf-8")
print(data)
PY
)"
    if [[ -z "$output" ]]; then
        fail "в установщике есть сведения о сборке" "внутри нет installer-build-info.json"
        return
    fi
    if [[ "$output" != *"releases/download"* ]]; then
        fail "в установщике есть сведения о сборке" "нет адреса релиза"
    fi
}

# 5. Собранный установщик выполняет установку.
check_install() {
    local work
    work="$(mktemp -d)"
    printf 'подделка образа\n' > "$work/snipnest.AppImage"
    cat > "$work/request.json" <<EOF
{
  "image_path": "$work/snipnest.AppImage",
  "image_name": "snipnest.AppImage",
  "app_dir": "$work/opt",
  "bin_dir": "$work/bin",
  "desktop_dir": "$work/share",
  "icons_dir": "$work/icons",
  "packages": [],
  "package_command": []
}
EOF
    if ! "$INSTALLER" --root-worker "$work/request.json" > "$work/report.json" 2>/dev/null; then
        fail "установщик выполняет установку" "см. отчёт: $(cat "$work/report.json" 2>/dev/null)"
        rm -rf "$work"
        return
    fi
    for needed in "opt/snipnest.AppImage" "bin/snipnest" "share/snipnest.desktop"; do
        if [[ ! -e "$work/$needed" ]]; then
            fail "установщик выполняет установку" "нет файла $needed"
        fi
    done
    if [[ ! -x "$work/bin/snipnest" ]]; then
        fail "установщик выполняет установку" "лаунчер не исполняемый"
    fi
    rm -rf "$work"
}

check_sources
check_build_script
check_binary
check_build_info
check_install

if [[ "$FAILED" -eq 0 ]]; then
    echo "OK: установщик — графическая программа, установку выполняет"
fi
exit "$FAILED"
