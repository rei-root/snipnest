"""Тесты настроек: папка сохранения и токен в системном хранилище."""

from __future__ import annotations

import importlib
import json
import stat

from snipnest.settings import (
    DEFAULT_DESTINATION,
    DEFAULT_THEME,
    FileSecretStore,
    Settings,
)


def test_тема_по_умолчанию_как_в_системе(tmp_path) -> None:
    """Пока владелец не выбрал тему, приложение следует системной."""
    settings = Settings(
        config_path=tmp_path / "settings.json",
        secret_store=FileSecretStore(tmp_path / "secret"),
    )
    assert settings.theme == DEFAULT_THEME
    assert settings.theme == "system"


def test_тема_сохраняется_и_читается(tmp_path) -> None:
    """Выбранная тема помнится между запусками приложения."""
    config = tmp_path / "settings.json"
    first = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    first.theme = "dark"
    first.save()

    second = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    assert second.theme == "dark"


def test_путь_по_умолчанию_указывает_на_изображения_pinterest() -> None:
    assert DEFAULT_DESTINATION.name == "Pinterest"
    assert DEFAULT_DESTINATION.parent.name == "Изображения"


def test_папка_сохранения_запоминается_между_запусками(tmp_path) -> None:
    config = tmp_path / "settings.json"
    first = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    first.destination = str(tmp_path / "downloads")
    first.save()

    second = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    assert second.destination == str(tmp_path / "downloads")


def test_битый_конфиг_не_ломает_загрузку_настроек(tmp_path) -> None:
    config = tmp_path / "settings.json"
    config.write_text("{ это не json", encoding="utf-8")
    settings = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    assert settings.destination


def test_токен_не_попадает_в_конфиг(tmp_path) -> None:
    config = tmp_path / "settings.json"
    store = FileSecretStore(tmp_path / "secret")
    settings = Settings(config_path=config, secret_store=store)
    settings.set_token("secret-token-value")
    settings.save()

    raw = config.read_text(encoding="utf-8")
    assert "secret-token-value" not in raw
    assert "secret-token-value" not in json.loads(raw).get("destination", "")


def test_файловый_секрет_хранится_с_правами_600(tmp_path) -> None:
    store = FileSecretStore(tmp_path / "secret")
    store.set("secret-token-value")
    mode = stat.S_IMODE((tmp_path / "secret").stat().st_mode)
    assert mode == 0o600


def test_токен_читается_обратно(tmp_path) -> None:
    store = FileSecretStore(tmp_path / "secret")
    settings = Settings(config_path=tmp_path / "settings.json", secret_store=store)
    settings.set_token("secret-token-value")
    assert settings.token == "secret-token-value"


def test_путь_к_gallery_dl_запоминается(tmp_path) -> None:
    config = tmp_path / "settings.json"
    first = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    first.gallery_dl_path = "/usr/bin/gallery-dl"
    first.save()

    second = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    assert second.gallery_dl_path == "/usr/bin/gallery-dl"


def test_путь_к_yt_dlp_запоминается(tmp_path) -> None:
    config = tmp_path / "settings.json"
    first = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    first.yt_dlp_path = "/usr/bin/yt-dlp"
    first.save()

    second = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    assert second.yt_dlp_path == "/usr/bin/yt-dlp"


def test_источник_cookies_запоминается(tmp_path) -> None:
    """Источник cookies — не секрет, он лежит рядом с путями к бинарникам."""
    config = tmp_path / "settings.json"
    first = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    first.cookies_browser = "firefox:abc.default-release"
    first.cookies_file = ""
    first.save()

    second = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    assert second.cookies_browser == "firefox:abc.default-release"
    assert second.cookies_file == ""


def test_путь_к_файлу_cookies_запоминается(tmp_path) -> None:
    config = tmp_path / "settings.json"
    first = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    first.cookies_file = "/home/sato/cookies.txt"
    first.save()

    second = Settings(config_path=config, secret_store=FileSecretStore(tmp_path / "secret"))
    assert second.cookies_file == "/home/sato/cookies.txt"


def test_старые_настройки_переносятся_в_новый_каталог(tmp_path) -> None:
    """После переименования настройки старого приложения не теряются."""
    migration = importlib.import_module("snipnest.migration")
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "settings.json").write_text(
        json.dumps({"destination": "/tmp/downloads"}), encoding="utf-8"
    )
    new_dir = tmp_path / "new"

    moved = migration.migrate_settings(legacy_dir, new_dir)

    assert moved
    moved_settings = json.loads((new_dir / "settings.json").read_text(encoding="utf-8"))
    assert moved_settings["destination"] == "/tmp/downloads"


def test_новые_настройки_не_перетираются_старыми(tmp_path) -> None:
    migration = importlib.import_module("snipnest.migration")
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "settings.json").write_text(
        json.dumps({"destination": "/tmp/legacy"}), encoding="utf-8"
    )
    new_dir = tmp_path / "new"
    new_dir.mkdir()
    (new_dir / "settings.json").write_text(
        json.dumps({"destination": "/tmp/current"}), encoding="utf-8"
    )

    moved = migration.migrate_settings(legacy_dir, new_dir)

    assert not moved
    kept = json.loads((new_dir / "settings.json").read_text(encoding="utf-8"))
    assert kept["destination"] == "/tmp/current"


def test_токен_переносится_из_старого_хранилища(monkeypatch) -> None:
    """Токен из старого keyring-сервиса переносится в новый."""
    migration = importlib.import_module("snipnest.migration")
    stored: dict[tuple[str, str], str] = {("old-service", "pinterest-token"): "token-value"}
    monkeypatch.setattr(
        migration.keyring,
        "get_password",
        lambda service, username: stored.get((service, username)),
    )
    monkeypatch.setattr(
        migration.keyring,
        "set_password",
        lambda service, username, secret: stored.__setitem__((service, username), secret),
    )

    moved = migration.migrate_token("old-service", "snipnest", "pinterest-token")

    assert moved
    assert stored[("snipnest", "pinterest-token")] == "token-value"


def test_при_своём_токене_старый_хранилище_не_трогается(monkeypatch) -> None:
    migration = importlib.import_module("snipnest.migration")
    stored: dict[tuple[str, str], str] = {
        ("old-service", "pinterest-token"): "old-value",
        ("snipnest", "pinterest-token"): "current-value",
    }
    monkeypatch.setattr(
        migration.keyring,
        "get_password",
        lambda service, username: stored.get((service, username)),
    )
    monkeypatch.setattr(
        migration.keyring,
        "set_password",
        lambda service, username, secret: stored.__setitem__((service, username), secret),
    )

    moved = migration.migrate_token("old-service", "snipnest", "pinterest-token")

    assert not moved
    assert stored[("snipnest", "pinterest-token")] == "current-value"
