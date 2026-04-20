import logging
import os
import uuid
from datetime import datetime, timezone

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
def yandex_callback(code: str, db: Session = Depends(get_db)):
    try:
        token_data = exchange_code_for_token(code)
        yandex_access = token_data.get("access_token")
        if not yandex_access:
            raise HTTPException(status_code=400, detail="No access token from Yandex")

        yandex_user = fetch_yandex_user(yandex_access)
    except Exception as e:
        logger.exception("Yandex OAuth failed")
        raise HTTPException(status_code=400, detail=f"Yandex auth failed: {e}")

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
        url=f"/?token={token}&user_id={user.id}&username={user.username}",
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
