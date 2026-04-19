import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from shared.config import settings
from shared.database import init_db

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from core.middleware import limiter  # noqa: E402


LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Translator</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { background: #fff; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); padding: 40px; max-width: 520px; width: 100%; text-align: center; }
        h1 { font-size: 24px; margin-bottom: 8px; color: #1a1a2e; }
        .subtitle { color: #666; margin-bottom: 24px; line-height: 1.5; font-size: 14px; }
        .widget-wrap { display: flex; justify-content: center; margin: 20px 0; }
        .status { margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; display: none; }
        .status.ok { background: #e8f5e9; color: #2e7d32; display: block; }
        .status.err { background: #ffebee; color: #c62828; display: block; }
        .status.info { background: #e3f2fd; color: #1565c0; display: block; }
        .quota { font-size: 13px; color: #888; margin-top: 8px; }
        .user-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding: 12px; background: #f8f9fa; border-radius: 8px; }
        .user-bar .name { font-weight: 600; color: #1a1a2e; }
        .user-bar .logout { background: none; border: 1px solid #ddd; border-radius: 6px; padding: 6px 14px; cursor: pointer; font-size: 13px; color: #666; }
        .user-bar .logout:hover { background: #fee; border-color: #e55; color: #c00; }
        #upload-area { display: none; }
        #upload-area.visible { display: block; }
        .drop-zone { border: 2px dashed #ccc; border-radius: 12px; padding: 40px 20px; cursor: pointer; transition: all 0.2s; background: #fafafa; }
        .drop-zone:hover, .drop-zone.dragover { border-color: #4a90d9; background: #f0f7ff; }
        .drop-zone p { color: #888; font-size: 14px; }
        .drop-zone .icon { font-size: 36px; margin-bottom: 8px; }
        #file-input { display: none; }
        .progress-wrap { margin-top: 16px; display: none; }
        .progress-wrap.visible { display: block; }
        .progress-bar { height: 8px; background: #eee; border-radius: 4px; overflow: hidden; margin-top: 8px; }
        .progress-bar .fill { height: 100%; background: #4a90d9; width: 0%; transition: width 0.3s; border-radius: 4px; }
        .progress-text { font-size: 13px; color: #666; margin-top: 4px; }
        .task-list { margin-top: 20px; text-align: left; }
        .task-item { padding: 10px 14px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px; font-size: 13px; display: flex; justify-content: space-between; align-items: center; }
        .task-item .filename { font-weight: 500; color: #1a1a2e; }
        .task-item .badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .badge.pending { background: #fff3e0; color: #e65100; }
        .badge.processing { background: #e3f2fd; color: #1565c0; }
        .badge.completed { background: #e8f5e9; color: #2e7d32; }
        .badge.failed { background: #ffebee; color: #c62828; }
        .task-item .download-btn { background: #4a90d9; color: #fff; border: none; border-radius: 4px; padding: 4px 10px; cursor: pointer; font-size: 12px; text-decoration: none; }
        .task-item .download-btn:hover { background: #357abd; }
    </style>
</head>
<body>
<div class="container">
    <h1>PDF Translator</h1>
    <p class="subtitle">Convert English PDFs to Russian Markdown + images</p>

    <div id="login-view">
        <div class="widget-wrap">
            <script async src="https://telegram.org/js/telegram-widget.js?22"
                data-telegram-login="pdf_translator_epub_bot"
                data-size="large"
                data-radius="8"
                data-onauth="onTelegramAuth(user)"
                data-request-access="write"></script>
        </div>
    </div>

    <div id="app-view" style="display:none">
        <div class="user-bar">
            <span class="name" id="user-name"></span>
            <button class="logout" onclick="doLogout()">Logout</button>
        </div>
        <div class="quota" id="quota-info"></div>

        <div id="upload-area">
            <div class="drop-zone" id="drop-zone" onclick="document.getElementById('file-input').click()">
                <div class="icon">📄</div>
                <p>Drop a PDF here or click to browse</p>
            </div>
            <input type="file" id="file-input" accept=".pdf" onchange="handleFile(this.files[0])">
        </div>

        <div class="progress-wrap" id="progress-wrap">
            <div class="progress-text" id="progress-text">Uploading...</div>
            <div class="progress-bar"><div class="fill" id="progress-fill"></div></div>
        </div>

        <div class="task-list" id="task-list"></div>
    </div>

    <div id="status" class="status"></div>
</div>

<script>
const API = '';
let currentToken = localStorage.getItem('token');

async function onTelegramAuth(user) {
    const statusEl = document.getElementById('status');
    try {
        const params = Object.entries(user)
            .filter(([_, v]) => v !== undefined && v !== '')
            .map(([k, v]) => k + '=' + encodeURIComponent(v))
            .join('&');
        const resp = await fetch(API + '/api/auth/telegram?' + params, { method: 'POST' });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Auth failed');
        currentToken = data.access_token;
        localStorage.setItem('token', currentToken);
        showApp(data.user);
    } catch (e) {
        statusEl.textContent = 'Auth error: ' + e.message;
        statusEl.className = 'status err';
    }
}

function showApp(user) {
    document.getElementById('login-view').style.display = 'none';
    document.getElementById('app-view').style.display = 'block';
    document.getElementById('upload-area').classList.add('visible');
    document.getElementById('user-name').textContent = user.username || user.first_name || 'User';
    document.getElementById('quota-info').textContent =
        'Quota: ' + (user.quota_used || 0).toLocaleString() + ' / ' + (user.quota_limit || 0).toLocaleString() + ' chars';
    document.getElementById('status').style.display = 'none';
    loadTasks();
}

function doLogout() {
    localStorage.removeItem('token');
    currentToken = null;
    document.getElementById('login-view').style.display = 'block';
    document.getElementById('app-view').style.display = 'none';
    document.getElementById('upload-area').classList.remove('visible');
    document.getElementById('progress-wrap').classList.remove('visible');
    document.getElementById('task-list').innerHTML = '';
    location.reload();
}

async function checkAuth() {
    if (!currentToken) return;
    try {
        const r = await fetch(API + '/api/auth/me', { headers: { 'Authorization': 'Bearer ' + currentToken } });
        if (r.ok) { showApp(await r.json()); return; }
    } catch (e) {}
    localStorage.removeItem('token');
    currentToken = null;
}

const dropZone = document.getElementById('drop-zone');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('dragover'); if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]); });

async function handleFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) { alert('Only PDF files accepted'); return; }
    const progressWrap = document.getElementById('progress-wrap');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    progressWrap.classList.add('visible');
    progressFill.style.width = '10%';
    progressText.textContent = 'Uploading ' + file.name + '...';

    const fd = new FormData();
    fd.append('file', file);
    try {
        const r = await fetch(API + '/api/upload', { method: 'POST', headers: { 'Authorization': 'Bearer ' + currentToken }, body: fd });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Upload failed');
        progressFill.style.width = '30%';
        progressText.textContent = 'Processing...';
        pollTask(data.task_id, file.name);
    } catch (e) {
        progressText.textContent = 'Upload error: ' + e.message;
        progressFill.style.width = '0%';
        progressFill.style.background = '#e55';
    }
}

async function pollTask(taskId, filename) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    for (let i = 0; i < 300; i++) {
        await new Promise(r => setTimeout(r, 3000));
        try {
            const r = await fetch(API + '/api/status/' + taskId, { headers: { 'Authorization': 'Bearer ' + currentToken } });
            const data = await r.json();
            progressFill.style.width = Math.max(30, data.progress) + '%';
            progressText.textContent = data.status + ' (' + Math.round(data.progress) + '%)';
            if (data.status === 'completed') {
                progressText.textContent = 'Done!';
                progressFill.style.background = '#4caf50';
                addTaskToUI({ id: taskId, filename, status: 'completed', download: true });
                setTimeout(() => { document.getElementById('progress-wrap').classList.remove('visible'); progressFill.style.background = '#4a90d9'; }, 3000);
                loadTasks();
                return;
            }
            if (data.status === 'failed') {
                progressText.textContent = 'Failed: ' + (data.error_msg || 'Unknown error');
                progressFill.style.background = '#e55';
                return;
            }
        } catch (e) {}
    }
    progressText.textContent = 'Timed out';
}

function addTaskToUI(task) {
    const list = document.getElementById('task-list');
    const badgeClass = task.status || 'pending';
    const badge = '<span class="badge ' + badgeClass + '">' + task.status + '</span>';
    const dl = task.download ? '<a class="download-btn" href="/api/download/' + task.id + '" download>Download</a>' : '';
    const el = document.createElement('div');
    el.className = 'task-item';
    el.innerHTML = '<span class="filename">' + (task.filename || task.original_filename || 'task') + '</span>' + badge + dl;
    list.prepend(el);
}

async function loadTasks() {
    try {
        const r = await fetch(API + '/api/auth/me', { headers: { 'Authorization': 'Bearer ' + currentToken } });
        if (!r.ok) return;
        const user = await r.json();
        document.getElementById('quota-info').textContent =
            'Quota: ' + (user.quota_used || 0).toLocaleString() + ' / ' + (user.quota_limit || 0).toLocaleString() + ' chars';
    } catch (e) {}
}

checkAuth();
</script>
</body>
</html>
"""


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


@app.api_route("/", methods=["GET", "HEAD"])
def index():
    return HTMLResponse(content=LOGIN_HTML)


from core.routes import router as api_router  # noqa: E402
from core.routes_auth import router as auth_router  # noqa: E402
from core.routes_admin import router as admin_router  # noqa: E402

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(admin_router)
