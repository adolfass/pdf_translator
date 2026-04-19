import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from shared.database import get_db
from core.middleware import require_admin
from shared.models import User
from shared.schemas import AdminUserResponse, QuotaUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    users = db.query(User).all()
    return [
        AdminUserResponse(
            id=u.id,
            telegram_id=u.telegram_id,
            username=u.username,
            first_name=u.first_name,
            role=u.role,
            quota_used=u.quota_used,
            quota_limit=u.quota_limit,
            created_at=u.created_at.isoformat() if u.created_at else None,
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        )
        for u in users
    ]


@router.get("/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return AdminUserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        role=user.role,
        quota_used=user.quota_used,
        quota_limit=user.quota_limit,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.patch("/users/{user_id}/quota")
def update_quota(
    user_id: str,
    body: QuotaUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.quota_limit = body.quota_limit
    user.quota_used = 0
    user.quota_reset_at = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    db.commit()
    db.refresh(user)

    return {"status": "ok", "user": AdminUserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        role=user.role,
        quota_used=user.quota_used,
        quota_limit=user.quota_limit,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )}


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    from shared.models import Task

    total_users = db.query(User).count()
    total_tasks = db.query(Task).count()
    completed = db.query(Task).filter(Task.status == "completed").count()
    failed = db.query(Task).filter(Task.status == "failed").count()
    total_chars = db.query(Task).filter(Task.status == "completed").with_entities(
        __import__("sqlalchemy").func.coalesce(__import__("sqlalchemy").func.sum(Task.chars_translated), 0)
    ).scalar()

    return {
        "total_users": total_users,
        "total_tasks": total_tasks,
        "completed_tasks": completed,
        "failed_tasks": failed,
        "total_chars_translated": total_chars,
    }
