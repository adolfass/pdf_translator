#!/usr/bin/env bash
# Cleanup completed tasks and files older than 7 days
# Install: sudo cp deploy/cleanup.sh /usr/local/bin/pdf-translator-cleanup.sh
# Cron: 0 3 * * * /usr/local/bin/pdf-translator-cleanup.sh >> /var/www/pdf-translator/logs/cleanup.log 2>&1

set -euo pipefail

PROJECT_DIR="/var/www/pdf-translator"
DB_PATH="${PROJECT_DIR}/data/app.db"
RESULTS_DIR="${PROJECT_DIR}/results"
TMP_DIR="${PROJECT_DIR}/tmp"
DAYS=7

echo "[$(date)] Starting cleanup of tasks/files older than ${DAYS} days..."

# Clean old result directories
if [ -d "$RESULTS_DIR" ]; then
    find "$RESULTS_DIR" -maxdepth 1 -mindepth 1 -type d -mtime +${DAYS} -exec rm -rf {} + 2>/dev/null || true
    echo "[$(date)] Cleaned old result directories"
fi

# Clean old tmp directories
if [ -d "$TMP_DIR" ]; then
    find "$TMP_DIR" -maxdepth 1 -mindepth 1 -type d -mtime +${DAYS} -exec rm -rf {} + 2>/dev/null || true
    echo "[$(date)] Cleaned old tmp directories"
fi

# Clean old task records from database
if [ -f "$DB_PATH" ]; then
    CUTOFF=$(date -u -d "${DAYS} days ago" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u +"%Y-%m-%d %H:%M:%S")
    sqlite3 "$DB_PATH" "DELETE FROM tasks WHERE status IN ('completed', 'failed') AND completed_at < '${CUTOFF}';" 2>/dev/null || true
    echo "[$(date]] Cleaned old task records from database"
fi

echo "[$(date)] Cleanup complete"
