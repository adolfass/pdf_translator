import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from shared.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def create_access_token(user_id: str, role: str = "user") -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def verify_telegram_init_data(data: dict, bot_token: str) -> Optional[dict]:
    received_hash = data.pop("hash", None)
    if not received_hash:
        return None

    auth_date = int(data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        return None

    sorted_params = sorted(f"{k}={v}" for k, v in data.items())
    data_check_string = "\n".join(sorted_params)

    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    return {
        "telegram_id": int(data.get("id", 0)),
        "username": data.get("username", ""),
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "photo_url": data.get("photo_url", ""),
    }
