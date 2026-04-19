import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from shared.database import get_db, SessionLocal
from core.middleware import check_quota, get_current_user, limiter
from shared.models import Task, User
from worker.engine import process_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
def healthcheck(db: Session = Depends(get_db)):
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/upload")
@limiter.limit("2/minute")
async def upload_pdf(
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    check_quota(user)

    task_id = str(uuid.uuid4())
    tmp_dir = os.path.join("tmp", task_id)
    os.makedirs(tmp_dir, exist_ok=True)
    pdf_path = os.path.join(tmp_dir, file.filename)

    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    task = Task(
        id=task_id,
        user_id=user.id,
        status="pending",
        original_filename=file.filename,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(process_task, task_id, pdf_path, user.id)

    return {"task_id": task_id, "status": "pending", "filename": file.filename}


@router.get("/status/{task_id}")
def get_status(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
    except Exception:
        task = None
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id and task.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "error_msg": task.error_msg,
        "chars_translated": task.chars_translated,
        "original_filename": task.original_filename,
        "result_filename": task.result_filename,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.get("/download/{task_id}")
def download_result(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result_dir = os.path.join("results", task_id)
    zip_path = os.path.join(result_dir, "result.zip")

    if not os.path.exists(zip_path):
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
        except Exception:
            task = None

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        if task.user_id and task.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        if task.status == "failed":
            raise HTTPException(status_code=500, detail=f"Task failed: {task.error_msg}")
        if task.status != "completed":
            raise HTTPException(status_code=400, detail=f"Task not ready: {task.status}")
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        path=zip_path,
        filename="translated.zip",
        media_type="application/zip",
    )
