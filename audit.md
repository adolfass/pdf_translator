# Server Audit Report — 2026-04-19

## 1. SYSTEM

| Item | Value |
|------|-------|
| OS | Ubuntu 22.04.2 LTS (Jammy Jellyfish) |
| Kernel | 5.15.0-174-generic |
| Timezone | Etc/UTC |
| NTP | Active, synchronized |

## 2. RESOURCES

| Resource | Total | Used | Free | Available |
|----------|-------|------|------|-----------|
| CPU | 4 vCPU | — | — | — |
| RAM | 7937 MB | 743 MB | 4614 MB | 6870 MB |
| Disk (/) | 79 GB | 25 GB (33%) | 51 GB | — |
| Swap | 1023 MB | 0 MB | 1023 MB | — |

## 3. SERVICES (filtered)

| Service | Status |
|---------|--------|
| nginx.service | ✅ active (running) |
| docker.service | ✅ active (running) |
| redis-server.service | ✅ active (running) |
| postgresql | ❌ Not a systemd service — runs in Docker on localhost:5432 |
| python/uvicorn | ❌ Not running |
| pdf-translator | ❌ Not deployed |

## 4. NETWORK

| Port | Process | Bind |
|------|---------|------|
| 80 | nginx | 0.0.0.0 |
| 443 | nginx | 0.0.0.0 |
| 3000 | nginx | 0.0.0.0 |
| 3001 | docker-proxy | 0.0.0.0 |
| 5432 | docker-proxy (PostgreSQL) | 127.0.0.1 |
| 6379 | redis-server | 127.0.0.1 |
| 22 | sshd | 0.0.0.0 |
| 1080 | 3proxy | 0.0.0.0 |
| 3128 | 3proxy | 0.0.0.0 |

### Nginx sites-enabled

| Site | Target |
|------|--------|
| default | /etc/nginx/sites-available/default |
| itplane.ru | /etc/nginx/sites-available/itplane.ru |
| mcp.itplane.ru | /etc/nginx/sites-available/mcp.itplane.ru |
| mcp-saas | /etc/nginx/sites-available/mcp-saas |
| planer.itplane.ru | /etc/nginx/sites-available/planer.itplane.ru |

## 5. PYTHON

| Package | Status | Version |
|---------|--------|---------|
| Python | ✅ Installed | 3.10.12 |
| fastapi | ✅ Installed | 0.135.2 |
| uvicorn | ✅ Installed | 0.42.0 |
| SQLAlchemy | ✅ Installed | 2.0.48 |
| tenacity | ✅ Installed | 9.1.4 |
| pytest | ✅ Installed | 9.0.2 |
| pydantic | ✅ Installed | 2.11.10 |
| pydantic-settings | ✅ Installed | 2.10.1 |
| requests | ✅ Installed | 2.33.1 |
| marker-pdf | ❌ **NOT INSTALLED** | — |

## 6. SYSTEM DEPS

| Dependency | Status |
|------------|--------|
| tesseract | ❌ **NOT INSTALLED** |
| poppler (pdftoppm/pdftotext) | ❌ **NOT INSTALLED** |
| libGL | ❌ **NOT INSTALLED** (only libglib2.0 present) |

## 7. PROJECT DIRECTORY

| Item | Value |
|------|-------|
| Path | /var/www/pdf-translator |
| Exists | ✅ Yes |
| Owner | root:root (0755) |
| Contents | AGENTS.md only |
| Git | ❌ Not initialized |
| venv | ❌ Not created |

## 8. CONFLICTS

| Check | Result |
|-------|--------|
| Port 8000 | ✅ FREE — available for dev server |
| Existing pdf-translator files | ✅ None — clean slate |
| book.itplane.ru nginx config | ❌ **Does not exist** — needs creation |
| pdf-translator systemd unit | ❌ **Does not exist** — needs creation |

## ACTION ITEMS BEFORE PHASE 0.1 CODE WORK

1. **Install missing system deps:** `tesseract-ocr`, `poppler-utils`, `libgl1-mesa-glx` (required by marker-pdf)
2. **Install marker-pdf:** `pip install marker-pdf` (heavy package, ~3.5GB RAM during install)
3. **Create nginx site** for `book.itplane.ru` → proxy to uvicorn on port 8000
4. **Create systemd unit** for uvicorn service
5. **Initialize git repo** and push to remote
6. **Create venv** and project directory structure
