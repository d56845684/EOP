#!/bin/bash
# Daily PostgreSQL backup script
# 使用方式:
#   手動執行: ./scripts/db-backup.sh
#   設定 cron: 0 3 * * * /path/to/EOP/scripts/db-backup.sh
#
# 備份檔案存放在 ./backups/ 目錄，保留最近 7 天

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
CONTAINER_NAME="teaching-platform-db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="eop_backup_${DATE}.sql.gz"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting database backup..."

# 執行 pg_dump 並壓縮
docker exec "$CONTAINER_NAME" pg_dump -U postgres --no-owner --no-acl \
  | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

FILESIZE=$(ls -lh "${BACKUP_DIR}/${BACKUP_FILE}" | awk '{print $5}')
echo "[$(date)] Backup saved: ${BACKUP_FILE} (${FILESIZE})"

# 清理超過 KEEP_DAYS 天的舊備份
DELETED=$(find "$BACKUP_DIR" -name "eop_backup_*.sql.gz" -mtime +${KEEP_DAYS} -print -delete | wc -l | tr -d ' ')
if [ "$DELETED" -gt 0 ]; then
  echo "[$(date)] Cleaned up ${DELETED} old backup(s)"
fi

echo "[$(date)] Backup complete. Total backups: $(ls "$BACKUP_DIR"/eop_backup_*.sql.gz 2>/dev/null | wc -l | tr -d ' ')"
