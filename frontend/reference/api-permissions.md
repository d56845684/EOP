# API 權限對照表

> 自動整理自 `backend/app/api/v1/` 所有端點，最後更新：2026-04-10

## 權限類型說明

| 類型 | 說明 |
|------|------|
| `None` | 公開端點，無需登入 |
| `get_current_user` | 需登入，不限角色 |
| `require_staff` | 僅限 employee / admin |
| `require_teacher` | 僅限 teacher / employee / admin |
| `require_page_permission("key")` | 依 role_pages 設定，角色須擁有該 page key |

---

## 角色預設 Page Keys

| Page Key | Admin | Employee | Teacher | Student |
|----------|:-----:|:--------:|:-------:|:-------:|
| dashboard | v | v | v | v |
| courses | v | v | | v |
| courses.list | v | v | v | v |
| courses.create | v | v | | |
| courses.edit | v | v | | |
| courses.delete | v | v | | |
| students | v | v | | |
| students.list | v | v | | |
| students.create | v | v | | |
| students.edit | v | v | | |
| students.delete | v | v | | |
| students.contracts | v | v | | v |
| students.courses | v | v | | v |
| teachers | v | v | | |
| teachers.list | v | v | v | |
| teachers.create | v | v | | |
| teachers.edit | v | v | | |
| teachers.delete | v | v | | |
| teachers.contracts | v | v | v | |
| teachers.slots | v | v | v | v |
| teachers.bonus | v | v | v | |
| teachers.details | v | v | v | |
| bookings | v | v | v | v |
| bookings.list | v | v | v | v |
| bookings.create | v | v | | v |
| bookings.edit | v | v | v | |
| bookings.delete | v | v | | |
| employees | v | v | | |
| employees.list | v | v | | |
| employees.create | v | v | | |
| employees.edit | v | v | | |
| employees.delete | v | v | | |
| permissions | v | | | |
| permissions.pages | v | | | |
| permissions.roles | v | | | |
| permissions.users | v | | | |
| profile | v | v | v | v |
| profile.edit | v | v | v | v |

---

## Auth (`/api/v1/auth`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| POST | `/auth/login` | None | 用戶登入 |
| POST | `/auth/logout` | get_current_user | 用戶登出 |
| POST | `/auth/refresh` | None | 刷新 Token |
| GET | `/auth/me` | get_current_user | 取得當前用戶資訊 |
| GET | `/auth/sessions` | get_current_user | 取得用戶所有 Sessions |
| DELETE | `/auth/sessions/{session_id}` | get_current_user | 撤銷特定 Session |
| POST | `/auth/password/reset` | None | 請求重設密碼 |
| POST | `/auth/password/change` | get_current_user | 變更密碼 |

## Auth - LINE (`/api/v1/auth/line`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/auth/line/login` | None | 取得 LINE 登入 URL |
| GET | `/auth/line/callback` | None | LINE OAuth 回調 |
| POST | `/auth/line/bind` | get_current_user | 取得綁定 LINE 的 URL |
| DELETE | `/auth/line/unbind` | get_current_user | 解除 LINE 綁定 |
| GET | `/auth/line/status` | get_current_user | 取得 LINE 綁定狀態 |
| GET | `/auth/line/bindings` | get_current_user | 取得用戶所有頻道的 LINE 綁定狀態 |

## Health (`/api/v1/health`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/health/` | None | 基本健康檢查 |
| GET | `/health/ready` | None | 就緒檢查（含依賴服務） |

---

## Courses (`/api/v1/courses`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/courses` | courses.list | 取得課程列表 |
| GET | `/courses/{course_id}` | courses.list | 取得單一課程 |
| POST | `/courses` | courses.create | 建立課程 |
| PUT | `/courses/{course_id}` | courses.edit | 更新課程 |
| DELETE | `/courses/{course_id}` | courses.delete | 刪除課程（軟刪除） |

---

