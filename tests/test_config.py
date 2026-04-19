from shared.config import settings


def test_settings_loaded():
    assert settings.max_workers == 1
    assert settings.chunk_size == 2000
    assert settings.yandex_retries == 3


def test_yandex_api_key_present():
    assert settings.yandex_api_key != ""


def test_database_url():
    assert "sqlite" in settings.database_url
