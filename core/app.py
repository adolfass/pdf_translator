import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from shared.config import settings
from shared.database import init_db

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs("data", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    os.makedirs("tmp", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    yield


app = FastAPI(
    title="PDF Translator",
    description="Convert English PDFs to Russian Markdown + images → ZIP",
    version="0.1.0",
    lifespan=lifespan,
)

from core.routes import router  # noqa: E402

app.include_router(router)
