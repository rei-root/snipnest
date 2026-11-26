#!/usr/bin/env bash
# Оракул задачи 007: установщик ставит пакет .deb без ошибки apt.
#
# Возвращает 0 тогда и только тогда, когда критерии выполнены. Печатает имя
# упавшего критерия и причину.
#
# Установщик проверяется как чёрный ящик: системные команды подменены
# скриптами, которые пишут свои аргументы в лог.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

BIN="$WORK/bin"
LOG="$WORK/calls.log"
INSTALLER="$WORK/dist/snipnest-installer-linux-amd64.bin"
RELEASE="$WORK/os-release"

FAILED=0

fail() {
    echo "КРИТЕРИЙ НЕ ВЫПОЛНЕН: $1 — $2" >&2
    FAILED=1
}

# Подставные системные команды: пишут аргументы и права файла в лог.
write_fake() {
    local name="$1" body="$2"
    cat > "$BIN/$name" <<EOF
#!/bin/sh
printf '=== $name\n' >> "$LOG"
for arg in "\$@"; do printf '%s\n' "\$arg" >> "$LOG"; done
last=""
for arg in "\$@"; do last="\$arg"; done
if [ -n "\$last" ] && [ -f "\$last" ]; then
    printf 'meta:file-mode %s\n' "\$(stat -c '%a' "\$last" 2>/dev/null)" >> "$LOG"
    printf 'meta:dir-mode %s\n' "\$(stat -c '%a' "\$(dirname "\$last")" 2>/dev/null)" >> "$LOG"
fi
$body
EOF
    chmod 755 "$BIN/$name"
}

# Аргументы последнего вызова команды из лога.
arguments() {
    awk -v name="$1" '
        /^=== / { block = ($0 == "=== " name) ? "" : "-" }
        block == "" && !/^meta:/ && !/^=== / { print }
    ' "$LOG"
}

# Служебные значения последнего вызова команды из лога.
meta() {
    awk -v name="$1" -v key="$2" '
        /^=== / { block = ($0 == "=== " name) ? "" : "-" }
        block == "" && $0 ~ "^meta:" key " " { print $2 }
    ' "$LOG"
}

run_installer() {
    env PATH="$BIN:$PATH" \
        SNIPNEST_OS_RELEASE="$RELEASE" \
        FAKE_APT_GET_EXIT="${FAKE_APT_GET_EXIT:-0}" \
        "$INSTALLER" --local "$WORK/snipnest_0.2.0_amd64.deb" --yes
}

setup() {
    mkdir -p "$BIN"
    : > "$LOG"
    write_fake sudo 'exec "$@"'
    write_fake apt-get 'exit "${FAKE_APT_GET_EXIT:-0}"'
    write_fake dpkg 'exit 0'
    printf 'ID=debian\nID_LIKE=""\n' > "$RELEASE"
    printf 'подделка пакета\n' > "$WORK/snipnest_0.2.0_amd64.deb"
    DIST="$WORK/dist" bash "$ROOT/packaging/build-installer.sh" >/dev/null \
        || fail "установщик собран" "сборка не отработала"
}

# 1. Путь, который apt принимает: абсолютный, без «.//».
check_apt_path() {
    local path
    path="$(arguments apt-get | tail -1)"
    if [[ -z "$path" ]]; then
        fail "apt-get получил путь к пакету" "apt-get не вызван"
        return
    fi
    if [[ "$path" == .//* ]]; then
        fail "apt-get получил путь к пакету" "путь начинается с «.//»: $path"
        return
    fi
    if [[ "$path" != /* ]]; then
        fail "apt-get получил путь к пакету" "путь не абсолютный: $path"
        return
    fi
    if [[ "$path" != *.deb ]]; then
        fail "apt-get получил путь к пакету" "путь не ведёт к .deb: $path"
    fi
}

# 2. Файл пакета читает служебный пользователь apt.
check_sandbox_rights() {
    local file_mode dir_mode
    file_mode="$(meta apt-get file-mode)"
    dir_mode="$(meta apt-get dir-mode)"
    if [[ "$file_mode" != "644" ]]; then
        fail "файл пакета доступен служебному пользователю apt" "права файла: ${file_mode:-нет}"
    fi
    if [[ "$dir_mode" != "755" ]]; then
        fail "каталог пакета доступен служебному пользователю apt" "права каталога: ${dir_mode:-нет}"
    fi
}

# 3. При отказе apt-get пакет ставится через dpkg.
check_dpkg_fallback() {
    if [[ "$(arguments dpkg | head -1)" != "-i" ]]; then
        fail "при отказе apt-get пакет ставится через dpkg" "dpkg не вызван с -i"
    fi
}

# 4. Человек видит итог установки.
check_result_printed() {
    if ! grep -q "через apt-get" "$WORK/out.txt"; then
        fail "установщик печатает итог" "в выводе нет «через apt-get»"
    fi
}

setup

run_installer > "$WORK/out.txt" 2>&1
STATUS=$?
if [[ "$STATUS" -ne 0 ]]; then
    fail "установщик отработал" "код возврата $STATUS, вывод: $(cat "$WORK/out.txt")"
else
    check_apt_path
    check_sandbox_rights
    check_result_printed
fi

# Тот же прогон, но apt-get отказывается.
: > "$LOG"
FAKE_APT_GET_EXIT=1 run_installer > "$WORK/out-fallback.txt" 2>&1
STATUS=$?
if [[ "$STATUS" -ne 0 ]]; then
    fail "установщик отработал при отказе apt-get" "код возврата $STATUS, вывод: $(cat "$WORK/out-fallback.txt")"
else
    check_dpkg_fallback
    if ! grep -q "через dpkg" "$WORK/out-fallback.txt"; then
        fail "установщик печатает итог при отказе apt-get" "в выводе нет «через dpkg»"
    fi
fi

if [[ "$FAILED" -eq 0 ]]; then
    echo "OK: установщик ставит пакет .deb без ошибки apt"
fi
exit "$FAILED"
