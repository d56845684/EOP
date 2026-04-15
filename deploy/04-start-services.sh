#!/bin/bash
# =============================================================
# 04-start-services.sh — 啟動 production 服務
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_PROD="${PROJECT_DIR}/.env.prod"
COMPOSE_PROD="${PROJECT_DIR}/docker-compose.prod.yml"

echo "=== EOP Production 服務啟動 ==="

# ---- 1. 檢查必要檔案 ----
if [ ! -f "${ENV_PROD}" ]; then
    echo "❌ 找不到 .env.prod，請先執行 ./deploy/03-setup-env.sh"
    exit 1
fi

if [ ! -f "${COMPOSE_PROD}" ]; then
    echo "❌ 找不到 docker-compose.prod.yml，請先執行 ./deploy/03-setup-env.sh"
    exit 1
fi

echo "環境檔: ${ENV_PROD}"
echo "Compose: ${COMPOSE_PROD}"

# ---- 2. Build 並啟動服務 ----
echo ""
echo "啟動服務中..."
cd "${PROJECT_DIR}"
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d

# ---- 3. 等待 backend 啟動 ----
echo ""
echo "等待 backend 啟動..."
RETRIES=30
while [ ${RETRIES} -gt 0 ]; do
    if docker logs teaching-platform-backend 2>&1 | grep -q "Database connected"; then
        echo "Backend 已就緒（Database connected）"
        break
    fi
    RETRIES=$((RETRIES - 1))
    if [ ${RETRIES} -le 0 ]; then
        echo "⚠️  等待逾時。請手動檢查 backend log："
        echo "   docker logs teaching-platform-backend"
        break
    fi
    sleep 2
done

# ---- 4. 顯示服務狀態 ----
echo ""
echo "=== 服務狀態 ==="
docker compose -f docker-compose.prod.yml ps

echo ""
echo "=== 完成 ==="
echo "Frontend: http://localhost:${FRONTEND_PORT:-4173}"
echo "Backend API: http://localhost:${BACKEND_PORT:-8001}"
echo "Backend Swagger: http://localhost:${BACKEND_PORT:-8001}/docs （production 預設關閉）"
echo ""
echo "查看 log:"
echo "  docker compose -f docker-compose.prod.yml logs -f backend"
