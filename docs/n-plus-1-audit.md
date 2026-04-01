# N+1 查詢審計報告

> 審計日期：2026-04-01
> 最後更新：2026-04-01

## 總覽

| 嚴重度 | 數量 | 已修復 |
|--------|------|--------|
| CRITICAL | 4 | 4 |
| HIGH | 6 | 6 |
| **合計** | **10** | **10** |

---

## CRITICAL（每頁可能觸發 100+ 次多餘查詢）

### 1. bookings.py — list_bookings → enrich_booking_with_relations

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/bookings.py`
- **位置**：list_bookings 約 line 590，enrich_booking_with_relations 約 line 359
- **問題**：列表查出 N 筆預約後，逐筆呼叫 enrich，每筆內部查 6~8 次
  - SELECT student（學生名）
  - SELECT teacher（教師名）
  - SELECT teacher_contract（教師合約）
  - SELECT course（課程名）
  - SELECT teacher_work_schedules（教師時段）
  - SELECT course（重複查課程）
- **影響**：20 筆/頁 × 8 查詢 = **~160 次額外查詢**
- **建議修復**：主查詢改用 LEFT JOIN 帶出所有關聯名稱，移除 enrich 迴圈
- **修復方式**：單一 SQL JOIN 8 張表 + LATERAL 請假檢查 + 批次取工作時段計算加班
- **修復日期**：2026-04-01

### 2. bookings.py — get_student_allowed_teachers

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/bookings.py`
- **位置**：約 line 110-170
- **問題**：三層巢狀迴圈
  - 外層：遍歷學生偏好（N 筆）
  - 中層：查符合的教師列表（每筆偏好 M 位教師）
  - 內層：查每位教師的合約費率（每位教師 K 份合約）
- **影響**：最差情況 10 偏好 × 50 教師 × 3 合約 = **~1500 次查詢**
- **建議修復**：改用單一 SQL 搭配 JOIN + WHERE 條件，一次取得符合條件的教師清單
- **修復方式**：三層巢狀改為分類處理 — 情境1直接加ID、情境2單一查詢、情境3用 JOIN teachers+contracts+details
- **修復日期**：2026-04-01
- **測試結果**：E2E booking flow 20/21 passed（Zoom OAuth 過期非相關問題）

### 3. student_contracts.py — list → enrich_contract_with_relations

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/student_contracts.py`
- **位置**：list 約 line 323，enrich 約 line 86
- **問題**：列表查出 N 筆合約後，逐筆 enrich
  - SELECT student（學生名）
  - SELECT contract_details（明細）
    - 明細內再逐筆 SELECT course（課程名）← 巢狀 N+1
  - SELECT leave_records（請假記錄）
  - SELECT addendums（附約）
- **影響**：20 筆/頁 × 5 查詢 + 明細內查詢 = **~100+ 次額外查詢**
- **建議修復**：
  - 主查詢用 LATERAL 子查詢帶出學生名
  - 明細/請假/附約改用批次 IN 查詢或 LATERAL
- **修復方式**：批次 ANY($1) 查詢學生/明細(JOIN courses)/請假/附約，asyncio.gather 並行，lookup map 組裝
- **修復日期**：2026-04-01
- **測試結果**：E2E booking flow 20/21 passed

### 4. teacher_contracts.py — list → enrich_contract_with_relations

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/teacher_contracts.py`
- **位置**：list 約 line 267，enrich 約 line 82
- **問題**：同 #3 模式
  - SELECT teacher（教師名）
  - SELECT contract_details + 逐筆查課程
  - SELECT work_schedules（工作時段）
  - SELECT addendums（附約）
- **影響**：**~100+ 次額外查詢**
- **建議修復**：同 #3
- **修復方式**：同 #3 — 批次 ANY + asyncio.gather + lookup map
- **修復日期**：2026-04-01
- **測試結果**：E2E booking flow 20/21 passed

---

## HIGH（每頁 20~60 次多餘查詢）

### 5. zoom.py — list_meeting_logs → enrich_meeting_log

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/zoom.py`
- **位置**：list 約 line 320，enrich_meeting_log 函式
- **問題**：每筆會議記錄逐筆查帳號名稱、教師名稱
- **影響**：20 筆/頁 × 3 查詢 = **~60 次額外查詢**
- **建議修復**：主查詢 LEFT JOIN zoom_accounts + teachers
- **修復方式**：批次 ANY + asyncio.gather 查帳號名/教師名，lookup map 組裝
- **修復日期**：2026-04-01

### 6. student_teacher_preferences.py — list → enrich_preference

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/student_teacher_preferences.py`
- **位置**：list 約 line 64，enrich 約 line 15
- **問題**：每筆偏好逐筆查
  - SELECT student（學生名）
  - SELECT course（課程名）
  - SELECT teacher（指定教師名）