## Students (`/api/v1/students`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/students` | students.list | 取得學生列表 |
| GET | `/students/{student_id}` | students.list | 取得單一學生 |
| POST | `/students` | students.create | 建立學生 |
| PUT | `/students/{student_id}` | students.edit | 更新學生 |
| DELETE | `/students/{student_id}` | students.delete | 刪除學生（軟刪除） |
| POST | `/students/{student_id}/convert-to-formal` | students.edit | 試上學生轉正式學生 |
| GET | `/students/overview/list` | students.list | 學生總覽列表 |
| GET | `/students/{student_id}/view` | students.list | 學生綜合檢視 |

## Student Courses (`/api/v1/student-courses`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/student-courses/options/students` | students.courses | 取得學生下拉選單 |
| GET | `/student-courses/options/courses` | students.courses | 取得課程下拉選單 |
| GET | `/student-courses` | students.courses | 取得學生選課列表 |
| GET | `/student-courses/by-student/{student_id}` | students.courses | 取得某學生的已選課程 |
| POST | `/student-courses` | students.edit | 新增學生選課 |
| DELETE | `/student-courses/{enrollment_id}` | students.edit | 移除學生選課（軟刪除） |

## Student Contracts (`/api/v1/student-contracts`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/student-contracts/options/students` | students.contracts | 取得學生下拉選單 |
| GET | `/student-contracts/options/courses` | students.contracts | 取得課程下拉選單 |
| GET | `/student-contracts/options/teachers` | students.contracts | 取得教師下拉選單 |
| GET | `/student-contracts` | students.contracts | 取得學生合約列表 |
| GET | `/student-contracts/{contract_id}` | students.contracts | 取得單一學生合約 |
| POST | `/student-contracts` | students.contracts | 建立學生合約 |
| PUT | `/student-contracts/{contract_id}` | students.contracts | 更新學生合約 |
| DELETE | `/student-contracts/{contract_id}` | students.contracts | 刪除學生合約（軟刪除） |

### Student Contract Details (合約明細)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/student-contracts/{contract_id}/details` | students.contracts | 取得合約明細 |
| POST | `/student-contracts/{contract_id}/details` | students.contracts | 新增合約明細 |
| PUT | `/student-contracts/{contract_id}/details/{detail_id}` | students.contracts | 更新合約明細 |
| DELETE | `/student-contracts/{contract_id}/details/{detail_id}` | students.contracts | 刪除合約明細 |

### Student Contract Leave Records (請假紀錄)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/student-contracts/{contract_id}/leave-records` | students.contracts | 取得請假紀錄 |
| POST | `/student-contracts/{contract_id}/leave-records` | students.contracts | 新增請假紀錄 |
| DELETE | `/student-contracts/{contract_id}/leave-records/{record_id}` | students.contracts | 刪除請假紀錄 |

### Student Contract Files (合約檔案)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/student-contracts/{contract_id}/generate-pdf` | students.contracts | 產生 PDF（已棄用） |
| GET | `/student-contracts/{contract_id}/generate-docx` | students.contracts | 產生 Word 文檔 |
| POST | `/student-contracts/{contract_id}/upload-url` | students.contracts | 取得合約檔案 signed upload URL |
| POST | `/student-contracts/{contract_id}/confirm-upload` | students.contracts | 確認合約檔案上傳完成 |
| GET | `/student-contracts/{contract_id}/download-url` | students.contracts | 取得合約檔案 signed download URL |

### Student Contract Addendums (附約)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/student-contracts/{contract_id}/addendums` | students.contracts | 取得附約列表 |
| POST | `/student-contracts/{contract_id}/addendums` | students.contracts | 建立附約 |
| GET | `/student-contracts/{contract_id}/addendums/{addendum_id}` | students.contracts | 取得單一附約 |
| PUT | `/student-contracts/{contract_id}/addendums/{addendum_id}` | students.contracts | 更新附約 |
| DELETE | `/student-contracts/{contract_id}/addendums/{addendum_id}` | students.contracts | 刪除附約 |
| GET | `/student-contracts/{contract_id}/addendums/{addendum_id}/generate-pdf` | students.contracts | 產生附約 PDF |
| POST | `/student-contracts/{contract_id}/addendums/{addendum_id}/upload-url` | students.contracts | 取得附約檔案 signed upload URL |
| POST | `/student-contracts/{contract_id}/addendums/{addendum_id}/confirm-upload` | students.contracts | 確認附約檔案上傳完成 |
| GET | `/student-contracts/{contract_id}/addendums/{addendum_id}/download-url` | students.contracts | 取得附約檔案 signed download URL |

