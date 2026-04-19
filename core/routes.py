import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from shared.database import get_db, SessionLocal
from shared.models import Task
from worker.engine import process_task

router = APIRouter()


@router.get("/health")
def healthcheck():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/upload")
async def upload_pdf(file: UploadFile, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    task_id = str(uuid.uuid4())
    tmp_dir = os.path.join("tmp", task_id)
    os.makedirs(tmp_dir, exist_ok=True)
    pdf_path = os.path.join(tmp_dir, file.filename)

    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    task = Task(
        id=task_id,
        status="pending",
        original_filename=file.filename,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(process_task, task_id, pdf_path)

    return {"task_id": task_id, "status": "pending", "filename": file.filename}


@router.get("/status/{task_id}")
def get_status(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

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
def download_result(task_id: str):
    result_dir = os.path.join("results", task_id)
    zip_path = os.path.join(result_dir, "result.zip")

    if not os.path.exists(zip_path):
        task_db = SessionLocal()
        try:
            task = task_db.query(Task).filter(Task.id == task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            if task.status == "failed":
                raise HTTPException(status_code=500, detail=f"Task failed: {task.error_msg}")
            if task.status != "completed":
                raise HTTPException(status_code=400, detail=f"Task not ready: {task.status}")
        finally:
            task_db.close()
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        path=zip_path,
        filename="translated.zip",
        media_type="application/zip",
    )
