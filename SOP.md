# 測試 SOP

## 快速開始

```bash
# 1. 啟動所有服務
docker compose up -d

# 2. 等待 backend 就緒 (約 10 秒)
curl -s http://localhost:8001/api/v1/health

# 3. 跑全部 E2E 測試
python3 backend/tests/live_e2e_booking_flow_test.py --email employee@eop-test.com --password TestPassword123!
python3 backend/tests/live_e2e_student_flow_test.py --email employee@eop-test.com --password TestPassword123!
python3 backend/tests/live_e2e_teacher_flow_test.py --email employee@eop-test.com --password TestPassword123!

# 4. 跑 unit + integration 測試 (不需要 backend 運行)
cd backend && pytest tests/unit/ tests/integration/ tests/e2e/ -v
```

---

## 測試層級總覽

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Unit Tests (pytest, mocked)                   │
│  不需服務運行，測試單一函數/模組                            │
│  └── tests/unit/test_security.py                        │
│  └── tests/unit/test_session_service.py                 │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Integration Tests (pytest, mocked)            │
│  測試 API 層行為（含 middleware），使用 mock               │
│  └── tests/integration/test_auth_api.py                 │
│  └── tests/integration/test_health_api.py               │
│  └── tests/integration/test_middleware.py                │
│  └── tests/integration/test_user_api.py                 │
├─────────────────────────────────────────────────────────┤
│  Layer 3: E2E Tests (pytest, mocked deps)               │
│  測試完整 auth/permission 流程                            │
│  └── tests/e2e/test_auth_flow.py                        │
│  └── tests/e2e/test_permission_flow.py                  │
├─────────────────────────────────────────────────────────┤
│  Layer 4: Live E2E Tests (httpx, 真實 DB)                │
│  ⚠️ 需要 docker compose up 且服務運行中                    │
│  └── tests/live_e2e_booking_flow_test.py    ← 核心流程    │
│  └── tests/live_e2e_student_flow_test.py    ← 學生管理    │
│  └── tests/live_e2e_teacher_flow_test.py    ← 教師管理    │
│  └── tests/live_booking_concurrency_test.py ← 並發安全    │
│  └── tests/live_booking_test.py             ← 預約細節    │
│  └── (其他 live_*.py 見下方清單)                          │
├─────────────────────────────────────────────────────────┤
│  Layer 5: External Tests (需外部憑證)                     │
│  └── tests/live_line_binding_test.py  (LINE OAuth)      │
│  └── tests/live_line_test.py          (LINE Messaging)  │
│  └── tests/live_s3_storage_test.py    (AWS S3)          │
└─────────────────────────────────────────────────────────┘
```

---

## 測試執行指引

### Layer 1-3: Unit / Integration / E2E (Mocked)

```bash
cd backend

# 全部跑
pytest tests/unit/ tests/integration/ tests/e2e/ -v

# 單獨跑某層
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v

# 單一檔案
pytest tests/unit/test_security.py -v
```

**前置條件**: 無（使用 mock，不需 Docker）
**預計時間**: < 30 秒
**何時跑**: 每次修改 backend 程式碼後

---

### Layer 4: Live E2E Tests (核心)

**前置條件**: `docker compose up -d` 且 backend 已就緒

#### E2E 預約完整流程 (最重要)

```bash
python3 backend/tests/live_e2e_booking_flow_test.py \
    --email employee@eop-test.com --password TestPassword123!
```

測試範圍 (21 步驟，含 Zoom):
1. 建立課程 / 學生 / 教師
2. 建立學生合約 / 教師合約 / 課程費率
3. 學生選課 / 教師偏好 / 教師時段
4. 建立預約 → 驗證 → 確認 → 重複預約拒絕 (409)
5. Zoom 會議建立 → 驗證 → 列表查詢（需有效 OAuth token）
6. 請假申請 → 驗證
7. 取消 → 刪除 → 確認已刪除
8. 清理所有測試資料

> **Zoom 測試說明**: 若 Zoom 帳號已建立但 OAuth token 過期，會議建立測試會標記為失敗但不影響其他測試。需到 Zoom 帳號管理頁面重新授權後再跑。

**何時跑**: 修改 bookings、contracts、slots 相關程式碼後

#### E2E 學生管理流程

```bash
python3 backend/tests/live_e2e_student_flow_test.py \
    --email employee@eop-test.com --password TestPassword123!
```

測試範圍 (13 步驟):
1. 建立學生 → 搜尋 → 詳情
2. 建立合約 → 選課 → 教師偏好 → 驗證堂數
3. 總覽 API → 篩選 → 詳情頁
4. 編輯 → 停用 → 篩選已停用

**何時跑**: 修改 students、student_contracts、student_courses 相關程式碼後

#### E2E 教師管理流程

```bash
python3 backend/tests/live_e2e_teacher_flow_test.py \
    --email employee@eop-test.com --password TestPassword123!
