#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# PDF Translator — Idempotent Setup Script
# Usage: sudo bash deploy/setup.sh
# ============================================================

PROJECT_DIR="/var/www/pdf-translator"
VENV_DIR="${PROJECT_DIR}/venv"
SERVICE_NAME="pdf-translator"
NGINX_CONF="deploy/nginx-book.itplane.ru.conf"
SYSTEMD_UNIT="deploy/pdf-translator.service"

echo "🔧 PDF Translator Setup — $(date)"

# --- System deps ---
echo "📦 Checking system dependencies..."
for pkg in tesseract-ocr poppler-utils libgl1-mesa-glx; do
    if dpkg -s "$pkg" 2>/dev/null | grep -q "Status: install ok installed"; then
        echo "  ✅ $pkg already installed"
    else
        echo "  ⬇️  Installing $pkg..."
        apt-get update -qq && apt-get install -y -qq "$pkg"
    fi
done

# --- Python venv ---
if [ -d "$VENV_DIR" ]; then
    echo "✅ Virtual environment exists at $VENV_DIR"
else
    echo "🐍 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# --- Pip deps ---
echo "📦 Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r "${PROJECT_DIR}/requirements.txt" -q

# --- Directories ---
echo "📁 Ensuring directories exist..."
mkdir -p "${PROJECT_DIR}"/{data,results,tmp,logs}

# --- Nginx ---
if [ -f "$NGINX_CONF" ]; then
    NGINX_SITES="/etc/nginx/sites-available/book.itplane.ru.conf"
    NGINX_LINK="/etc/nginx/sites-enabled/book.itplane.ru.conf"

    cp -f "$NGINX_CONF" "$NGINX_SITES"

    if [ ! -L "$NGINX_LINK" ]; then
        ln -sf "$NGINX_SITES" "$NGINX_LINK"
        echo "✅ Nginx site linked"
    else
        echo "✅ Nginx site already linked"
    fi

    nginx -t && systemctl reload nginx
    echo "✅ Nginx reloaded"
else
    echo "⚠️  Nginx config not found at $NGINX_CONF — skipping"
fi

# --- Systemd ---
if [ -f "$SYSTEMD_UNIT" ]; then
    cp -f "$SYSTEMD_UNIT" "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    systemctl restart "$SERVICE_NAME"
    echo "✅ Systemd service deployed and restarted"
else
    echo "⚠️  Systemd unit not found at $SYSTEMD_UNIT — skipping"
fi

# --- Healthcheck ---
sleep 2
if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Healthcheck passed"
else
    echo "⚠️  Healthcheck failed — check logs: journalctl -u $SERVICE_NAME -n 50"
fi

echo "✅ Setup complete — $(date)"