- **影響**：20 筆 × 3 查詢 = **~60 次額外查詢**
- **建議修復**：主查詢 LEFT JOIN students + courses + teachers
- **修復方式**：批次 ANY + asyncio.gather + lookup map
- **修復日期**：2026-04-01

### 7. teacher_slots.py — list → enrich_slot_with_relations

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/teacher_slots.py`
- **位置**：list 約 line 129，enrich 約 line 32
- **問題**：每筆時段逐筆查
  - SELECT teacher（教師名）
  - SELECT teacher_contract（合約編號）
- **影響**：20 筆 × 2 查詢 = **~40 次額外查詢**
- **建議修復**：主查詢 LEFT JOIN teachers + teacher_contracts
- **修復方式**：批次 ANY + asyncio.gather + lookup map
- **修復日期**：2026-04-01

### 8. student_courses.py — list → enrich_enrollment

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/student_courses.py`
- **位置**：list 約 line 122，enrich 約 line 17
- **問題**：每筆選課逐筆查
  - SELECT course（課程名）
  - SELECT student（學生名）
- **影響**：20 筆 × 2 查詢 = **~40 次額外查詢**
- **建議修復**：主查詢 LEFT JOIN courses + students
- **修復方式**：批次 ANY + asyncio.gather + lookup map（含 by-student 端點）
- **修復日期**：2026-04-01

### 9. employees.py — list → enrich_employee

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/employees.py`
- **位置**：list 迴圈 enrich_employee
- **問題**：每筆員工逐筆查 user_profiles + roles 取得角色名稱
- **影響**：20 筆 × 1 查詢 = **~20 次額外查詢**
- **建議修復**：主查詢 LEFT JOIN user_profiles + roles
- **修復方式**：批次 ANY 查 user_profiles + roles，lookup map 組裝
- **修復日期**：2026-04-01

### 10. student_contracts.py — get_course_options 迴圈查課程

- **狀態**：✅ 已修復
- **檔案**：`backend/app/api/v1/student_contracts.py`
- **位置**：約 line 206-214
- **問題**：取得學生選課後，逐一 SELECT course 查課程名稱
- **影響**：N 門課 = **N 次額外查詢**
- **建議修復**：改用 `WHERE id IN (course_ids)` 批次查詢
- **修復方式**：改用 `WHERE id = ANY($1)` 單次批次查詢
- **修復日期**：2026-04-01

---

## 已修復的 View API（參考）

以下 API 已在先前優化中修復 N+1 問題：

| API | 修復方式 | 修復日期 |
|-----|---------|---------|
| `GET /students/{id}/view` | asyncio.gather 並行 + CTE 統計 | 2026-03-27 |
| `GET /teachers/{id}/view` | asyncio.gather 並行 + CTE 統計 + LATERAL | 2026-03-27 |
| `GET /students/overview/list` | 單一 SQL + LATERAL 子查詢 | 2026-03-26 |

---

## 修復優先順序建議

1. **#1 bookings list** — 使用頻率最高，影響最大
2. **#2 get_student_allowed_teachers** — 最差情況查詢爆炸
3. **#3 student_contracts list** — 合約管理常用
4. **#4 teacher_contracts list** — 同上
5. **#5~#10** — 依使用頻率逐步修復

## 通用修復模式

```python
# ❌ N+1 模式（避免）
items = await table_select(table="bookings", ...)
for item in items:
    student = await table_select(table="students", filters={"id": item["student_id"]})
    item["student_name"] = student[0]["name"]

# ✅ JOIN 模式（推薦）
items = await pool.fetch("""
    SELECT b.*, s.name AS student_name, t.name AS teacher_name
    FROM bookings b
    LEFT JOIN students s ON s.id = b.student_id
    LEFT JOIN teachers t ON t.id = b.teacher_id
    WHERE b.is_deleted = FALSE
    ORDER BY b.created_at DESC
    LIMIT $1 OFFSET $2
""", limit, offset)

# ✅ 批次 IN 查詢模式
ids = [item["course_id"] for item in items]
courses = await pool.fetch(
    "SELECT id, course_name FROM courses WHERE id = ANY($1)", ids
)
course_map = {str(c["id"]): c["course_name"] for c in courses}
for item in items:
    item["course_name"] = course_map.get(item["course_id"])

# ✅ asyncio.gather 模式（無法合併 SQL 時）
results = await asyncio.gather(*[
    enrich_item(item) for item in items
])
```
