"""Тесты настроек: папка сохранения и токен в системном хранилище."""

from __future__ import annotations

import json
import stat

from gallary_downloader.settings import (
    DEFAULT_DESTINATION,
    FileSecretStore,
    Settings,
)


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
