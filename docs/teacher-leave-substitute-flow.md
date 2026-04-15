# 教師請假與代課完整流程

> 最後更新：2026-04-02

## 總覽

教師無法出席已確認的預約時，系統提供「請假 + 代課」機制。員工可在核准請假前先指派代課教師，確保學生課程不中斷。

```
教師有事無法上課
    ↓
建立請假申請（leave_record, pending）
    ↓
員工處理 ─┬─ 先查詢可代課教師 → 指派代課 → 核准請假（booking 維持 confirmed）
          ├─ 無代課直接核准 → booking 取消 → 堂數退回 + Zoom 取消
          ├─ 駁回 → booking 不變
          └─ 申請人撤回 → 取消請假
```

---

## 一、請假申請

### 1.1 誰可以發起

| 發起者 | 條件 | initiator_type |
|--------|------|---------------|
| 教師本人 | 只能對自己的預約 | teacher |
| 學生本人 | 只能對自己的預約 | student |
| 員工 | 可代任何人建立 | student（預設） |

### 1.2 前置條件

- 預約必須是 `confirmed` 狀態
- 同一預約不能有兩筆 `pending` 請假
- 距離上課時間 ≥ 30 分鐘

### 1.3 請假類型（系統自動判定）

| 距上課時間 | 類型 | 額度限制 |
|-----------|------|---------|
| < 30 分鐘 | 禁止 | 直接擋回 |
| 0.5 ~ 24 小時 | 緊急 (emergency) | 每合約 ceil(總堂數 x 0.2) 次 |
| >= 24 小時 | 一般 (normal) | 無限制 |

### 1.4 API

```
POST /api/v1/leave-records
Body: { booking_id, reason }
```

---

## 二、代課教師指派（員工操作）

### 2.1 查詢可用代課教師

```
GET /api/v1/bookings/options/substitute-teachers?booking_id={id}
```

系統自動篩選符合以下**全部條件**的教師：

| 條件 | 說明 |
|------|------|
| A. 有涵蓋時段 | 代課教師在預約日期有 slot，且 start_time ≤ 預約起始、end_time ≥ 預約結束 |
| B. 合約有該課程費率 | 代課教師的有效合約 teacher_contract_details 有該 course_id 的 course_rate |
| C. 無時間衝突 | 該時段沒有其他正常預約，也沒有其他代課安排 |

回傳：符合條件的教師清單，附合約資訊與時薪

### 2.2 指派代課

```
POST /api/v1/substitute-details
Body: { booking_id, substitute_teacher_id, substitute_contract_id, reason? }
```

**驗證流程（依序）：**

```
1. 預約存在且 confirmed
2. 預約尚無代課紀錄
3. 不能指派原教師自己
4. 代課教師存在且啟用
5. 代課教師在該日有涵蓋時段
6. 代課教師合約有效
7. 代課教師合約包含此課程
8. 代課教師當日無其他預約衝突（含正常預約 + 其他代課）
```

**成功後：**
- 建立 `substitute_details` 紀錄（含 substitute_hourly_rate）
- 更新 `bookings.substitute_detail_id` 指向該紀錄
- booking 狀態不變（維持 confirmed）

### 2.3 取消代課

```
DELETE /api/v1/substitute-details/{sub_id}
```

- 軟刪除 substitute_details
- 清除 `bookings.substitute_detail_id`
- booking 狀態改回 `pending`（需教師重新確認）

---

## 三、請假審核（員工操作）

### 3.1 核准

```
POST /api/v1/leave-records/{leave_id}/approve
```

系統根據 `bookings.substitute_detail_id` 自動分流：

#### 路徑 A：有代課教師

| 項目 | 動作 |
|------|------|
| leave_status | → approved |
| booking 狀態 | 維持 confirmed（代課教師照上） |
| 合約堂數 | 不恢復（堂數照扣） |
| 教師時段 | 不釋放 |
| Zoom 會議 | 不取消 |
| 請假計數 | used_leave_count += 1 |
| 緊急請假計數 | used_emergency_leave_count += 1（僅 emergency） |
| 歷史記錄 | 寫入 student_contract_leave_records |

#### 路徑 B：無代課教師