## Student Teacher Preferences (`/api/v1/student-teacher-preferences`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/student-teacher-preferences/options/teachers` | students.edit | 取得教師選項（下拉選單） |
| GET | `/student-teacher-preferences/options/courses` | students.edit | 取得學生已選課程選項 |
| GET | `/student-teacher-preferences/allowed-teachers` | students.edit | 取得可預約教師白名單 |
| GET | `/student-teacher-preferences/` | students.edit | 列出學生的教師偏好設定 |
| POST | `/student-teacher-preferences/` | students.edit | 新增學生教師偏好 |
| PUT | `/student-teacher-preferences/{preference_id}` | students.edit | 更新學生教師偏好 |
| DELETE | `/student-teacher-preferences/{preference_id}` | students.edit | 刪除學生教師偏好（軟刪除） |

---

## Teachers (`/api/v1/teachers`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/teachers` | teachers.list | 取得教師列表 |
| PUT | `/teachers/me` | require_teacher | 教師更新自己的資料 |
| GET | `/teachers/overview/list` | teachers.list | 教師總覽列表 |
| GET | `/teachers/{teacher_id}` | teachers.list | 取得單一教師 |
| POST | `/teachers` | teachers.create | 建立教師 |
| PUT | `/teachers/{teacher_id}` | teachers.edit | 更新教師 |
| DELETE | `/teachers/{teacher_id}` | teachers.delete | 刪除教師（軟刪除） |
| POST | `/teachers/{teacher_id}/avatar/upload-url` | teachers.edit | 取得頭像 signed upload URL |
| POST | `/teachers/{teacher_id}/avatar/confirm-upload` | teachers.edit | 確認頭像上傳完成 |
| GET | `/teachers/{teacher_id}/view` | teachers.list | 教師綜合檢視 |

## Teacher Contracts (`/api/v1/teacher-contracts`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/teacher-contracts/options/teachers` | teachers.contracts | 取得教師下拉選單 |
| GET | `/teacher-contracts/options/courses` | teachers.contracts | 取得課程下拉選單 |
| GET | `/teacher-contracts` | teachers.contracts | 取得教師合約列表 |
| GET | `/teacher-contracts/{contract_id}` | teachers.contracts | 取得單一教師合約 |
| POST | `/teacher-contracts` | teachers.contracts | 建立教師合約 |
| PUT | `/teacher-contracts/{contract_id}` | teachers.contracts | 更新教師合約 |
| DELETE | `/teacher-contracts/{contract_id}` | teachers.contracts | 刪除教師合約（軟刪除） |

### Teacher Contract Details (合約明細)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/teacher-contracts/{contract_id}/details` | teachers.contracts | 取得合約明細 |
| POST | `/teacher-contracts/{contract_id}/details` | teachers.contracts | 新增合約明細 |
| PUT | `/teacher-contracts/{contract_id}/details/{detail_id}` | teachers.contracts | 更新合約明細 |
| DELETE | `/teacher-contracts/{contract_id}/details/{detail_id}` | teachers.contracts | 刪除合約明細 |

### Teacher Contract Work Schedules (工作時段)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/teacher-contracts/{contract_id}/work-schedules` | teachers.contracts | 取得工作時段 |
| PUT | `/teacher-contracts/{contract_id}/work-schedules` | teachers.contracts | 設定工作時段 |
| DELETE | `/teacher-contracts/{contract_id}/work-schedules` | teachers.contracts | 刪除工作時段 |

### Teacher Contract Files (合約檔案)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/teacher-contracts/{contract_id}/generate-pdf` | teachers.contracts | 產生 PDF |
| POST | `/teacher-contracts/{contract_id}/upload-url` | teachers.contracts | 取得合約檔案 signed upload URL |
| POST | `/teacher-contracts/{contract_id}/confirm-upload` | teachers.contracts | 確認合約檔案上傳完成 |
| GET | `/teacher-contracts/{contract_id}/download-url` | teachers.contracts | 取得合約檔案 signed download URL |

