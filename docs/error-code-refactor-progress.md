# Error code 重構進度 (#63 PR B)

> 依 Issue #78 的 mapping 表逐模組重構 696 個 raise sites。

## Phase 1 — Logger（完成）

- ✅ `_error_response` 加 `log_detail` / `log_exc_info` / `request` 參數
- ✅ 4xx → `logger.info("error_code=X status=4XX detail=...")`
- ✅ 5xx → `logger.error(..., exc_info=True)` 保留 traceback
- ✅ AuthException / HTTPException / global handler 統一吃 log_detail

Commit：`4271371` → push 後 `3e9057b`（在 PR #76）

## Phase 2 — PR A 介面（完成）

- ✅ `error_codes.py` StrEnum → IntEnum
- ✅ 26 個既有 code 改為 6 位數 `<3-status><3-seq>`
- ✅ `AppException.error_code: str → int`
- ✅ Frontend `ApiError.code: string → number`
- ✅ `fetchWithAuth.detectLogoutReason` 字串 → 401005/401006 數字

## Phase 3 — PR B 重構（進行中）

依模組重構 raise sites，加 domain-specific code，最終退役 `infer_error_code`。

### 編碼規則

6 位 code = `<3-digit HTTP status><1-digit domain><2-digit seq>`

範例：`400113 = BOOKING_DURATION_NOT_COURSE_MULTIPLE`
- `400` = HTTP 400 family
- `1` = Domain 1 (Booking)
- `13` = sequence within (Domain 1, 400)

### Domain 對應

| Domain | Files | 預估 raises |
|--------|-------|-------------|
| 1 BOOKING | bookings.py, leave_records.py, lesson_notes.py, substitute_details.py | 111 |
| 2 CONTRACT | student_contracts.py, teacher_contracts.py, teacher_bonus.py, teacher_details.py | 117 |
| 3 TEACHER | teachers.py, teacher_slots.py | 59 |
| 4 STUDENT | students.py, student_courses.py, student_teacher_preferences.py | 52 |
| 5 EMPLOYEE | employees.py, invites.py, page_permissions.py, users.py | 60 |
| 6 COURSE | courses.py | 11 |
| 7 EXTERNAL | zoom.py, google_drive.py, line_auth.py | 42 |
| 9 SYSTEM | alerts.py, auth.py | 7 |
| **總計** | — | **459** distinct codes |

### 重構進度（逐檔）

| File | Raises | Distinct | Status | Code 範圍 | Commit |
|------|--------|----------|--------|-----------|--------|
| **Domain 1 — BOOKING** | | | | | |
| `bookings.py` | 88 | 55 | 🟢 完成 | 400100-400130, 403101-403108, 404101-404102, 409101-409102, 500101-500111, 502101 | `0066312` |
| `leave_records.py` | 33 | 27 | 🟢 完成 | 400131-400140, 403109-403116, 404103 (+sharing 404101), 500112-500116 | `d77f53b` |
| `lesson_notes.py` | 12 | 12 | 🟢 完成 | 400141-400142, 403117-403120, 404104-404105, 409103-409105 | — |
| `substitute_details.py` | 21 | 19 | 🟢 完成 | 400143-400149, 403121-403123, 404106 (+sharing 404101), 409106-409107, 500117-500121 | — |
| **Domain 2 — CONTRACT** | | | | | |
| `student_contracts.py` | 104 | 69 | 🟢 完成 | 400201-400215, 403201-403208, 404201-404207, 500201-500226 | — |
| `teacher_contracts.py` | 96 | — | ⚪ 未開始 | — | — |
| `teacher_bonus.py` | 15 | — | ⚪ 未開始 | — | — |
| `teacher_details.py` | 25 | — | ⚪ 未開始 | — | — |
| **Domain 3 — TEACHER** | | | | | |
| `teacher_slots.py` | 50 | — | ⚪ 未開始 | — | — |
| `teachers.py` | 35 | — | ⚪ 未開始 | — | — |
| **Domain 4 — STUDENT** | | | | | |
| `students.py` | 33 | — | ⚪ 未開始 | — | — |
| `student_courses.py` | 13 | — | ⚪ 未開始 | — | — |
| `student_teacher_preferences.py` | 22 | — | ⚪ 未開始 | — | — |
| **Domain 5 — EMPLOYEE** | | | | | |
| `employees.py` | 26 | — | ⚪ 未開始 | — | — |
| `invites.py` | 13 | — | ⚪ 未開始 | — | — |
| `page_permissions.py` | 28 | — | ⚪ 未開始 | — | — |
| `users.py` | 8 | — | ⚪ 未開始 | — | — |
| **Domain 6 — COURSE** | | | | | |
| `courses.py` | 16 | — | ⚪ 未開始 | — | — |
| **Domain 7 — EXTERNAL** | | | | | |
| `zoom.py` | 41 | — | ⚪ 未開始 | — | — |
| `google_drive.py` | 6 | — | ⚪ 未開始 | — | — |
| `line_auth.py` | 2 | — | ⚪ 未開始 | — | — |
| **Domain 9 — SYSTEM** | | | | | |
| `alerts.py` | 5 | — | ⚪ 未開始 | — | — |
| `auth.py` | 3 | — | ⚪ 未開始 | — | — |

圖例：⚪ 未開始 / 🟡 進行中 / 🟢 完成 / 🔴 卡住

### Helper 函式（已擴充）

`backend/app/core/exceptions.py` 提供：

| Helper | Status | 用途 |
|--------|--------|------|
| `bad_request(detail, error_code)` | 400 | 通用驗證 |
| `forbidden(detail, error_code)` | 403 | 權限不足 |
| `not_found(resource, error_code)` | 404 | 資源不存在 |
| `conflict(detail, error_code)` | 409 | 資源衝突 |
| `internal_error(detail, error_code)` | 500 | 內部錯誤 |
| `service_unavailable(detail, error_code)` | 503 | 上游服務暫時無法使用 |
| `bad_gateway(detail, error_code)` | 502 | 上游服務錯誤 |
| `duplicate(field, error_code)` | 400 | 重複值衝突 |

### 退役計畫

`infer_error_code` 在所有 raise 都顯式給 code 後可移除：

- `backend/app/core/error_codes.py` `infer_error_code()`
- `backend/app/main.py` `http_exception_handler` 內 `explicit_code or infer_error_code(...)` → 改成只用 explicit

退役條件：上表所有 file Status 為 🟢。

## 相關 Issues / PRs

- Parent: #63（Phase 1+2 主追蹤）
- Inventory: #78（459 個 code mapping）
- 前置 PR: #76（含 Phase 1 + PR A）
- 具體 case: #30（軟刪同名衝突 → 500，PR B 完成後自然解掉）
