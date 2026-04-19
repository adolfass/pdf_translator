from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from shared.auth import decode_access_token
from shared.config import settings
from shared.database import get_db
from shared.models import User

security = HTTPBearer(auto_error=False)

limiter = Limiter(key_func=get_remote_address)


def get_user_id_from_request(request: Request) -> str:
    creds: Optional[HTTPAuthorizationCredentials] = request.state.credentials if hasattr(request.state, "credentials") else None
    if creds:
        payload = decode_access_token(creds.credentials)
        if payload:
            return payload.get("sub", "anonymous")
    return get_remote_address(request)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not settings.auth_enabled:
        return _get_or_create_default_user(db)

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    _reset_quota_if_needed(user, db)

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def check_quota(user: User):
    if user.role == "admin":
        return
    if user.quota_used >= user.quota_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Quota exceeded. Used {user.quota_used:,} of {user.quota_limit:,} chars. Resets monthly.",
        )


def _get_or_create_default_user(db: Session) -> User:
    user = db.query(User).filter(User.telegram_id == 0).first()
    if not user:
        user = User(
            telegram_id=0,
            username="anonymous",
            first_name="Anonymous",
            role="admin",
            quota_limit=999_999_999,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _reset_quota_if_needed(user: User, db: Session):
    if user.role == "admin":
        return
    now = datetime.now(timezone.utc)
    reset_at = user.quota_reset_at
    if reset_at and reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=timezone.utc)
    if reset_at and now >= reset_at:
        user.quota_used = 0
        user.quota_reset_at = _next_month(now)
        db.commit()
    elif not user.quota_reset_at:
        user.quota_reset_at = _next_month(now)
        db.commit()


def _next_month(dt: datetime) -> datetime:
    month = dt.month + 1 if dt.month < 12 else 1
    year = dt.year if dt.month < 12 else dt.year + 1
    return dt.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
