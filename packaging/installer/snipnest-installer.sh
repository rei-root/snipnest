#!/bin/sh
# Установщик Snipnest.
#
# Один файл, внутри которого нет приложения: установщик определяет семейство
# дистрибутива и ставит приложение его родным способом — пакетом .deb на
# debian-системах и переносимым образом в /opt на остальных.
#
# Написано на POSIX shell: установщик запускается раньше, чем в системе
# появилось приложение, поэтому он должен работать везде, где есть /bin/sh.
set -eu

VERSION="@VERSION@"
RELEASE_URL="@RELEASE_URL@"
APPIMAGE_NAME="@APPIMAGE_NAME@"
DEB_NAME="@DEB_NAME@"
MIN_GLIBC="@MIN_GLIBC@"

MODE="system"
DRY_RUN=0
ASSUME_YES=0
LOCAL_FILE=""
OS_RELEASE="${SNIPNEST_OS_RELEASE:-/etc/os-release}"

SYSTEM_DIR="/opt/snipnest"
SYSTEM_BIN="/usr/local/bin"
SYSTEM_DESKTOP="/usr/share/applications"
SYSTEM_ICONS="/usr/share/icons/hicolor"

log() {
    printf '%s\n' "$*"
}

warn() {
    printf 'ВНИМАНИЕ: %s\n' "$*" >&2
}

fail() {
    printf 'ОШИБКА: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat <<'EOF'
Установщик Snipnest.

Использование:
  snipnest-installer-linux-amd64.bin [ключи]

Ключи:
  --user           поставить в домашний каталог, без прав администратора
  --local ФАЙЛ     поставить из локального файла, без сети
  --url АДРЕС       брать файлы по другому адресу (по умолчанию — релиз)
  --dry-run        показать план установки и ничего не делать
  --yes            не спрашивать подтверждения
  --version        показать версию установщика
  --help           показать эту справку

Что делает установщик:
  * определяет семейство дистрибутива по /etc/os-release;
  * на debian-based ставит пакет .deb через apt-get (запасной путь — dpkg);
  * на остальных кладёт переносимый образ в /opt/snipnest, делает лаунчер
    в /usr/local/bin, ярлык в /usr/share/applications и иконки;
  * с ключом --user всё это делается в домашнем каталоге.

Файл установщика из релиза хранится без исполняемого бита: перед запуском
сделайте его исполняемым — chmod +x snipnest-installer-linux-amd64.bin
EOF
}

# --- разбор ключей ---------------------------------------------------------

while [ $# -gt 0 ]; do
    case "$1" in
        --user) MODE="user" ;;
        --dry-run) DRY_RUN=1 ;;
        --yes|-y) ASSUME_YES=1 ;;
        --local)
            [ $# -ge 2 ] || fail "--local требует путь к файлу"
            LOCAL_FILE="$2"
            shift
            ;;
        --url)
            [ $# -ge 2 ] || fail "--url требует адрес"
            RELEASE_URL="$2"
            shift
            ;;
        --version)
            printf 'snipnest-installer %s\n' "$VERSION"
            exit 0
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *) fail "неизвестный ключ: $1 (справка: --help)" ;;
    esac
    shift
done

if [ "$MODE" = "user" ]; then
    HOME_DIR="${HOME:-/tmp}"
    SYSTEM_DIR="$HOME_DIR/.local/opt/snipnest"
    SYSTEM_BIN="$HOME_DIR/.local/bin"
    SYSTEM_DESKTOP="$HOME_DIR/.local/share/applications"
    SYSTEM_ICONS="$HOME_DIR/.local/share/icons/hicolor"
fi

# --- система ---------------------------------------------------------------

detect_family() {
    id=""
    id_like=""
    if [ -r "$OS_RELEASE" ]; then
        while IFS='=' read -r key value; do
            case "$key" in
                ID) id="$value" ;;
                ID_LIKE) id_like="$value" ;;
            esac
        done < "$OS_RELEASE"
    fi
    case " $id $id_like " in
        *debian*) printf 'debian\n'; return ;;
        *arch*|*manjaro*|*endeavour*) printf 'arch\n'; return ;;
        *fedora*|*rhel*|*centos*|*rocky*|*alma*) printf 'rhel\n'; return ;;
        *suse*|*opensuse*) printf 'suse\n'; return ;;
        *gentoo*) printf 'gentoo\n'; return ;;
        *alpine*) printf 'alpine\n'; return ;;
    esac
    printf 'unknown\n'
}