```

測試範圍 (14 步驟):
1. 建立教師 → 搜尋 → 詳情
2. 建立合約 → 課程費率明細 → 驗證
3. 建立時段 → 列表 → 編輯可用狀態
4. 總覽 API → 詳情頁
5. 編輯 → 停用

**何時跑**: 修改 teachers、teacher_contracts、teacher_slots 相關程式碼後

#### 預約並發安全性

```bash
python3 backend/tests/live_booking_concurrency_test.py \
    --email employee@eop-test.com --password TestPassword123!
```

測試範圍:
1. 建立預約 → 成功
2. 同時段重複預約 → 被拒絕 (409)
3. 刪除後重新預約 → 成功

**何時跑**: 修改預約建立邏輯或 DB 交易相關程式碼後

---

### Layer 4: Live Feature Tests (功能模組)

以下測試各自覆蓋特定功能模組：

| 測試檔案 | 測試範圍 | 執行指令 |
|---------|---------|---------|
| `live_auth_test.py` | 登入/登出/token refresh | `python3 tests/live_auth_test.py --email ... --password ...` |
| `live_booking_test.py` | 30 分鐘區塊/多預約/邊界 | `python3 tests/live_booking_test.py --email ... --password ...` |
| `live_courses_test.py` | 課程 CRUD | `python3 tests/live_courses_test.py --email ... --password ...` |
| `live_student_contracts_test.py` | 學生合約 CRUD | `python3 tests/live_student_contracts_test.py --email ... --password ...` |
| `live_teacher_contracts_test.py` | 教師合約 CRUD | `python3 tests/live_teacher_contracts_test.py --email ... --password ...` |
| `live_student_courses_test.py` | 學生選課 | `python3 tests/live_student_courses_test.py --email ... --password ...` |
| `live_substitute_test.py` | 代課流程 | `python3 tests/live_substitute_test.py --email ... --password ...` |
| `live_leave_emergency_test.py` | 緊急請假額度 | `python3 tests/live_leave_emergency_test.py --email ... --password ...` |
| `live_convert_to_formal_test.py` | 試上轉正流程 | `python3 tests/live_convert_to_formal_test.py --email ... --password ...` |
| `live_trial_bonus_test.py` | 試上獎金 | `python3 tests/live_trial_bonus_test.py --email ... --password ...` |
| `live_permission_test.py` | 頁面權限 | `python3 tests/live_permission_test.py --email ... --password ...` |
| `live_work_schedules_test.py` | 教師工作時段 | `python3 tests/live_work_schedules_test.py --email ... --password ...` |

---

### Layer 5: External Integration Tests

需要真實外部服務憑證，通常只在部署前或環境設定後執行。

| 測試 | 需要的憑證 |
|-----|----------|
| `live_line_binding_test.py` | `LINE_LOGIN_CHANNEL_ID`, `LINE_LOGIN_CHANNEL_SECRET` |
| `live_line_test.py` | `LINE_*_MESSAGING_TOKEN` + 真實 LINE User ID |
| `live_s3_storage_test.py` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET` |

```bash
# 確認 .env 有相關憑證後
python3 backend/tests/live_line_binding_test.py --email ... --password ...
python3 backend/tests/live_s3_storage_test.py --email ... --password ...
```

---

## 工具腳本

| 腳本 | 用途 |
|-----|------|
| `tests/live_seed_test_data.py` | 建立測試用假資料（教師、學生、課程、合約） |
| `scripts/db-backup.sh` | PostgreSQL 備份（daily cron 用） |

```bash
# Seed 測試資料
python3 backend/tests/live_seed_test_data.py --email admin@example.com --password ...

# 手動備份 DB
./scripts/db-backup.sh
```

---

## 測試帳號

| 角色 | Email | Password |
|------|-------|----------|
| Employee | `employee@eop-test.com` | `TestPassword123!` |
| Teacher | `teacher@eop-test.com` | `TestPassword123!` |
| Student | `student@eop-test.com` | `TestPassword123!` |

**注意**: Employee 角色可執行 CRUD，Student/Teacher 只有讀取權限。E2E 測試請使用 Employee 帳號。

---

## 部署前檢查清單

```
□ Layer 1-3 全過: pytest tests/unit/ tests/integration/ tests/e2e/ -v
□ E2E 預約流程:   live_e2e_booking_flow_test.py     (21/21, Zoom 需 OAuth)
□ E2E 學生管理:   live_e2e_student_flow_test.py      (13/13)
□ E2E 教師管理:   live_e2e_teacher_flow_test.py      (14/14)
□ 並發安全性:     live_booking_concurrency_test.py    (3/3)
□ DB 備份:        ./scripts/db-backup.sh 已設定 cron
□ 環境變數:       .env 已設定 REDIS_PASSWORD、DEBUG=false
```

---

## 已移除的測試

| 檔案 | 移除原因 |
|-----|---------|
| `test_auth.py` | 空檔案，無測試內容 |
| `test_rls_filtering.py` | RLS 已在 migration 020 完全移除 |
| `live_register_test.py` | 公開註冊已關閉，改為 invite-only 流程 |
