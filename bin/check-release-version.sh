#!/usr/bin/env bash
# Оракул задачи 012: релиз 0.2.2 собран из версии пакета.
#
# Возвращает 0 тогда и только тогда, когда критерии выполнены. Печатает имя
# упавшего критерия и причину.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
EXPECTED_VERSION="0.2.2"
OLD_VERSION="0.2.1"

FAILED=0

fail() {
    echo "КРИТЕРИЙ НЕ ВЫПОЛНЕН: $1 — $2" >&2
    FAILED=1
}

version_of_package() {
    sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/src/snipnest/__init__.py" | head -1
}

# 1. Версия пакета — та, что вышла в релизе.
check_version() {
    local version
    version="$(version_of_package)"
    if [[ "$version" != "$EXPECTED_VERSION" ]]; then
        fail "версия пакета — $EXPECTED_VERSION" "в пакете $version"
    fi
}

# 2. Имена артефактов собираются из версии пакета.
check_artifact_names() {
    local deb image url
    deb="$(bash -c "source '$ROOT/packaging/common.sh'; deb_name")"
    image="$(bash -c "source '$ROOT/packaging/common.sh'; appimage_name")"
    url="$(bash -c "source '$ROOT/packaging/common.sh'; release_url")"
    if [[ "$deb" != *"${EXPECTED_VERSION}"* ]]; then
        fail "имя пакета содержит версию" "$deb"
    fi
    if [[ "$image" != *"${EXPECTED_VERSION}"* ]]; then
        fail "имя образа содержит версию" "$image"
    fi
    if [[ "$url" != *"/v${EXPECTED_VERSION}" ]]; then
        fail "адрес релиза ведёт на тег версии" "$url"
    fi
}

# 3. Прежней версии нигде не осталось.
check_no_old_version() {
    local found
    found="$(grep -rn "$OLD_VERSION" \
        --include='*.py' --include='*.md' --include='*.sh' --include='*.yml' \
        "$ROOT/src" "$ROOT/tests" "$ROOT/packaging" "$ROOT/README.md" \
        "$ROOT/.github" 2>/dev/null | grep -v "$OLD_VERSION-" | head -3)"
    if [[ -n "$found" ]]; then
        fail "прежней версии нигде не осталось" "$found"
    fi
}

# 4. Собранный установщик внутри знает версию и адрес релиза.
check_installer_build_info() {
    local installer="$DIST/snipnest-installer-linux-amd64.bin"
    if [[ ! -f "$installer" ]]; then
        echo "Установщик не собран — четвёртый критерий пропущен."
        return
    fi
    local info
    info="$(cd "$ROOT" && uv run python - "$installer" <<'PY' 2>/dev/null
import sys
from PyInstaller.archive.readers import CArchiveReader

reader = CArchiveReader(sys.argv[1])
print(reader.extract("installer-build-info.json").decode("utf-8"))
PY
)"
    if [[ -z "$info" ]]; then
        fail "в установщике есть сведения о сборке" "внутри нет installer-build-info.json"
        return
    fi
    if [[ "$info" != *"\"$EXPECTED_VERSION\""* ]]; then
        fail "в установщике есть сведения о сборке" "внутри нет версии $EXPECTED_VERSION"
    fi
    if [[ "$info" != *"/v${EXPECTED_VERSION}"* ]]; then
        fail "в установщике есть сведения о сборке" "внутри нет адреса релиза v$EXPECTED_VERSION"
    fi
}

check_version
check_artifact_names
check_no_old_version
check_installer_build_info

if [[ "$FAILED" -eq 0 ]]; then
    echo "OK: релиз $EXPECTED_VERSION собран из версии пакета"
fi
exit "$FAILED"
