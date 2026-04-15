# 測試教學

## 目錄結構

```
tests/
├── e2e/                              # E2E 流程測試（打真實 API，完整業務流程）
│   ├── live_e2e_booking_flow_test.py       # 預約完整流程 (34 cases)
│   ├── live_e2e_student_flow_test.py       # 學生管理 (16 cases)
│   ├── live_e2e_teacher_flow_test.py       # 教師管理 + 頭像上傳 (21 cases)
│   ├── live_e2e_overtime_test.py           # 正職教師加班費計算
│   ├── live_e2e_trial_to_formal_test.py    # 試上轉正 + 獎金 (13 cases)
│   ├── live_e2e_leave_flow_test.py         # 請假流程 (10 cases)
│   ├── live_e2e_contracts_test.py          # 合約 CRUD + PDF + S3 + 安全 (35 cases)
│   └── live_e2e_courses_test.py            # 課程 + 選課 (15 cases)
│
├── unit/                             # 單元測試（mock-based，不需要真實服務）
│   ├── test_preference_service.py          # 偏好 service (9 cases)
│   ├── test_security.py                    # 安全模組
│   └── test_session_service.py             # Session 服務
│
├── live_auth_test.py                 # 多角色認證 (30 cases)
├── live_permission_test.py           # 權限邊界 (61 cases)
├── live_booking_test.py              # 預約邊界條件 (30 cases)
├── live_booking_concurrency_test.py  # 併發安全 (12 cases)
├── live_substitute_test.py           # 代課流程 (18 cases)
├── live_work_schedules_test.py       # 排班 + 加班 (37 cases)
├── live_line_binding_test.py         # LINE 綁定
└── live_line_test.py                 # LINE 訊息
```

## 前置準備

### 1. 啟動服務

```bash
# 從專案根目錄
docker compose up -d
```

確認 backend 正常運行：`http://localhost:8001/docs`

### 2. 帳號

| 用途 | Email | 密碼來源 |
|------|-------|---------|
| Super Admin | `eopAdmin@example.com` | `.env` 的 `SUPER_ADMIN_PASSWORD` |
| Employee | `employee@eop-test.com` | `TestPassword123!` |
| Teacher | `teacher@eop-test.com` | `TestPassword123!` |
| Student | `student@eop-test.com` | `TestPassword123!` |

大部分測試使用 Super Admin 帳號。

### 3. 工作目錄

所有指令都在 `backend/` 目錄下執行：

```bash
cd backend
```

---

## 單元測試（不需要真實服務）

在 Docker 容器內執行：

```bash
# 全部單元測試
docker compose exec backend python3 -m pytest tests/unit/ -v --noconftest --import-mode=importlib

# 單一檔案
docker compose exec backend python3 -m pytest tests/unit/test_preference_service.py -v --noconftest --import-mode=importlib
```

> 注意：需加 `--noconftest --import-mode=importlib` 避免 conftest 載入問題。

---

## E2E 流程測試

E2E 測試打真實 API，需要服務已啟動。在 host 執行（不是 Docker 內）：

### 跑全部 E2E

```bash
# 預約流程
python3 tests/e2e/live_e2e_booking_flow_test.py --email eopAdmin@example.com --password <密碼>

# 學生管理
python3 tests/e2e/live_e2e_student_flow_test.py --email eopAdmin@example.com --password <密碼>

# 教師管理（含頭像上傳）
python3 tests/e2e/live_e2e_teacher_flow_test.py --email eopAdmin@example.com --password <密碼>

# 加班費計算
python3 tests/e2e/live_e2e_overtime_test.py --email eopAdmin@example.com --password <密碼>

# 試上轉正 + 獎金
python3 tests/e2e/live_e2e_trial_to_formal_test.py --email eopAdmin@example.com --password <密碼>

# 請假流程
python3 tests/e2e/live_e2e_leave_flow_test.py --email eopAdmin@example.com --password <密碼>

# 合約 CRUD + PDF + S3
python3 tests/e2e/live_e2e_contracts_test.py --email eopAdmin@example.com --password <密碼>

# 課程 + 選課
python3 tests/e2e/live_e2e_courses_test.py --email eopAdmin@example.com --password <密碼>
```

### 一次跑全部 E2E（bash 腳本）

```bash
PW="你的密碼"
for f in tests/e2e/live_e2e_*.py; do
  echo "========== $(basename $f) =========="
  python3 "$f" --email eopAdmin@example.com --password "$PW"
  echo
done
```

---

## 獨立 Live 測試

