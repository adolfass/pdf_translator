import requests

from shared.config import settings

YANDEX_AUTH_URL = "https://oauth.yandex.ru/authorize"
YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"
YANDEX_USER_URL = "https://login.yandex.ru/info"


def get_yandex_login_url(state: str = None) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.yandex_client_id,
        "redirect_uri": settings.yandex_redirect_uri,
        "scope": "login:info",
    }
    if state:
        params["state"] = state
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{YANDEX_AUTH_URL}?{qs}"


def exchange_code_for_token(code: str) -> dict:
    resp = requests.post(
        YANDEX_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.yandex_client_id,
            "client_secret": settings.yandex_client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_yandex_user(access_token: str) -> dict:
    resp = requests.get(
        YANDEX_USER_URL,
        headers={"Authorization": f"OAuth {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    login = data.get("login", "")
    email = data.get("default_email", "")
    name = data.get("real_name", "") or data.get("display_name", "") or login
    return {
        "yandex_id": str(data.get("id", "")),
        "username": login,
        "email": email,
        "display_name": name,
        "avatar_url": data.get("default_avatar_id", ""),
    }
