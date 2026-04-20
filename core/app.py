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
        :root {
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #263348;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --neon-purple: #a855f7;
            --neon-pink: #ec4899;
            --neon-blue: #3b82f6;
            --neon-cyan: #06b6d4;
            --gradient-primary: linear-gradient(135deg, #a855f7, #ec4899, #3b82f6, #06b6d4);
            --gradient-bg: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
            --glow-purple: 0 0 20px rgba(168, 85, 247, 0.4);
            --glow-cyan: 0 0 20px rgba(6, 182, 212, 0.4);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--gradient-bg);
            background-size: 400% 400%;
            animation: gradient-shift 15s ease infinite;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-primary);
        }

        @keyframes gradient-shift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        @keyframes neon-pulse {
            0%, 100% { box-shadow: 0 0 5px rgba(168, 85, 247, 0.3), 0 0 10px rgba(168, 85, 247, 0.2); }
            50% { box-shadow: 0 0 15px rgba(168, 85, 247, 0.6), 0 0 30px rgba(168, 85, 247, 0.3), 0 0 45px rgba(168, 85, 247, 0.1); }
        }

        @keyframes border-glow {
            0%, 100% { border-color: var(--neon-purple); box-shadow: var(--glow-purple); }
            33% { border-color: var(--neon-pink); box-shadow: 0 0 20px rgba(236, 72, 153, 0.4); }
            66% { border-color: var(--neon-cyan); box-shadow: var(--glow-cyan); }
        }

        .container {
            background: var(--bg-card);
            border: 1px solid rgba(168, 85, 247, 0.2);
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4), var(--glow-purple);
            padding: 40px;
            max-width: 520px;
            width: 100%;
            text-align: center;
            animation: neon-pulse 4s ease-in-out infinite;
        }

        h1 {
            font-size: 28px;
            margin-bottom: 8px;
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 700;
        }

        .subtitle { color: var(--text-secondary); margin-bottom: 24px; line-height: 1.5; font-size: 14px; }

        .widget-wrap { display: flex; justify-content: center; margin: 20px 0; }

        .status { margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; display: none; }
        .status.ok { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); display: block; }
        .status.err { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); display: block; }
        .status.info { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); display: block; }

        .quota { font-size: 13px; color: var(--text-secondary); margin-top: 8px; }

        .user-bar {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 20px; padding: 12px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(168, 85, 247, 0.2);
            border-radius: 8px;
        }
        .user-bar .name { font-weight: 600; color: var(--text-primary); }
        .user-bar .logout {
            background: transparent; border: 1px solid rgba(239, 68, 68, 0.4);
            border-radius: 6px; padding: 6px 14px; cursor: pointer;
            font-size: 13px; color: #f87171; transition: all 0.2s;
        }
        .user-bar .logout:hover {
            background: rgba(239, 68, 68, 0.15); border-color: #f87171;
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.3);
        }

        #upload-area { display: none; }
        #upload-area.visible { display: block; }

        .drop-zone {
            border: 2px dashed var(--neon-purple);
            border-radius: 12px; padding: 40px 20px; cursor: pointer;
            transition: all 0.3s;
            background: rgba(168, 85, 247, 0.05);
            animation: border-glow 6s ease-in-out infinite;
        }
        .drop-zone:hover, .drop-zone.dragover {
            border-color: var(--neon-cyan);
            background: rgba(6, 182, 212, 0.1);
            box-shadow: var(--glow-cyan);
        }
        .drop-zone p { color: var(--text-secondary); font-size: 14px; }
        .drop-zone .icon { font-size: 36px; margin-bottom: 8px; }

        #file-input { display: none; }

        .progress-wrap { margin-top: 16px; display: none; }
        .progress-wrap.visible { display: block; }
        .progress-bar {
            height: 8px; background: rgba(15, 23, 42, 0.8);
            border-radius: 4px; overflow: hidden; margin-top: 8px;
            border: 1px solid rgba(168, 85, 247, 0.2);
        }
        .progress-bar .fill {
            height: 100%;
            background: var(--gradient-primary);
            background-size: 200% 200%;
            animation: gradient-shift 3s ease infinite;
            width: 0%; transition: width 0.3s; border-radius: 4px;
            box-shadow: 0 0 10px rgba(168, 85, 247, 0.5);
        }
        .progress-text { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

        .task-list { margin-top: 20px; text-align: left; }
        .task-item {
            padding: 10px 14px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(168, 85, 247, 0.15);
            border-radius: 8px; margin-bottom: 8px;
            font-size: 13px; display: flex; justify-content: space-between; align-items: center;
            transition: all 0.2s;
        }
        .task-item:hover {
            background: var(--bg-card-hover);
            border-color: rgba(168, 85, 247, 0.3);
        }
        .task-item .filename { font-weight: 500; color: var(--text-primary); }

        .task-item .badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .badge.pending { background: rgba(251, 146, 60, 0.15); color: #fb923c; border: 1px solid rgba(251, 146, 60, 0.3); }
        .badge.processing { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
        .badge.completed { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
        .badge.failed { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

        .task-item .download-btn {
            background: var(--gradient-primary);
            color: #fff; border: none; border-radius: 4px;
            padding: 4px 10px; cursor: pointer; font-size: 12px;
            text-decoration: none; transition: all 0.2s;
        }
        .task-item .download-btn:hover {
            box-shadow: 0 0 12px rgba(168, 85, 247, 0.5);
            transform: scale(1.05);
        }

        .page-range-wrap { margin: 16px 0 8px; text-align: left; }
        .page-range-wrap label { font-size: 13px; color: var(--text-secondary); display: block; margin-bottom: 6px; }
        .page-range-input {
            width: 100%; padding: 10px 14px;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(168, 85, 247, 0.3);
            border-radius: 8px; color: var(--text-primary);
            font-size: 14px; outline: none; transition: all 0.2s;
            font-family: 'SF Mono', 'Fira Code', monospace;
        }
        .page-range-input:focus {
            border-color: var(--neon-purple);
            box-shadow: 0 0 10px rgba(168, 85, 247, 0.3);
        }
        .page-range-input::placeholder { color: var(--text-secondary); opacity: 0.5; }
        .page-range-wrap small { font-size: 11px; color: var(--text-secondary); margin-top: 4px; display: block; }

        .file-preview { display: none; margin: 16px 0; padding: 14px; background: rgba(15,23,42,0.6); border: 1px solid rgba(168,85,247,0.2); border-radius: 8px; text-align: left; }
        .file-preview.visible { display: block; }
        .file-preview .name { font-weight: 600; color: var(--text-primary); font-size: 14px; }
        .file-preview .actions { display: flex; gap: 8px; margin-top: 12px; }
        .btn-start {
            flex: 1; padding: 10px; border: none; border-radius: 6px; cursor: pointer;
            font-size: 14px; font-weight: 600; color: #fff;
            background: var(--gradient-primary); transition: all 0.2s;
        }
        .btn-start:hover { box-shadow: 0 0 15px rgba(168,85,247,0.5); transform: scale(1.02); }
        .btn-start:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }
        .btn-cancel {
            padding: 10px 18px; border: 1px solid rgba(239,68,68,0.4); border-radius: 6px;
            cursor: pointer; font-size: 14px; color: #f87171; background: transparent; transition: all 0.2s;
        }
        .btn-cancel:hover { background: rgba(239,68,68,0.15); border-color: #f87171; }

        .yandex-btn {
            display: inline-block; padding: 14px 32px; border-radius: 8px;
            background: linear-gradient(135deg, #fc3f1d, #ffcc00);
            color: #000; font-weight: 700; font-size: 16px;
            text-decoration: none; transition: all 0.2s;
            box-shadow: 0 0 15px rgba(252, 63, 29, 0.3);
        }
        .yandex-btn:hover {
            box-shadow: 0 0 25px rgba(252, 63, 29, 0.6);
            transform: scale(1.03);
        }
    </style>
</head>
<body>
<div class="container">
    <h1>PDF Translator</h1>
    <p class="subtitle">Convert English PDFs to Russian Markdown + images</p>

    <div id="login-view">
        <div class="widget-wrap">
            <a href="/api/auth/yandex/login" class="yandex-btn">Войти через Яндекс</a>
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
            <input type="file" id="file-input" accept=".pdf" onchange="onFileSelected(this.files[0])" style="display:none">
            <div class="file-preview" id="file-preview">
                <div class="name" id="file-name"></div>
                <div class="page-range-wrap">
                    <label for="page-range">Pages to process (optional):</label>
                    <input type="text" id="page-range" class="page-range-input" placeholder="e.g., 1-10, 15, 20-25">
                    <small>Leave empty to process all pages</small>
                </div>
                <div class="actions">
                    <button class="btn-start" id="btn-start" onclick="startProcessing()">▶️ Start</button>
                    <button class="btn-cancel" onclick="cancelFile()">✕ Cancel</button>
                </div>
            </div>
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
    // Check if returning from Yandex OAuth with token in URL
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');
    const urlUsername = params.get('username');
    if (urlToken) {
        currentToken = urlToken;
        localStorage.setItem('token', currentToken);
        window.history.replaceState({}, '', window.location.pathname);
        showApp({ username: urlUsername || 'User' });
        return;
    }
    if (!currentToken) return;
    try {
        const r = await fetch(API + '/api/auth/me', { headers: { 'Authorization': 'Bearer ' + currentToken } });
        if (r.ok) { showApp(await r.json()); return; }
    } catch (e) {}
    localStorage.removeItem('token');
    currentToken = null;
}

let selectedFile = null;

const dropZone = document.getElementById('drop-zone');
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('dragover'); if (e.dataTransfer.files[0]) onFileSelected(e.dataTransfer.files[0]); });

function onFileSelected(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) { alert('Only PDF files accepted'); return; }
    selectedFile = file;
    document.getElementById('file-name').textContent = '📎 ' + file.name;
    document.getElementById('file-preview').classList.add('visible');
    document.getElementById('drop-zone').style.display = 'none';
}

function cancelFile() {
    selectedFile = null;
    document.getElementById('file-input').value = '';
    document.getElementById('file-preview').classList.remove('visible');
    document.getElementById('drop-zone').style.display = 'block';
}

async function startProcessing() {
    if (!selectedFile) return;
    const file = selectedFile;
    const progressWrap = document.getElementById('progress-wrap');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const pageRange = document.getElementById('page-range').value.trim();
    const btnStart = document.getElementById('btn-start');
    btnStart.disabled = true;
    btnStart.textContent = '⏳ Uploading...';
    progressWrap.classList.add('visible');
    progressFill.style.width = '10%';
    progressText.textContent = 'Uploading ' + file.name + (pageRange ? ' (pages: ' + pageRange + ')' : '') + '...';

    const fd = new FormData();
    fd.append('file', file);
    if (pageRange) fd.append('page_range', pageRange);
    try {
        const r = await fetch(API + '/api/upload', { method: 'POST', headers: { 'Authorization': 'Bearer ' + currentToken }, body: fd });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Upload failed');
        progressFill.style.width = '30%';
        progressText.textContent = 'Processing' + (pageRange ? ' pages ' + pageRange : '...');
        pollTask(data.task_id, file.name, pageRange);
        cancelFile();
    } catch (e) {
        progressText.textContent = 'Upload error: ' + e.message;
        progressFill.style.width = '0%';
        progressFill.style.background = '#e55';
        btnStart.disabled = false;
        btnStart.textContent = '▶️ Start';
    }
}
}

async function pollTask(taskId, filename, pageRange) {
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    for (let i = 0; i < 300; i++) {
        await new Promise(r => setTimeout(r, 3000));
        try {
            const r = await fetch(API + '/api/status/' + taskId, { headers: { 'Authorization': 'Bearer ' + currentToken } });
            const data = await r.json();
            progressFill.style.width = Math.max(30, data.progress) + '%';
            const pages = data.page_range ? ' pages ' + data.page_range : '';
            progressText.textContent = data.status + pages + ' (' + Math.round(data.progress) + '%)';
            if (data.status === 'completed') {
                progressText.textContent = 'Done!';
                progressFill.style.background = '#4caf50';
                addTaskToUI({ id: taskId, filename, status: 'completed', download: true, page_range: data.page_range });
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
    const pages = task.page_range ? '<span style="color:#94a3b8;font-size:11px;margin-right:8px">p.' + task.page_range + '</span>' : '';
    const dl = task.download ? '<button class="download-btn" data-task-id="' + task.id + '" onclick="downloadFile(this.dataset.taskId, this)">Download</button>' : '';
    const el = document.createElement('div');
    el.className = 'task-item';
    el.innerHTML = '<span class="filename">' + (task.filename || task.original_filename || 'task') + '</span>' + pages + badge + dl;
    list.prepend(el);
}

async function downloadFile(taskId, btn) {
    const orig = btn.textContent;
    btn.textContent = '...';
    btn.disabled = true;
    try {
        const response = await fetch(API + '/api/download/' + taskId, {
            headers: { 'Authorization': 'Bearer ' + currentToken }
        });
        if (!response.ok) throw new Error('Download failed (' + response.status + ')');
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'book_' + taskId.slice(0, 8) + '.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        btn.textContent = 'Done!';
        setTimeout(() => { btn.textContent = orig; btn.disabled = false; }, 2000);
    } catch (e) {
        btn.textContent = 'Error';
        btn.disabled = false;
        setTimeout(() => { btn.textContent = orig; }, 2000);
    }
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