### Teacher Contract Addendums (附約)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/teacher-contracts/{contract_id}/addendums` | teachers.contracts | 取得附約列表 |
| POST | `/teacher-contracts/{contract_id}/addendums` | teachers.contracts | 建立附約 |
| GET | `/teacher-contracts/{contract_id}/addendums/{addendum_id}` | teachers.contracts | 取得單一附約 |
| PUT | `/teacher-contracts/{contract_id}/addendums/{addendum_id}` | teachers.contracts | 更新附約 |
| DELETE | `/teacher-contracts/{contract_id}/addendums/{addendum_id}` | teachers.contracts | 刪除附約 |
| GET | `/teacher-contracts/{contract_id}/addendums/{addendum_id}/generate-pdf` | teachers.contracts | 產生附約 PDF |
| POST | `/teacher-contracts/{contract_id}/addendums/{addendum_id}/upload-url` | teachers.contracts | 取得附約檔案 signed upload URL |
| POST | `/teacher-contracts/{contract_id}/addendums/{addendum_id}/confirm-upload` | teachers.contracts | 確認附約檔案上傳完成 |
| GET | `/teacher-contracts/{contract_id}/addendums/{addendum_id}/download-url` | teachers.contracts | 取得附約檔案 signed download URL |

## Teacher Details (`/api/v1/teacher-details`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/teacher-details` | teachers.details | 取得教師明細列表 |
| POST | `/teacher-details` | teachers.edit | 新增教師明細 |
| PUT | `/teacher-details/{detail_id}` | teachers.edit | 更新教師明細 |
| DELETE | `/teacher-details/{detail_id}` | teachers.edit | 刪除教師明細（軟刪除） |
| POST | `/teacher-details/{detail_id}/upload-url` | teachers.edit | 取得明細檔案 signed upload URL |
| POST | `/teacher-details/{detail_id}/confirm-upload` | teachers.edit | 確認明細檔案上傳完成 |
| GET | `/teacher-details/{detail_id}/download-url` | teachers.details | 取得明細檔案 signed download URL |

## Teacher Bonus (`/api/v1/teacher-bonus`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/teacher-bonus` | teachers.bonus | 取得教師獎金列表 |
| GET | `/teacher-bonus/{bonus_id}` | teachers.bonus | 取得單筆教師獎金 |
| POST | `/teacher-bonus` | teachers.bonus | 新增教師獎金紀錄 |
| PUT | `/teacher-bonus/{bonus_id}` | teachers.bonus | 更新教師獎金紀錄 |
| DELETE | `/teacher-bonus/{bonus_id}` | teachers.bonus | 刪除教師獎金紀錄（軟刪除） |
| GET | `/teacher-bonus/options/teachers` | teachers.bonus | 取得教師下拉選項 |

## Teacher Slots (`/api/v1/teacher-slots`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/teacher-slots` | teachers.slots | 取得教師時段列表 |
| GET | `/teacher-slots/options/teachers` | teachers.slots | 取得教師下拉選單 |
| GET | `/teacher-slots/my-contracts` | teachers.slots | 取得當前教師的合約 |
| GET | `/teacher-slots/{slot_id}` | teachers.slots | 取得單一教師時段 |
| POST | `/teacher-slots` | teachers.slots | 建立教師時段 |
| POST | `/teacher-slots/batch` | teachers.slots | 批次建立教師時段（週期性） |
| DELETE | `/teacher-slots/batch` | teachers.slots | 批次刪除教師時段 |
| PUT | `/teacher-slots/batch` | teachers.slots | 批次更新教師時段 |
| POST | `/teacher-slots/batch-by-ids/delete` | teachers.slots | 根據 ID 批次刪除教師時段 |
| POST | `/teacher-slots/batch-by-ids/update` | teachers.slots | 根據 ID 批次更新教師時段 |
| PUT | `/teacher-slots/{slot_id}` | teachers.slots | 更新教師時段 |
| DELETE | `/teacher-slots/{slot_id}` | teachers.slots | 刪除教師時段（軟刪除） |

