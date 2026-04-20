import logging
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from shared.auth import create_access_token
from shared.config import settings
from shared.database import get_db, SessionLocal
from core.middleware import get_current_user
from shared.models import User
from shared.schemas import UserResponse
from shared.yandex_auth import exchange_code_for_token, fetch_yandex_user, get_yandex_login_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/yandex/login")
def yandex_login():
    state = str(uuid.uuid4())
    url = get_yandex_login_url(state=state)
    return RedirectResponse(url=url)


@router.get("/yandex/callback")
def yandex_callback(code: str = None, error: str = None, error_description: str = None, db: Session = Depends(get_db)):
    if error:
        logger.error("Yandex OAuth error: %s — %s", error, error_description)
        msg = error_description or error
        if error == "invalid_scope":
            msg = "Yandex OAuth: requested scope not granted. Open oauth.yandex.ru → your app → Scopes → enable 'login:info' and save."
        return HTMLResponse(
            status_code=400,
            content=f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Auth Error</title>
            <style>body{{font-family:sans-serif;background:#0f172a;color:#f8fafc;display:flex;align-items:center;justify-content:center;min-height:100vh}}
            .box{{background:#1e293b;padding:40px;border-radius:16px;max-width:500px;text-align:center}}
            h1{{color:#f87171}}a{{color:#a855f7}}</style></head><body><div class="box">
            <h1>⚠️ Auth Error</h1><p>{msg}</p>
            <p><a href="/">← Back to login</a></p></div></body></html>""",
        )

    try:
        token_data = exchange_code_for_token(code)
        yandex_access = token_data.get("access_token")
        if not yandex_access:
            raise HTTPException(status_code=400, detail="No access token from Yandex")

        yandex_user = fetch_yandex_user(yandex_access)
    except Exception as e:
        logger.exception("Yandex OAuth failed")
        err_msg = str(e)
        if "invalid_scope" in err_msg.lower():
            err_msg = "Yandex OAuth: requested scope not granted. Open oauth.yandex.ru → your app → Scopes → enable 'login:info' and save."
        return HTMLResponse(
            status_code=400,
            content=f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Auth Error</title>
            <style>body{{font-family:sans-serif;background:#0f172a;color:#f8fafc;display:flex;align-items:center;justify-content:center;min-height:100vh}}
            .box{{background:#1e293b;padding:40px;border-radius:16px;max-width:500px;text-align:center}}
            h1{{color:#f87171}}a{{color:#a855f7}}</style></head><body><div class="box">
            <h1>⚠️ Auth Error</h1><p>{err_msg}</p>
            <p><a href="/">← Back to login</a></p></div></body></html>""",
        )

    user = db.query(User).filter(User.yandex_id == yandex_user["yandex_id"]).first()
    if not user:
        user = User(
            yandex_id=yandex_user["yandex_id"],
            username=yandex_user["username"],
            first_name=yandex_user["display_name"],
            quota_limit=settings.default_quota_chars,
        )
        db.add(user)

    user.last_login_at = datetime.now(timezone.utc)
    if user.username != yandex_user["username"]:
        user.username = yandex_user["username"]
    if user.first_name != yandex_user["display_name"]:
        user.first_name = yandex_user["display_name"]

    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)

    return RedirectResponse(
        url=f"/?token={quote(token, safe='')}&user_id={quote(user.id, safe='')}&username={quote(user.username or '', safe='')}",
        status_code=302,
    )


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        yandex_id=user.yandex_id,
        username=user.username,
        first_name=user.first_name,
        role=user.role,
        quota_used=user.quota_used,
        quota_limit=user.quota_limit,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    user.last_login_at = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        db.commit()
    finally:
        db.close()
    return {"status": "ok"}