detect_glibc() {
    if command -v getconf >/dev/null 2>&1; then
        version="$(getconf GNU_LIBC_VERSION 2>/dev/null || true)"
        case "$version" in
            glibc\ *) printf '%s\n' "${version#glibc }"; return ;;
        esac
    fi
    if command -v ldd >/dev/null 2>&1; then
        ldd --version 2>/dev/null | head -1 | sed -n 's/.*[^0-9]\([0-9][0-9.]*\).*/\1/p'
        return
    fi
    printf '\n'
}

version_ge() {
    # version_ge A B — истина, когда A не меньше B.
    if [ -z "$2" ]; then
        return 0
    fi
    lowest="$(printf '%s\n%s\n' "$2" "$1" | sort -V 2>/dev/null | head -1)"
    [ "$lowest" = "$2" ]
}

as_root() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        fail "нужны права администратора, а sudo нет"
    fi
}

run_priv() {
    # В домашнем режиме права не нужны: файлы и так принадлежат человеку.
    if [ "$MODE" = "user" ]; then
        "$@"
    else
        as_root "$@"
    fi
}

download() {
    url="$1"
    dest="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL --retry 3 --retry-delay 2 -o "$dest" "$url" \
            || fail "не удалось скачать $url"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$dest" "$url" || fail "не удалось скачать $url"
    else
        fail "нечем скачивать: нет ни curl, ни wget"
    fi
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | cut -d' ' -f1
    else
        printf '\n'
    fi
}

confirm() {
    [ "$ASSUME_YES" -eq 1 ] && return 0
    printf 'Продолжить? [y/N] '
    read -r answer || answer=""
    case "$answer" in
        y|Y|yes|Yes) return 0 ;;
    esac
    fail "установка отменена"
}

# --- план ------------------------------------------------------------------

FAMILY="$(detect_family)"
GLIBC="$(detect_glibc)"

plan_deb() {
    file="$1"
    log "семейство: debian (пакет .deb)"
    log "файл: $file"
    log "команда: apt-get install -y <абсолютный путь к $file>"
    log "запасной путь: dpkg -i <абсолютный путь к $file>"
}

plan_image() {
    file="$1"
    log "семейство: $FAMILY (переносимый образ)"
    log "файл: $file"
    log "каталог: $SYSTEM_DIR"
    log "лаунчер: $SYSTEM_BIN/snipnest"
    log "ярлык: $SYSTEM_DESKTOP/snipnest.desktop"
    log "иконки: $SYSTEM_ICONS"
}

# --- установка -------------------------------------------------------------

