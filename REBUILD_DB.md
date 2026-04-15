# 將資料庫重建為最新狀態

1. 停止所有服務
2. docker volume rm db-config
3. rm -rf volumes/db/data
4. docker compose up -d
