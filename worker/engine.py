import logging
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

import requests

from shared.config import settings
from shared.database import SessionLocal
from shared.models import Task
from worker.retry import yandex_retry_policy, circuit_guard

logger = logging.getLogger(__name__)

YANDEX_URL = "https://translate.api.cloud.yandex.net/translate/v2/translate"


def _translate_chunk(text: str, target_lang: str = "ru") -> str:
    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "texts": [text],
        "targetLanguageCode": target_lang,
        "folderId": settings.yandex_folder_id,
    }
    resp = requests.post(YANDEX_URL, headers=headers, json=body, timeout=settings.yandex_timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["translations"][0]["text"]


@circuit_guard
@yandex_retry_policy()
def translate_text(text: str, target_lang: str = "ru") -> str:
    return _translate_chunk(text, target_lang)


def translate_document(text: str, chunk_size: int = None) -> str:
    chunk_size = chunk_size or settings.chunk_size
    parts = []
    total = len(text)
    translated_chars = 0

    for i in range(0, total, chunk_size):
        chunk = text[i:i + chunk_size]
        translated = translate_text(chunk)
        parts.append(translated)
        translated_chars += len(chunk)

        if settings.delay_sec > 0:
            time.sleep(settings.delay_sec)

    return "".join(parts)


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import text_from_rendered

        converter = PdfConverter(artifact_dict=create_model_dict())
        rendered = converter(pdf_path)
        text, _, images = text_from_rendered(rendered)
        return text, images
    except Exception:
        logger.warning("Marker failed, falling back to force_ocr")
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import text_from_rendered

        converter = PdfConverter(artifact_dict=create_model_dict(), config={"force_ocr": True})
        rendered = converter(pdf_path)
        text, _, images = text_from_rendered(rendered)
        return text, images


def create_zip_archive(markdown_text: str, images: dict, output_dir: str) -> str:
    zip_path = os.path.join(output_dir, "result.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("document.md", markdown_text)
        for img_name, img_data in images.items():
            if hasattr(img_data, "save"):
                import io
                buf = io.BytesIO()
                img_data.save(buf, format="PNG")
                buf.seek(0)
                zf.writestr(f"images/{img_name}", buf.read())
            elif isinstance(img_data, bytes):
                zf.writestr(f"images/{img_name}", img_data)
    return zip_path


def process_task(task_id: str, pdf_path: str):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error("Task %s not found", task_id)
            return

        task.status = "processing"
        task.progress = 0.0
        db.commit()

        # Step 1: Extract text from PDF
        logger.info("Extracting text from %s", pdf_path)
        task.progress = 10.0
        db.commit()

        text, images = extract_text_from_pdf(pdf_path)
        task.progress = 30.0
        db.commit()

        # Step 2: Translate
        logger.info("Translating document (%d chars)", len(text))
        task.progress = 40.0
        db.commit()

        translated = translate_document(text)
        task.chars_translated = len(translated)
        task.progress = 80.0
        db.commit()

        # Step 3: Create ZIP
        logger.info("Creating ZIP archive")
        result_dir = os.path.join(os.path.dirname(__file__), "..", "results", task_id)
        os.makedirs(result_dir, exist_ok=True)
        zip_path = create_zip_archive(translated, images, result_dir)

        task.result_filename = os.path.basename(zip_path)
        task.status = "completed"
        task.progress = 100.0
        task.completed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.commit()

        logger.info("Task %s completed: %s", task_id, zip_path)

    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "failed"
            task.error_msg = str(exc)
            db.commit()
    finally:
        db.close()