# Путь к файлу для apt: абсолютный — как есть, относительный — с «./».
# Смесь вида «.//tmp/…» apt не берёт: «E: В командной строке указан
# неподдерживаемый файл».
apt_path() {
    case "$1" in
        /*) printf '%s\n' "$1" ;;
        *) printf './%s\n' "$1" ;;
    esac
}

# Каталог для копии пакета, которую прочтёт служебный пользователь apt
# (_apt). apt не работает в песочнице, если файл этому пользователю
# недоступен, и печатает «Отказано в доступе». Поэтому каталог доступен
# всем на чтение и обход (0755), а файл — на чтение (0644).
stage_dir() {
    for base in /var/tmp /tmp; do
        [ -d "$base" ] || continue
        dir="$(mktemp -d "$base/snipnest.XXXXXX" 2>/dev/null)" || continue
        chmod 755 "$dir"
        printf '%s\n' "$dir"
        return 0
    done
    return 1
}

install_deb() {
    file="$1"
    dir="$(stage_dir)" || fail "негде создать временный каталог для пакета"
    stage="$dir"
    package="$dir/$DEB_NAME"
    cp "$file" "$package" || fail "не удалось подготовить пакет $DEB_NAME"
    chmod 644 "$package"

    log "Ставлю пакет $DEB_NAME"
    if command -v apt-get >/dev/null 2>&1; then
        if run_priv apt-get install -y "$(apt_path "$package")"; then
            log "Пакет $DEB_NAME поставлен через apt-get."
            return 0
        fi
        warn "apt-get не справился — ставлю через dpkg"
    fi
    if command -v dpkg >/dev/null 2>&1; then
        if run_priv dpkg -i "$package"; then
            log "Пакет $DEB_NAME поставлен через dpkg."
            return 0
        fi
    fi
    fail "не удалось поставить пакет $DEB_NAME"
}

install_image() {
    file="$1"
    log "Кладу образ в $SYSTEM_DIR"
    run_priv mkdir -p "$SYSTEM_DIR" "$SYSTEM_BIN" "$SYSTEM_DESKTOP" "$SYSTEM_ICONS"
    run_priv cp "$file" "$SYSTEM_DIR/snipnest.AppImage"
    run_priv chmod 755 "$SYSTEM_DIR/snipnest.AppImage"

    # Ярлык и иконка берутся из самого образа: он собран из тех же файлов,
    # что и меню приложений.
    extract="$work/extract"
    mkdir -p "$extract"
    if (cd "$extract" && "$SYSTEM_DIR/snipnest.AppImage" --appimage-extract >/dev/null 2>&1); then
        if [ -f "$extract/squashfs-root/snipnest.desktop" ]; then
            run_priv cp "$extract/squashfs-root/snipnest.desktop" \
                "$SYSTEM_DESKTOP/snipnest.desktop"
        fi
        if [ -f "$extract/squashfs-root/snipnest.png" ]; then
            for size in 16 24 32 48 64 128 256 512; do
                run_priv mkdir -p "$SYSTEM_ICONS/${size}x${size}/apps"
                run_priv cp "$extract/squashfs-root/snipnest.png" \
                    "$SYSTEM_ICONS/${size}x${size}/apps/snipnest.png"
            done
        fi
    else
        warn "не удалось распаковать образ: ярлык и иконка не поставлены"
    fi

    cat > "$work/launcher" <<EOF
#!/bin/sh
# Запуск Snipnest, установленного установщиком.
exec "$SYSTEM_DIR/snipnest.AppImage" "\$@"
EOF
    run_priv cp "$work/launcher" "$SYSTEM_BIN/snipnest"
    run_priv chmod 755 "$SYSTEM_BIN/snipnest"
}

# --- ход установки ---------------------------------------------------------

log "Snipnest $VERSION — установщик"
log "система: $FAMILY, glibc ${GLIBC:-неизвестно} (нужен не ниже $MIN_GLIBC)"

if [ -n "$GLIBC" ] && ! version_ge "$GLIBC" "$MIN_GLIBC"; then
    fail "на этой системе glibc $GLIBC, а программы собраны под $MIN_GLIBC и новее не запустятся"
fi

work="$(mktemp -d)"
stage=""
trap 'rm -rf "$work" || true; [ -n "$stage" ] && rm -rf "$stage" || true' EXIT

if [ "$FAMILY" = "debian" ] && [ "$MODE" = "system" ]; then
    name="$DEB_NAME"
else
    name="$APPIMAGE_NAME"
fi

if [ "$DRY_RUN" -eq 1 ]; then
    # Показываем план и ничего не качаем: человек должен увидеть, что
    # будет сделано, до того как согласится.
    if [ "$FAMILY" = "debian" ] && [ "$MODE" = "system" ]; then
        plan_deb "$name"
    else
        plan_image "$name"
    fi
    log "план показан, ничего не ставлю"
    exit 0
fi

if [ -n "$LOCAL_FILE" ]; then
    [ -f "$LOCAL_FILE" ] || fail "файла нет: $LOCAL_FILE"
    log "беру локальный файл: $LOCAL_FILE"
    file="$LOCAL_FILE"
else
    url="$RELEASE_URL/$name"
    log "качаю $url"
    file="$work/$name"
    download "$url" "$file"

    sums="$work/SHA256SUMS"
    if download "$RELEASE_URL/SHA256SUMS" "$sums" 2>/dev/null; then
        expected="$(grep " $name\$" "$sums" | cut -d' ' -f1 | head -1)"
        actual="$(sha256_of "$file")"
        if [ -n "$expected" ] && [ -n "$actual" ] && [ "$expected" != "$actual" ]; then
            fail "контрольная сумма не совпала: файл повреждён или подменён"
        fi
        log "контрольная сумма сходится"
    else
        warn "не удалось скачать SHA256SUMS — сумму не проверяю"
    fi
fi

if [ "$FAMILY" = "debian" ] && [ "$MODE" = "system" ]; then
    confirm
    install_deb "$file"
else
    confirm
    install_image "$file"
fi

log "Готово. Приложение доступно как snipnest."
log "Компоненты (gallery-dl, yt-dlp, ffmpeg) мастер поставит при первом запуске."