---

## Bookings (`/api/v1/bookings`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/bookings` | bookings.list | 取得預約列表 |
| GET | `/bookings/slot-availability/{teacher_slot_id}` | bookings.list | 取得時段可用狀態 |
| GET | `/bookings/my-student-info` | bookings.list | 取得當前學生資訊 |
| GET | `/bookings/my-contracts` | bookings.list | 取得當前學生的合約 |
| GET | `/bookings/{booking_id}` | bookings.list | 取得單一預約 |
| POST | `/bookings` | bookings.create | 建立預約 |
| POST | `/bookings/batch` | bookings.create | 批次建立預約 |
| PUT | `/bookings/batch` | bookings.edit | 批次更新預約狀態 |
| PUT | `/bookings/{booking_id}` | bookings.edit | 更新預約 |
| DELETE | `/bookings/batch` | bookings.edit | 批次刪除預約（軟刪除） |
| DELETE | `/bookings/{booking_id}` | bookings.edit | 刪除預約（軟刪除） |
| POST | `/bookings/batch-by-ids/update` | bookings.edit | 根據 ID 批次更新預約 |
| POST | `/bookings/batch-by-ids/delete` | bookings.edit | 根據 ID 批次刪除預約 |

### Bookings Options (下拉選單)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/bookings/options/students` | bookings.list | 取得學生下拉選單 |
| GET | `/bookings/options/teachers` | bookings.list | 取得教師下拉選單 |
| GET | `/bookings/options/overlapping-courses` | bookings.list | 取得重疊課程選單 |
| GET | `/bookings/options/courses` | bookings.list | 取得課程下拉選單 |
| GET | `/bookings/options/student-contracts/{student_id}` | bookings.list | 取得學生合約下拉選單 |
| GET | `/bookings/options/substitute-teachers` | bookings.list | 取得代課教師選單 |
| GET | `/bookings/options/teacher-contracts/{teacher_id}` | bookings.list | 取得教師合約下拉選單 |
| GET | `/bookings/options/teacher-slots/{teacher_id}` | bookings.list | 取得教師可用時段選單 |

## Leave Records (`/api/v1/leave-records`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| POST | `/leave-records` | bookings.list | 建立請假申請 |
| GET | `/leave-records` | bookings.list | 取得請假紀錄列表 |
| GET | `/leave-records/{leave_id}` | bookings.list | 取得單筆請假紀錄 |
| POST | `/leave-records/{leave_id}/approve` | bookings.edit | 核准請假 |
| POST | `/leave-records/{leave_id}/reject` | bookings.edit | 駁回請假 |
| POST | `/leave-records/{leave_id}/cancel` | bookings.list | 撤回請假申請 |

---

## Employees (`/api/v1/employees`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/employees/roles` | employees.list | 取得可指定的角色列表 |
| GET | `/employees` | employees.list | 取得員工列表 |
| GET | `/employees/{employee_id}` | employees.list | 取得單一員工 |
| POST | `/employees` | employees.create | 建立員工 |
| PUT | `/employees/{employee_id}` | employees.edit | 更新員工 |
| DELETE | `/employees/{employee_id}` | employees.delete | 刪除員工（軟刪除） |

## Users (`/api/v1/users`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/users/profile` | get_current_user | 取得當前用戶完整資料 |
| GET | `/users/` | employees.list | 列出所有帳號 |
| PUT | `/users/{user_id}` | employees.edit | 更新帳號角色/狀態 |
| DELETE | `/users/{user_id}` | employees.delete | 停用帳號 |

## Invites (`/api/v1/invites`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| POST | `/invites/generate` | require_staff | 產生邀請連結 |
| POST | `/invites/accept` | None | 接受邀請建立帳號 |

---

## Page Permissions (`/api/v1/`)

