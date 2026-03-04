#!/bin/bash
# =============================================================
# 02-run-migrations.sh — 對 RDS 執行 database migration
# 需要先安裝 postgresql-client (psql, pg_isready)
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MIGRATIONS_DIR="${PROJECT_DIR}/supabase/migrations"
ENDPOINT_FILE="${SCRIPT_DIR}/.rds-endpoint"

DB_PORT="5432"
DB_NAME="postgres"
DB_USER="postgres"

echo "=== EOP RDS Migration Runner ==="

# ---- 1. 取得 RDS Endpoint ----
if [ -n "${RDS_ENDPOINT:-}" ]; then
    DB_HOST="${RDS_ENDPOINT}"
    echo "使用環境變數 RDS_ENDPOINT"
elif [ -n "${1:-}" ]; then
    DB_HOST="$1"
    echo "使用參數指定的 endpoint"
elif [ -f "${ENDPOINT_FILE}" ]; then
    DB_HOST=$(cat "${ENDPOINT_FILE}")
    echo "從 ${ENDPOINT_FILE} 讀取 endpoint"
else
    echo "❌ 找不到 RDS endpoint。請執行以下其中一項："
    echo "   1. 先執行 ./deploy/01-create-rds.sh"
    echo "   2. 設定環境變數: export RDS_ENDPOINT=<your-endpoint>"
    echo "   3. 作為參數傳入: ./deploy/02-run-migrations.sh <endpoint>"
    exit 1
fi

echo "Host: ${DB_HOST}:${DB_PORT}"
echo "Database: ${DB_NAME}"
echo "Migrations: ${MIGRATIONS_DIR}"

# ---- 2. 取得密碼 ----
if [ -n "${RDS_MASTER_PASSWORD:-}" ]; then
    export PGPASSWORD="${RDS_MASTER_PASSWORD}"
    echo "使用環境變數 RDS_MASTER_PASSWORD"
else
    read -s -p "請輸入 RDS 密碼: " PGPASSWORD
    echo ""
    export PGPASSWORD
fi

# ---- 3. 等待連線就緒 ----
echo ""
echo "等待資料庫連線就緒..."
RETRIES=30
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; do
    RETRIES=$((RETRIES - 1))
    if [ ${RETRIES} -le 0 ]; then
        echo "❌ 無法連線到資料庫，請檢查："
        echo "   - RDS 是否為 available 狀態"
        echo "   - Security Group 是否允許從此機器連線"
        echo "   - Endpoint 是否正確: ${DB_HOST}"
        exit 1
    fi
    echo "  資料庫尚未就緒，等待中...（剩餘重試: ${RETRIES}）"
    sleep 2
done
echo "資料庫連線就緒！"

# ---- 4. 建立 migration tracking table ----
echo ""
echo "建立 migration tracking table..."
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" <<'EOF'
CREATE TABLE IF NOT EXISTS _migrations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);
EOF

# ---- 5. 取得已執行的遷移列表 ----
EXECUTED_MIGRATIONS=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    -t -A -c "SELECT name FROM _migrations ORDER BY name;")

# ---- 6. 依序執行 migration ----
echo ""
echo "檢查待執行的 migration..."
PENDING_COUNT=0
SKIP_COUNT=0

for migration_file in $(ls -1 "${MIGRATIONS_DIR}"/*.sql 2>/dev/null | sort); do
    filename=$(basename "${migration_file}")

    if echo "${EXECUTED_MIGRATIONS}" | grep -q "^${filename}$"; then
        echo "  [SKIP] ${filename}（已執行）"
        SKIP_COUNT=$((SKIP_COUNT + 1))
    else
        echo "  [RUN]  ${filename}"

        if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
            -v ON_ERROR_STOP=1 -f "${migration_file}"; then
            # 記錄已執行
            psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c \
                "INSERT INTO _migrations (name) VALUES ('${filename}');"
            echo "  [OK]   ${filename} 執行成功"
            PENDING_COUNT=$((PENDING_COUNT + 1))
        else
            echo "  [FAIL] ${filename} 執行失敗！"
            exit 1
        fi
    fi
done

echo ""
if [ ${PENDING_COUNT} -eq 0 ]; then
    echo "沒有待執行的 migration。（已跳過 ${SKIP_COUNT} 個）"
else
    echo "成功執行 ${PENDING_COUNT} 個 migration。（跳過 ${SKIP_COUNT} 個）"
fi

echo "=== Migration 完成 ==="
echo ""
echo "下一步: ./deploy/03-setup-env.sh"
