from shared.config import settings


def test_settings_loaded():
    assert settings.max_workers == 1
    assert settings.chunk_size == 2000
    assert settings.yandex_retries == 3


def test_yandex_api_key_present():
    assert settings.yandex_api_key != ""


def test_database_url():
    assert "sqlite" in settings.database_url


def test_jwt_secret_present():
    assert settings.jwt_secret != "change-me-in-production"


def test_default_quota():
    assert settings.default_quota_chars == 1_000_000


def test_auth_enabled():
    assert settings.auth_enabled is True