| 項目 | 動作 |
|------|------|
| leave_status | → approved |
| booking 狀態 | → cancelled |
| 合約堂數 | remaining_lessons += lessons_used（恢復） |
| 教師時段 | 釋放（重算 is_booked） |
| Zoom 會議 | 取消 |
| 請假計數 | used_leave_count += 1 |
| 緊急請假計數 | used_emergency_leave_count += 1（僅 emergency） |
| 歷史記錄 | 寫入 student_contract_leave_records |

### 3.2 駁回

```
POST /api/v1/leave-records/{leave_id}/reject
Body: { rejection_reason }
```

- leave_status → rejected
- booking 不變（維持 confirmed）

### 3.3 撤回

```
POST /api/v1/leave-records/{leave_id}/cancel
```

- 僅 pending 狀態可撤回
- leave_status → cancelled
- booking 不變

---

## 四、完整時序圖

### 4.1 有代課教師的完整流程

```
教師       員工                    系統
  |                                 |
  |-- 建立請假申請 ----------------->|
  |          (pending)              |
  |                                 |
  |         查詢可用代課教師 ------->|
  |         <-- 回傳候選名單 --------|
  |                                 |
  |         指派代課教師 ----------->|
  |         (建立 substitute_detail) |
  |         (booking.substitute_detail_id 設值)
  |                                 |
  |         核准請假 --------------->|
  |         (檢查 substitute_detail_id 不為 NULL)
  |         (booking 維持 confirmed) |
  |                                 |
  |     代課教師照原時間上課         |
```

### 4.2 無代課教師的流程

```
教師       員工                    系統
  |                                 |
  |-- 建立請假申請 ----------------->|
  |          (pending)              |
  |                                 |
  |         查詢可用代課教師 ------->|
  |         <-- 回傳空列表 [] ------|
  |                                 |
  |         （找不到代課）           |
  |         直接核准請假 ----------->|
  |         (substitute_detail_id = NULL)
  |         (booking → cancelled)   |
  |         (堂數退回合約)           |
  |         (釋放教師時段)           |
  |         (取消 Zoom 會議)         |
  |                                 |
  |     學生該堂課被取消             |
```

---

## 五、目前問題與待處理事項

### 問題 1：無代課時直接取消，沒有緩衝機制

**現況**：員工可以在沒有安排代課的情況下直接核准請假，系統立即取消預約。

**風險**：
- 員工誤操作直接核准，學生課程被取消且無法復原
- 沒有時間窗口讓其他員工嘗試尋找代課教師

**待處理**：

- [ ] **方案 A（推薦 — 改動小）**：核准時加入確認機制
  - 當 `substitute_detail_id` 為 NULL 時，核准 API 要求額外傳入 `confirm_cancel: true` 參數
  - 不傳或為 false 時回傳 warning：「此預約尚無代課老師，核准將直接取消預約，是否確認？」
  - 前端顯示二次確認 Dialog
  - **涉及檔案**：`leave_records.py` approve 端點、前端請假審核 Modal

- [ ] **方案 B（完整 — 改動大）**：新增「待安排代課」中間狀態
  - booking_status 加入 `substitute_pending`
  - 核准請假時若無代課 → booking 進入 `substitute_pending`
  - 員工在時間窗口內安排代課 → booking 回到 `confirmed`
  - 超過期限（如開課前 2 小時）仍無代課 → 自動取消
  - **涉及檔案**：booking schema enum、leave_records.py、substitute_details.py、前端狀態顯示、可能需排程任務

### 問題 2：核准順序未強制

**現況**：員工可以先核准請假，再安排代課（但此時預約已經被取消了）。也可以先安排代課再核准。

**正確順序應為**：先安排代課（如有） → 再核准請假

**待處理**：

- [ ] 在請假審核 UI 加入引導提示，提醒員工先查看/安排代課
- [ ] 或在 API 層面強制：若有可用代課教師但未安排，核准時回傳提示（非硬擋）

### 問題 3：教師請假 vs 學生請假的代課邏輯差異

**現況**：代課僅在「教師請假」場景有意義。學生請假時不需要代課，因為課就是取消。

**但程式碼中**：approve 時統一檢查 `substitute_detail_id`，不區分 initiator_type。學生請假若剛好有 substitute_detail（理論上不會發生但未擋），也會走「有代課」路徑。

**待處理**：

- [ ] 在 approve 邏輯中，若 `initiator_type = student`，跳過代課檢查，直接走取消路徑
- [ ] 或驗證：學生請假的預約不應該有 substitute_detail_id