這些測試打真實 API，針對特定功能做深度驗證。

### 認證 + 權限

```bash
# 多角色認證（自動從 .env 讀 admin 密碼）
python3 tests/live_auth_test.py

# 指定角色
python3 tests/live_auth_test.py --roles student teacher

# 權限邊界（自動從 .env 讀 admin 密碼）
python3 tests/live_permission_test.py
```

### 預約

```bash
# 預約邊界條件（30min 區塊、slot availability、衝突檢測）
python3 tests/live_booking_test.py --email eopAdmin@example.com --password <密碼>

# 併發安全
python3 tests/live_booking_concurrency_test.py --email eopAdmin@example.com --password <密碼>
```

### 代課 + 排班

```bash
# 代課流程
python3 tests/live_substitute_test.py --email eopAdmin@example.com --password <密碼>

# 排班 + 加班計算
python3 tests/live_work_schedules_test.py --email eopAdmin@example.com --password <密碼>
```

### LINE 整合

```bash
# 檢查 LINE 設定
python3 tests/live_line_binding_test.py --check-config
python3 tests/live_line_test.py --check-config

# 完整綁定測試（需要已登入帳號）
python3 tests/live_line_binding_test.py --full-test --email <email> --password <密碼>

# 訊息發送（需要 LINE User ID）
python3 tests/live_line_test.py --direct --line-user-id <LINE_USER_ID> --channel student
```

---

## 常用選項

| 選項 | 說明 | 支援的測試 |
|------|------|-----------|
| `--cleanup-only` | 只清理測試資料，不跑測試 | booking, work_schedules, trial_to_formal, leave_flow |
| `--keep-data` / `--no-cleanup` | 跑完不清理（debug 用） | substitute, auth, permission |
| `--roles student teacher` | 指定測試角色 | auth |

---

## 測試資料

- 所有測試都會自行建立測試資料，跑完自動清理
- 測試資料前綴帶時間戳（如 `E2ECTR163042_`），不會跟真實資料衝突
- 如果測試中斷導致殘留資料，用 `--cleanup-only` 清理

---

## 新增測試的 Pattern

### E2E 測試模板

```python
#!/usr/bin/env python3
import httpx, asyncio, argparse, sys, os
from datetime import datetime

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"E2EXXX{_TS}_"

class MyTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results = []
        self.client = None

    async def _post(self, path, json_data=None):
        return await self.client.post(f"{self.url}{path}", json=json_data or {})

    async def _get(self, path, params=None):
        return await self.client.get(f"{self.url}{path}", params=params)

    async def _put(self, path, json_data=None):
        return await self.client.put(f"{self.url}{path}", json=json_data or {})

    async def _delete(self, path):
        return await self.client.delete(f"{self.url}{path}")

    async def _test(self, name, fn):
        try:
            result = await fn()
            passed = result is True
            msg = "" if passed else str(result)
            self.results.append((name, passed, msg))
            print(f"  {'✓' if passed else '✗'} {name}" + (f" — {msg}" if msg else ""))
            return passed
        except Exception as e:
            self.results.append((name, False, str(e)))
            print(f"  ✗ {name} — ERROR: {e}")
            return False

    async def run(self, email, password):
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            self.client = client
            resp = await self._post("/api/v1/auth/login", {"email": email, "password": password})
            if resp.status_code != 200:
                print(f"  ✗ Login failed"); return False
            print(f"  ✓ Login")

            # 你的測試...
            await self._test("測試名稱", self._my_test)

            # Cleanup
            await self._cleanup()

            passed = sum(1 for _, ok, _ in self.results if ok)
            failed = sum(1 for _, ok, _ in self.results if not ok)
            print(f"Results: {passed}/{len(self.results)} — {'ALL PASSED' if failed == 0 else f'{failed} FAILED'}")
            return failed == 0

    async def _my_test(self):
        resp = await self._get("/api/v1/some-endpoint")
        if resp.status_code != 200: return f"{resp.status_code}"
        return True

    async def _cleanup(self):
        pass  # 清理測試資料

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    ok = await MyTester().run(args.email, args.password)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    asyncio.run(main())
```

### 重點

1. **TEST_PREFIX 帶時間戳** — 避免並行跑測試時衝突
2. **每個測試方法回傳 `True` 或錯誤訊息字串** — 不用 assert
3. **error message 用 fallback** — `body.get("detail") or body.get("message") or str(body)`
4. **cleanup 按外鍵順序刪除** — 先刪子表再刪父表
5. **放在 `tests/e2e/`** — 檔名以 `live_e2e_` 開頭
