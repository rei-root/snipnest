#!/usr/bin/env bash
# Собрать один исполняемый файл: dist/snipnest.
#
# Внутри — программа, Qt и переносимый Python (он нужен Python-компонентам).
set -euo pipefail

# shellcheck source=packaging/common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

ensure_runtime
build_pyinstaller onefile

log "Готово: $DIST/snipnest"
