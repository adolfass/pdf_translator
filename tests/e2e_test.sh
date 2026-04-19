#!/usr/bin/env bash
# E2E test script for PDF Translator auth flow
# Simulates: Telegram login → JWT → upload → poll → download
set -euo pipefail

BASE_URL="http://127.0.0.1:8000"
BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN /var/www/pdf-translator/.env | cut -d= -f2)

PASS=0
FAIL=0

result() {
    if [ "$2" = "ok" ]; then
        echo "✅ $1"
        PASS=$((PASS + 1))
    else
        echo "❌ $1 — $2"
        FAIL=$((FAIL + 1))
    fi
}

echo "=========================================="
echo "  PDF Translator E2E Test Suite"
echo "=========================================="

# --- Step 1: Health check ---
echo ""
echo "1. Health check..."
HTTP=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/health")
[ "$HTTP" = "200" ] && result "Health endpoint" "ok" || result "Health endpoint" "HTTP $HTTP"

# --- Step 2: Root page returns HTML with Telegram widget ---
echo "2. Root page..."
HTML=$(curl -s "$BASE_URL/")
echo "$HTML" | grep -q "telegram-widget.js" && result "Root page has Telegram widget" "ok" || result "Root page has Telegram widget" "missing"

# --- Step 3: Auth without token returns 401 ---
echo "3. Auth protection..."
HTTP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/api/upload")
[ "$HTTP" = "401" ] && result "Upload requires auth (401)" "ok" || result "Upload requires auth" "HTTP $HTTP"

# --- Step 4: Mock Telegram login ---
echo "4. Telegram login (mock)..."

# Use Python to compute valid HMAC-SHA256 hash and make the request
AUTH_RESULT=$(python3 << 'PYEOF'
import hashlib, hmac, time, urllib.parse, requests, os, json

bot_token = os.environ.get("BOT_TOKEN", "")
base_url = "http://127.0.0.1:8000"

data = {
    "id": "42",
    "username": "e2e_test_user",
    "first_name": "E2E Test",
    "auth_date": str(int(time.time())),
}

# Build sorted data check string
sorted_params = sorted(f"{k}={v}" for k, v in data.items())
data_check = "\n".join(sorted_params)

# Compute HMAC-SHA256
secret = hashlib.sha256(bot_token.encode()).digest()
data["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

# Make request
params = urllib.parse.urlencode(data)
resp = requests.post(f"{base_url}/api/auth/telegram?{params}")
print(json.dumps(resp.json()))
PYEOF
)

TOKEN=$(echo "$AUTH_RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)

if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
    result "Telegram login returns JWT" "ok"
else
    result "Telegram login returns JWT" "empty token: $AUTH_RESULT"
    echo "   Skipping remaining tests (no auth token)"
    echo ""
    echo "=========================================="
    echo "  Results: $PASS passed, $FAIL failed"
    echo "=========================================="
    exit 1
fi

# --- Step 5: GET /me with token ---
echo "5. Get current user..."
ME_RESP=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/auth/me")
ME_ID=$(echo "$ME_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true)
[ -n "$ME_ID" ] && result "GET /me returns user" "ok" || result "GET /me returns user" "$ME_RESP"

# --- Step 6: Create test PDF ---
echo "6. Create test PDF..."
TEST_DIR=$(mktemp -d)
python3 -c "
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
c = canvas.Canvas('$TEST_DIR/test.pdf', pagesize=letter)
c.drawString(100, 750, 'Hello World - This is a test document for PDF Translator E2E testing.')
c.drawString(100, 730, 'The quick brown fox jumps over the lazy dog.')
c.save()
" 2>/dev/null && result "Test PDF created" "ok" || {
    # Fallback: create minimal PDF
    printf '%%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n163\n%%%%EOF\n' > "$TEST_DIR/test.pdf"
    result "Test PDF created (minimal)" "ok"
}

# --- Step 7: Upload PDF ---
echo "7. Upload PDF..."
UPLOAD_RESP=$(curl -s -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$TEST_DIR/test.pdf;filename=test.pdf" \
    "$BASE_URL/api/upload")
TASK_ID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null || true)

if [ -n "$TASK_ID" ]; then
    result "Upload returns task_id" "ok"
else
    result "Upload returns task_id" "$UPLOAD_RESP"
fi

# --- Step 8: Poll task status ---
echo "8. Poll task status (timeout=5min, marker-pdf may download models on first run)..."
STATUS="pending"
if [ -n "$TASK_ID" ]; then
    for i in $(seq 1 100); do
        STATUS_RESP=$(curl -s -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/status/$TASK_ID")
        STATUS=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "unknown")
        PROGRESS=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('progress',0))" 2>/dev/null || echo "0")
        echo "   Poll $i: status=$STATUS progress=$PROGRESS"
        if [ "$STATUS" = "completed" ]; then
            result "Task completed" "ok"
            break
        elif [ "$STATUS" = "failed" ]; then
            ERROR=$(echo "$STATUS_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error_msg',''))" 2>/dev/null || true)
            result "Task completed" "failed: $ERROR"
            break
        fi
        sleep 3
    done
    if [ "$STATUS" != "completed" ] && [ "$STATUS" != "failed" ]; then
        result "Task completed" "still processing (marker-pdf downloading models on first run)"
        STATUS="processing"
    fi
else
    result "Task completed" "skipped (no task_id)"
fi

# --- Step 9: Download result ---
echo "9. Download result..."
if [ -n "$TASK_ID" ] && [ "$STATUS" = "completed" ]; then
    HTTP=$(curl -s -o "$TEST_DIR/result.zip" -w "%{http_code}" \
        -H "Authorization: Bearer $TOKEN" \
        "$BASE_URL/api/download/$TASK_ID")
    [ "$HTTP" = "200" ] && [ -f "$TEST_DIR/result.zip" ] && result "Download ZIP" "ok" || result "Download ZIP" "HTTP $HTTP"
else
    result "Download ZIP" "skipped (task status=$STATUS)"
fi

# --- Step 10: Verify ZIP contents ---
echo "10. Verify ZIP..."
if [ -f "$TEST_DIR/result.zip" ]; then
    CONTENTS=$(unzip -l "$TEST_DIR/result.zip" 2>/dev/null | grep -c "\.md" || echo "0")
    [ "$CONTENTS" -gt 0 ] && result "ZIP contains .md file" "ok" || result "ZIP contains .md file" "no .md files found"
else
    result "ZIP contains .md file" "skipped"
fi

# --- Step 11: Admin access control ---
echo "11. Admin access control..."
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$BASE_URL/api/admin/stats")
[ "$HTTP" = "403" ] && result "Admin endpoint rejects non-admin (403)" "ok" || result "Admin endpoint rejects non-admin" "HTTP $HTTP"

# --- Cleanup ---
rm -rf "$TEST_DIR"

echo ""
echo "=========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "=========================================="

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
