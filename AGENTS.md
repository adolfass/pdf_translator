# PDF Translator — Agent Guide

## Project
Convert English technical PDFs → Russian Markdown + images → ZIP download.

## Stack
Python 3.10, FastAPI, uvicorn, SQLite (WAL mode), SQLAlchemy, marker-pdf, Yandex Translate API, tenacity (retry), Nginx reverse proxy, systemd.

## Server Context
- Host: 157.22.175.40 (Ubuntu 22.04, 4vCPU, 8GB RAM, 80GB NVMe)
- Domain: book.itplane.ru
- Work dir: /var/www/pdf-translator
- Other projects in /var/www/ — do not touch them
- Nginx already running (ports 80/443/3000). Redis on :6379. Docker on :3001. PostgreSQL (docker) on localhost:5432.
- Existing nginx sites: itplane.ru, mcp.itplane.ru, mcp-saas, planer.itplane.ru

## Hard Constraints
- **MAX_WORKERS=1** — marker-pdf peaks at ~3.5GB RAM. Never increase.
- **No secrets in git** — use pydantic-settings + .env (gitignored).
- **Backup configs before editing** — nginx, systemd, .env.
- **Do not modify other /var/www/ projects.**

## Code Layout
```
shared/    config.py, database.py, models.py
worker/    engine.py, retry.py
core/      app.py, routes.py
tests/     conftest.py, test_*.py
deploy/    setup.sh, pdf-translator.service, nginx.conf
```

## Key Implementation Details
- **SQLite**: WAL mode. Task model fields: id, status, progress, error_msg, chars_translated, timestamps.
- **Yandex Translate**: Use tenacity for retry + circuit breaker.
- **marker-pdf**: Wrapper with fallback to `--force_ocr`.
- **FastAPI endpoints**: healthcheck, upload, status, download.
- **systemd**: Service unit for uvicorn. Nginx reverse proxy to book.itplane.ru.
- **Cron**: Cleanup completed tasks/files older than 7 days.

## Developer Commands
```bash
# Create venv (first time)
python3 -m venv venv && source venv/bin/activate

# Install deps
pip install fastapi uvicorn sqlalchemy marker-pdf requests tenacity pytest python-dotenv pydantic-settings

# Run dev server
uvicorn core.app:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v

# Deploy
systemctl daemon-reload && systemctl restart pdf-translator
nginx -t && systemctl reload nginx
```

## Git
- Remote: https://github.com/adolfass/pdf_translator
- .env must stay local — never commit.
