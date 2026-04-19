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
    <title>PDF Translator — English to Russian</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .container { background: #fff; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); padding: 40px; max-width: 420px; width: 100%; text-align: center; }
        h1 { font-size: 24px; margin-bottom: 8px; color: #1a1a2e; }
        p { color: #666; margin-bottom: 24px; line-height: 1.5; }
        .widget-wrap { display: flex; justify-content: center; margin: 20px 0; }
        .status { margin-top: 16px; padding: 12px; border-radius: 8px; font-size: 14px; display: none; }
        .status.ok { background: #e8f5e9; color: #2e7d32; display: block; }
        .status.err { background: #ffebee; color: #c62828; display: block; }
        .quota { font-size: 13px; color: #888; margin-top: 12px; }
    </style>
</head>
<body>
<div class="container">
    <h1>📄 PDF Translator</h1>
    <p>Convert English technical PDFs to Russian Markdown. Sign in with Telegram to start.</p>
    <div class="widget-wrap">
        <script async src="https://telegram.org/js/telegram-widget.js?22"
            data-telegram-login="pdf_translator_epub_bot"
            data-size="large"
            data-radius="8"
            data-onauth="onTelegramAuth(user)"
            data-request-access="write"></script>
    </div>
    <div id="status" class="status"></div>
    <div id="quota" class="quota" style="display:none"></div>
</div>
<script>
async function onTelegramAuth(user) {
    const statusEl = document.getElementById('status');
    const quotaEl = document.getElementById('quota');
    try {
        const params = Object.entries(user)
            .filter(([_, v]) => v !== undefined && v !== '')
            .map(([k, v]) => k + '=' + encodeURIComponent(v))
            .join('&');
        const resp = await fetch('/api/auth/telegram?' + params, { method: 'POST' });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Auth failed');
        localStorage.setItem('token', data.access_token);
        statusEl.textContent = 'Signed in as ' + (data.user.username || data.user.first_name);
        statusEl.className = 'status ok';
        quotaEl.textContent = 'Quota: ' + data.user.quota_used.toLocaleString() + ' / ' + data.user.quota_limit.toLocaleString() + ' chars';
        quotaEl.style.display = 'block';
        showApp(data.user);
    } catch (e) {
        statusEl.textContent = 'Auth error: ' + e.message;
        statusEl.className = 'status err';
    }
}
function showApp(user) {
    document.querySelector('.widget-wrap').innerHTML = '<p>Logged in as <b>' + (user.username || user.first_name) + '</b></p>';
}
(function() {
    const token = localStorage.getItem('token');
    if (token) {
        fetch('/api/auth/me', { headers: { 'Authorization': 'Bearer ' + token } })
            .then(r => { if (r.ok) return r.json(); throw new Error('expired'); })
            .then(data => { if (data && data.id) showApp(data); })
            .catch(() => localStorage.removeItem('token'));
    }
})();
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
