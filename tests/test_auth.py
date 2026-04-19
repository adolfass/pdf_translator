import hashlib
import hmac
import time

import pytest

from shared.auth import verify_telegram_init_data, create_access_token, decode_access_token

BOT_TOKEN = "test-bot-token-123"


def make_telegram_data(overrides=None):
    data = {
        "id": "12345",
        "username": "testuser",
        "first_name": "Test",
        "auth_date": str(int(time.time())),
    }
    if overrides:
        data.update(overrides)

    sorted_params = sorted(f"{k}={v}" for k, v in data.items())
    data_check_string = "\n".join(sorted_params)
    secret_key = hashlib.sha256(BOT_TOKEN.encode("utf-8")).digest()
    data["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return data


def test_valid_telegram_hash():
    data = make_telegram_data()
    result = verify_telegram_init_data(data, BOT_TOKEN)
    assert result is not None
    assert result["telegram_id"] == 12345
    assert result["username"] == "testuser"
    assert result["first_name"] == "Test"


def test_invalid_telegram_hash():
    data = make_telegram_data()
    data["hash"] = "invalidhash123"
    result = verify_telegram_init_data(data, BOT_TOKEN)
    assert result is None


def test_expired_telegram_auth():
    data = make_telegram_data({"auth_date": str(int(time.time()) - 90000)})
    result = verify_telegram_init_data(data, BOT_TOKEN)
    assert result is None


def test_missing_hash():
    data = make_telegram_data()
    del data["hash"]
    result = verify_telegram_init_data(data, BOT_TOKEN)
    assert result is None


def test_jwt_token_roundtrip():
    user_id = "test-user-uuid"
    token = create_access_token(user_id, role="user")
    assert token is not None

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["role"] == "user"
    assert "exp" in payload
    assert "iat" in payload


def test_jwt_expired_token():
    import jwt
    from datetime import datetime, timezone, timedelta

    expired_payload = {
        "sub": "test-user",
        "role": "user",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    from shared.config import settings
    token = jwt.encode(expired_payload, settings.jwt_secret, algorithm="HS256")

    result = decode_access_token(token)
    assert result is None


def test_jwt_invalid_token():
    result = decode_access_token("not-a-valid-token")
    assert result is None
