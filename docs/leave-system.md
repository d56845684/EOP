# 課堂請假系統邏輯文件

> 最後更新：2026-03-26

## 請假流程

```
學生/教師 申請請假 → 待審核(pending) → 員工 核准/駁回
                                    ↗ 核准 → 取消預約 + 恢復堂數 + 取消 Zoom
                                    ↘ 駁回 → 不動，預約維持
```

## API 端點

| 端點 | 方法 | 說明 | 權限 |
|------|------|------|------|
| `/api/v1/leave-records` | POST | 建立請假申請 | bookings.list |
| `/api/v1/leave-records` | GET | 列表（依角色篩選） | bookings.list |
| `/api/v1/leave-records/{id}` | GET | 單筆詳情 | bookings.list |
| `/api/v1/leave-records/{id}/approve` | POST | 核准請假 | bookings.edit + 員工 |
| `/api/v1/leave-records/{id}/reject` | POST | 駁回請假（需填理由） | bookings.edit + 員工 |
| `/api/v1/leave-records/{id}/cancel` | POST | 撤回請假申請 | bookings.list |

## 請假類型判定（自動）

系統根據「距離上課時間」自動判定請假類型：

| 距離上課時間 | 類型 | 處理 |
|-------------|------|------|
| < 30 分鐘 | 禁止 | 直接擋回：「課程開始前 30 分鐘內無法請假」 |
| 0.5 ~ 24 小時 | 緊急請假 (emergency) | 檢查緊急額度，超過則擋回 |
| ≥ 24 小時 | 一般請假 (normal) | 正常流程，不扣額度 |

## 緊急請假額度

```
額度 = ceil(合約總堂數 × 0.2)
例如：41 堂 → 額度 9 次
```

- 額度以合約為單位，記錄在 `student_contracts.used_emergency_leave_count`
- 已用完時擋回：「緊急請假額度已用完 (X/Y)」

## 核准後的副作用

### 無代課老師

| 項目 | 動作 |
|------|------|
| 預約狀態 | → cancelled |
| 合約堂數 | remaining_lessons += lessons_used（恢復） |
| 教師時段 | 釋放（update_slot_booked_status） |
| Zoom 會議 | 取消（cancel_meeting_for_booking） |
| 請假計數 | used_leave_count += 1 |
| 緊急請假計數 | used_emergency_leave_count += 1（僅緊急請假） |
| 歷史記錄 | 寫入 student_contract_leave_records |

### 有代課老師（substitute_detail_id 不為 NULL）

| 項目 | 動作 |
|------|------|
| 預約狀態 | 維持 confirmed（代課老師照上） |
| 合約堂數 | 不恢復 |
| Zoom 會議 | 不取消 |
| 請假計數 | used_leave_count += 1 |
| 緊急請假計數 | used_emergency_leave_count += 1（僅緊急請假） |
| 歷史記錄 | 寫入 student_contract_leave_records |

## 駁回 / 撤回

- **駁回**：員工操作，需填 rejection_reason，預約不變，計數器不變
- **撤回**：申請人自己取消，只有 pending 狀態可撤回，預約不變

## 權限控制

| 角色 | 可建立 | 可撤回 | 可核准/駁回 |
|------|--------|--------|------------|
| 學生 | 自己的預約 | 自己的 pending | 不可 |
| 教師 | 自己的預約 | 自己的 pending | 不可 |
| 員工 | 代學生建立（預設 initiator_type=student） | 任何 pending | 可以 |

## 限制條件

- 同一預約不能有兩筆 pending 請假申請
- 只有 `confirmed` 狀態的預約可以請假
- `deduct_lesson` 建立時永遠為 false（目前未使用額外扣堂邏輯）
- 時間判定使用 UTC+8（台灣時間）

## 請假編號格式

```
LV + YYYYMMDD + 3 位流水號
例如：LV20260326001
```

## 涉及的資料表

| 表 | 用途 |
|----|------|
| `leave_records` | 請假主表（狀態、類型、原因、審核資訊） |
| `student_contracts` | used_leave_count / used_emergency_leave_count 計數器 |
| `student_contract_leave_records` | 核准後的歷史記錄（關聯到合約） |
| `bookings` | 關聯預約，核准時可能被取消 |
| `zoom_meeting_logs` | 核准取消預約時連帶取消 Zoom 會議 |

## 資料表欄位

### leave_records

| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | Primary Key |
| leave_no | VARCHAR(50) | 請假編號（唯一） |
| initiator_type | ENUM | 'student' 或 'teacher' |
| initiator_student_id | UUID | FK → students（學生請假時） |
| initiator_teacher_id | UUID | FK → teachers（教師請假時） |
| booking_id | UUID | FK → bookings（關聯的預約） |
| leave_date | DATE | 請假日期 |
| start_time / end_time | TIME | 請假時段 |
| reason | TEXT | 請假原因（必填） |
| leave_status | ENUM | pending / approved / rejected / cancelled |
| leave_type | VARCHAR(20) | 'normal' 或 'emergency' |
| deduct_lesson | BOOLEAN | 是否扣堂（目前建立時永遠 false） |
| approver_id | UUID | FK → employees（審核人） |
| approved_at | TIMESTAMPTZ | 審核時間 |
| rejection_reason | TEXT | 駁回原因 |

### student_contracts 相關欄位

| 欄位 | 說明 |
|------|------|
| total_leave_allowed | 一般請假允許次數 |
| used_leave_count | 已使用一般請假次數 |
| used_emergency_leave_count | 已使用緊急請假次數 |

## 程式碼位置

| 檔案 | 說明 |
|------|------|
| `backend/app/api/v1/leave_records.py` | 請假 API 端點 |
| `backend/app/schemas/leave_record.py` | Pydantic schemas |
| `backend/app/api/v1/bookings.py` | cancel_booking_side_effects（核准時呼叫） |
| `frontend-dennis/src/lib/api/leaveRecords.ts` | 前端 API client |
| `frontend-dennis/src/app/bookings/page.tsx` | 前端請假 Modal（建立/審核） |
| `supabase/migrations/001_complete_schema.sql` | leave_records 表定義 |
| `supabase/migrations/006_student_contract_leave_and_courses.sql` | 合約請假記錄表 |
| `supabase/migrations/035_leave_type_emergency_quota.sql` | 緊急請假欄位 |
