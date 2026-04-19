import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from shared.auth import create_access_token, verify_telegram_init_data
from shared.config import settings
from shared.database import get_db
from core.middleware import check_quota, get_current_user
from shared.models import User
from shared.schemas import AuthResponse, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/telegram")
def telegram_login(request: Request, db: Session = Depends(get_db)):
    form = request.query_params
    data = dict(form)

    user_info = verify_telegram_init_data(data, settings.telegram_bot_token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth data")

    user = db.query(User).filter(User.telegram_id == user_info["telegram_id"]).first()
    if not user:
        user = User(
            telegram_id=user_info["telegram_id"],
            username=user_info.get("username"),
            first_name=user_info.get("first_name"),
            quota_limit=settings.default_quota_chars,
        )
        db.add(user)

    user.last_login_at = datetime.now(timezone.utc)

    if user.username != user_info.get("username"):
        user.username = user_info.get("username")
    if user.first_name != user_info.get("first_name"):
        user.first_name = user_info.get("first_name")

    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.role)

    return AuthResponse(
        access_token=token,
        user={
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "role": user.role,
            "quota_used": user.quota_used,
            "quota_limit": user.quota_limit,
        },
    )


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
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
    from shared.database import SessionLocal
    db = SessionLocal()
    try:
        db.commit()
    finally:
        db.close()
    return {"status": "ok"}
