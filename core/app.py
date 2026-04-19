import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from shared.config import settings
from shared.database import init_db

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from core.middleware import limiter  # noqa: E402


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
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"https://{settings.telegram_bot_domain}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from core.routes import router as api_router  # noqa: E402
from core.routes_auth import router as auth_router  # noqa: E402
from core.routes_admin import router as admin_router  # noqa: E402

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(admin_router)