### Pages

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/pages` | permissions.pages | 取得頁面列表 |
| POST | `/pages` | permissions.pages | 建立頁面 |
| PUT | `/pages/{page_id}` | permissions.pages | 更新頁面 |
| DELETE | `/pages/{page_id}` | permissions.pages | 停用頁面 |

### Roles

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/roles` | permissions.roles | 取得所有角色 |
| POST | `/roles` | permissions.roles | 建立新角色 |
| PUT | `/roles/{role_id}` | permissions.roles | 更新角色 |
| DELETE | `/roles/{role_id}` | permissions.roles | 刪除角色 |
| GET | `/role-pages` | permissions.roles | 查看角色預設頁面 |
| PUT | `/role-pages` | permissions.roles | 批次設定角色頁面 |

### User Overrides

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/user-pages/{user_id}` | permissions.users | 查看用戶頁面覆寫 |
| PUT | `/user-pages/{user_id}` | permissions.users | 批次設定用戶頁面覆寫 |
| GET | `/permissions/me` | get_current_user | 取得當前用戶有效權限 |

---

## Notifications (`/api/v1/notifications`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/notifications/preferences` | get_current_user | 取得我的通知偏好 |
| PUT | `/notifications/preferences` | get_current_user | 更新我的通知偏好 |

### LINE Notifications (`/api/v1/notifications/line`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/notifications/line/preferences` | get_current_user | 取得 LINE 通知偏好 |
| PUT | `/notifications/line/preferences` | get_current_user | 更新 LINE 通知偏好 |
| POST | `/notifications/line/test` | get_current_user | 發送測試通知 |
| GET | `/notifications/line/history` | get_current_user | 取得通知歷史 |
| GET | `/notifications/line/bindings` | require_staff | 列出 LINE 綁定用戶 |
| POST | `/notifications/line/send` | require_staff | 發送 LINE 訊息給指定用戶 |

---

## Google Drive (`/api/v1/google-drive`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/google-drive/oauth/authorize` | require_staff | 取得 Google OAuth 授權 URL |
| GET | `/google-drive/oauth/callback` | None | Google OAuth callback |
| GET | `/google-drive/oauth/status` | get_current_user | 查詢 Google Drive 綁定狀態 |
| DELETE | `/google-drive/oauth/unlink` | require_staff | 解除 Google Drive 綁定 |
| PUT | `/google-drive/folder` | require_staff | 設定上傳目標資料夾 |

## Zoom (`/api/v1/zoom`)

| Method | Path | 權限 | 說明 |
|--------|------|------|------|
| GET | `/zoom/accounts` | require_staff | 取得 Zoom 帳號列表 |
| POST | `/zoom/accounts` | require_staff | 建立 Zoom 帳號 |
| PUT | `/zoom/accounts/{account_id}` | require_staff | 更新 Zoom 帳號 |
| DELETE | `/zoom/accounts/{account_id}` | require_staff | 刪除 Zoom 帳號 |
| POST | `/zoom/accounts/{account_id}/test` | require_staff | 測試 Zoom 帳號連線 |
| POST | `/zoom/meetings/create` | bookings.edit | 為預約建立 Zoom 會議 |
| GET | `/zoom/meetings` | bookings.list | 取得 Zoom 會議日誌列表 |
| GET | `/zoom/meetings/{booking_id}` | bookings.list | 取得單一 Zoom 會議日誌 |
| POST | `/zoom/meetings/{booking_id}/fetch-recording` | bookings.edit | 拉取 Zoom 錄影並上傳 |
| GET | `/zoom/oauth/authorize` | require_staff | 取得 Zoom OAuth 授權 URL |
| GET | `/zoom/oauth/callback` | None | Zoom OAuth callback |
| DELETE | `/zoom/oauth/unlink` | require_staff | 解除 Zoom 帳號綁定 |
| GET | `/zoom/oauth/status` | get_current_user | 查詢 Zoom 綁定狀態 |
| POST | `/zoom/webhook` | None | Zoom webhook 端點 |
| POST | `/zoom/internal/download-token` | None | 取得 Zoom 錄影下載 token（內部） |
| POST | `/zoom/recording-callback` | None | Zoom 錄影完成回調 |