### 問題 4：缺少通知機制

**現況**：請假建立、核准、代課指派等操作都沒有推送通知。

**待處理**：

- [ ] 教師建立請假 → 通知員工審核（LINE / Email）
- [ ] 核准取消 → 通知學生課程已取消
- [ ] 指派代課 → 通知代課教師 + 學生（教師已更換）
- [ ] 依賴：LINE messaging service（已有基礎設施）、Email service（Backlog）

### 問題 5：代課教師在學生偏好白名單的驗證

**現況**：`substitute_details.py` 中**沒有**檢查代課教師是否在學生偏好白名單內。

**但 `booking-flow.md` 文件中標註了**驗證項目包含「代課教師必須在學生偏好白名單內」。

**待處理**：

- [ ] 確認業務規則：代課教師是否需要在學生偏好白名單內？
  - 如果是 → 需在 `create_substitute_detail` 中加入白名單驗證
  - 如果否 → 更新 `booking-flow.md` 文件移除該條件

### ~~問題 6：代課教師無法查看被指派的預約與 Zoom / 錄影~~ (已修復)

**已修復（2026-04-02）**，修改內容：

- [x] `bookings.py` GET /bookings — 教師 WHERE 條件加入 `OR EXISTS(substitute_details.substitute_teacher_id)`
- [x] `bookings.py` GET /bookings/{id} — 權限檢查加入代課教師判斷
- [x] `zoom.py` GET /zoom/meetings/{booking_id} — 權限檢查加入代課教師判斷（含 Zoom 連結 + Drive 錄影）
- [x] `substitute_details.py` 新增 GET /substitute-details/my — 代課教師查看自己的代課指派

---

## 六、涉及的資料表

| 表 | 用途 |
|----|------|
| `leave_records` | 請假主表（狀態、類型、審核資訊） |
| `substitute_details` | 代課紀錄（代課教師、合約、時薪） |
| `bookings` | 預約主表（substitute_detail_id 指向代課） |
| `student_contracts` | 請假計數器（used_leave_count 等） |
| `student_contract_leave_records` | 核准後的請假歷史 |
| `teacher_available_slots` | 教師開放時段（代課驗證用） |
| `teacher_contracts` / `teacher_contract_details` | 代課教師合約與課程費率 |
| `zoom_meeting_logs` | Zoom 會議（取消預約時連帶取消） |

---

## 七、API 端點總覽

| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/v1/leave-records` | POST | 建立請假 |
| `/api/v1/leave-records` | GET | 請假列表 |
| `/api/v1/leave-records/{id}` | GET | 請假詳情 |
| `/api/v1/leave-records/{id}/approve` | POST | 核准請假 |
| `/api/v1/leave-records/{id}/reject` | POST | 駁回請假 |
| `/api/v1/leave-records/{id}/cancel` | POST | 撤回請假 |
| `/api/v1/bookings/options/substitute-teachers` | GET | 查詢可用代課教師 |
| `/api/v1/substitute-details` | POST | 指派代課 |
| `/api/v1/substitute-details` | GET | 代課紀錄列表 |
| `/api/v1/substitute-details/{id}` | GET | 代課紀錄詳情 |
| `/api/v1/substitute-details/{id}` | DELETE | 取消代課 |
| `/api/v1/substitute-details/my` | GET | 代課教師查看自己的代課指派 |

---

## 八、程式碼位置

| 檔案 | 說明 |
|------|------|
| `backend/app/api/v1/leave_records.py` | 請假 CRUD + 審核 |
| `backend/app/api/v1/substitute_details.py` | 代課 CRUD |
| `backend/app/api/v1/bookings.py` | cancel_booking_side_effects + 代課教師選項 |
| `backend/app/schemas/leave_record.py` | 請假 schemas |
| `backend/app/schemas/substitute_detail.py` | 代課 schemas |
| `backend/app/schemas/booking.py` | BookingStatus enum |
| `supabase/migrations/001_complete_schema.sql` | bookings / substitute_details / leave_records 表定義 |
| `supabase/migrations/006_student_contract_leave_and_courses.sql` | student_contract_leave_records 表 |
| `supabase/migrations/035_leave_type_emergency_quota.sql` | 緊急請假欄位 |
