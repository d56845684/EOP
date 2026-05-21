# Error code 對照表

共 **479** 個 error code（自動產生自 `backend/app/core/error_codes.py`）。

## 編碼規則

6 位數 = `<3-digit HTTP status><1-digit domain><2-digit seq>`

- 例：`400113` = 400 Bad Request、Domain 1 (BOOKING)、序號 13 = `BOOKING_DURATION_NOT_COURSE_MULTIPLE`

### Domain 對照

| Digit | Name | 涵蓋檔案 |
|-------|------|-----------|
| 1 | BOOKING | bookings / leave_records / lesson_notes / substitute_details |
| 2 | CONTRACT | student_contracts / teacher_contracts / teacher_bonus / teacher_details |
| 3 | TEACHER | teacher_slots / teachers |
| 4 | STUDENT | students / student_courses / student_teacher_preferences |
| 5 | EMPLOYEE | employees / page_permissions / invites / users |
| 6 | COURSE | courses |
| 7 | EXTERNAL | zoom / google_drive / line_auth |
| 9 | SYSTEM | alerts / auth / 通用 |

---

## Domain 0 — GENERIC

共 26 個 code

### 400 Bad Request

| Code | Name | Description |
|------|------|-------------|
| `400001` | `VALIDATION_ERROR` |  |
| `400002` | `DUPLICATE_ENTRY` |  |
| `400003` | `NO_UPDATE_DATA` |  |
| `400004` | `INVALID_STATE` |  |
| `400005` | `INVALID_FILE` |  |
| `400006` | `QUOTA_EXCEEDED` |  |
| `400007` | `WRONG_PASSWORD` |  |

### 401 Unauthorized

| Code | Name | Description |
|------|------|-------------|
| `401001` | `AUTH_ERROR` |  |
| `401002` | `AUTH_TOKEN_EXPIRED` |  |
| `401003` | `AUTH_TOKEN_INVALID` |  |
| `401004` | `AUTH_SESSION_EXPIRED` |  |
| `401005` | `AUTH_IDLE_TIMEOUT` |  |
| `401006` | `AUTH_SESSION_REPLACED` |  |
| `401007` | `AUTH_LOGIN_FAILED` |  |
| `401008` | `AUTH_API_KEY_INVALID` |  |

### 403 Forbidden

| Code | Name | Description |
|------|------|-------------|
| `403001` | `FORBIDDEN` |  |
| `403002` | `FORBIDDEN_ROLE` |  |
| `403003` | `FORBIDDEN_OWNER` |  |
| `403004` | `FORBIDDEN_PROTECTED` |  |
| `403005` | `FORBIDDEN_PAGE` |  |

### 404 Not Found

| Code | Name | Description |
|------|------|-------------|
| `404001` | `NOT_FOUND` |  |

### 409 Conflict

| Code | Name | Description |
|------|------|-------------|
| `409001` | `CONFLICT` |  |

### 422 Unprocessable Entity

| Code | Name | Description |
|------|------|-------------|
| `422001` | `REQUEST_VALIDATION_ERROR` | Pydantic body/query/path 驗證失敗 |

### 429 Too Many Requests

| Code | Name | Description |
|------|------|-------------|
| `429001` | `RATE_LIMITED` |  |

### 500 Internal Server Error

| Code | Name | Description |
|------|------|-------------|
| `500001` | `INTERNAL_ERROR` |  |

### 503 Service Unavailable

| Code | Name | Description |
|------|------|-------------|
| `503001` | `SERVICE_UNAVAILABLE` |  |

---

## Domain 1 — BOOKING

共 108 個 code

### 400 Bad Request

| Code | Name | Description |
|------|------|-------------|
| `400100` | `BOOKING_INVALID` | generic booking 400 |
| `400101` | `BOOKING_STUDENT_NOT_FOUND_OR_DISABLED` | 學生不存在或已停用 |
| `400102` | `BOOKING_TEACHER_NOT_FOUND_OR_DISABLED` | 教師不存在或已停用 |
| `400103` | `BOOKING_COURSE_NOT_FOUND_OR_DISABLED` | 課程不存在或已停用 |
| `400104` | `BOOKING_STUDENT_COURSE_NOT_ENROLLED` | 學生未選修此課程 |
| `400105` | `BOOKING_TEACHER_NOT_QUALIFIED` | 教師無此課程的授課資格 |
| `400106` | `BOOKING_STUDENT_CONTRACT_NOT_FOUND` | 學生合約不存在 |
| `400107` | `BOOKING_STUDENT_CONTRACT_LESSONS_INSUFFICIENT` | 學生合約剩餘堂數不足 |
| `400108` | `BOOKING_FORMAL_STUDENT_REQUIRES_CONTRACT` | 正式學生必須提供學生合約 |
| `400109` | `BOOKING_TEACHER_CONTRACT_NOT_FOUND` | 教師合約不存在 |
| `400110` | `BOOKING_TEACHER_SLOT_NOT_FOUND` | 教師時段不存在 (400 路徑) |
| `400111` | `BOOKING_TEACHER_SLOT_UNAVAILABLE` | 教師時段不可用 |
| `400112` | `BOOKING_DATE_SLOT_MISMATCH` | 預約日期與時段日期不符 |
| `400113` | `BOOKING_DURATION_NOT_COURSE_MULTIPLE` | 預約時長必須是課程時長倍數 |
| `400114` | `BOOKING_TIME_OUT_OF_SLOT_RANGE` | 預約時間超出時段範圍 |
| `400115` | `BOOKING_END_TIME_NOT_30MIN_BOUNDARY` | 結束時間必須在 30 分鐘邊界上 |
| `400116` | `BOOKING_END_TIME_BEFORE_START` | 新結束時間必須晚於開始時間 |
| `400117` | `BOOKING_SHORTEN_ONLY` | 只允許縮短預約 |
| `400118` | `BOOKING_SHORTENED_DURATION_NOT_MULTIPLE` | 縮短後時長必須是課程時長倍數 |
| `400119` | `BOOKING_TEACHER_NOT_IN_STUDENT_PREFERENCES` | 此教師不在學生的偏好可預約教師範圍內 |
| `400120` | `BOOKING_SLOT_NO_VALID_CONTRACT` | 此時段無有效教師有效合約 |
| `400121` | `BOOKING_TIME_NO_AVAILABLE_SLOT` | 找不到包含預約時間的可用時段 |
| `400122` | `BOOKING_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400123` | `BOOKING_COMPLETED_NOT_EDITABLE` | 已完成的預約無法修改 |
| `400124` | `BOOKING_CANCELLED_NOT_EDITABLE` | 已取消的預約無法修改 |
| `400125` | `BOOKING_ONLY_PENDING_CAN_CONFIRM` | 只有待確認的預約可以確認 |
| `400126` | `BOOKING_ONLY_PENDING_CAN_CANCEL` | 只有待確認的預約可以取消（已確認走請假） |
| `400127` | `BOOKING_ONLY_PENDING_OR_CANCELLED_CAN_DELETE` | 只有待確認或已取消可刪 |
| `400128` | `BOOKING_COURSE_ID_REQUIRED` | 請提供課程 ID |
| `400129` | `BOOKING_BOOKING_ID_REQUIRED` | 請提供預約 ID |
| `400130` | `BOOKING_STUDENT_NOT_EXIST` | 學生不存在 (不同於上面的"或已停用") |
| `400131` | `BOOKING_LEAVE_INITIATOR_TYPE_REQUIRED` | 員工代申請須指定 initiator_type |
| `400132` | `BOOKING_LEAVE_PENDING_ALREADY_EXISTS` | 此預約已有待審核的請假申請 |
| `400133` | `BOOKING_LEAVE_BOOKING_NOT_CONFIRMED` | 只有已確認的預約可以請假 |
| `400134` | `BOOKING_LEAVE_ONLY_PENDING_CAN_WITHDRAW` | 只有待審核的請假可以撤回 |
| `400135` | `BOOKING_LEAVE_ONLY_PENDING_CAN_APPROVE` | 只有待審核的請假可以核准 |
| `400136` | `BOOKING_LEAVE_ONLY_PENDING_CAN_REJECT` | 只有待審核的請假可以駁回 |
| `400137` | `BOOKING_LEAVE_NO_STUDENT_CONTRACT` | 此預約查無對應的學生合約 |
| `400138` | `BOOKING_LEAVE_EMERGENCY_QUOTA_EXCEEDED` | 緊急請假額度已用完 |
| `400139` | `BOOKING_LEAVE_TOO_LATE` | 課程開始前 30 分鐘內無法請假 |
| `400140` | `BOOKING_LEAVE_RELATED_BOOKING_NOT_EXIST` | 關聯的預約不存在（與 BOOKING_NOT_FOUND 不同情境） |
| `400141` | `BOOKING_NOTE_INVALID_STATUS_UPLOAD` | 預約狀態 X 無法上傳筆記 |
| `400142` | `BOOKING_NOTE_INVALID_STATUS_CONFIRM` | 預約狀態 X 無法確認筆記 |
| `400143` | `BOOKING_SUB_TEACHER_SELF_NOT_ALLOWED` | 不能指派原教師自己為代課 |
| `400144` | `BOOKING_SUB_TEACHER_NOT_FOUND` | 代課教師不存在或未啟用 |
| `400145` | `BOOKING_SUB_TEACHER_CONTRACT_INVALID` | 代課教師合約不存在或非有效狀態 |
| `400146` | `BOOKING_SUB_TEACHER_CONTRACT_NO_COURSE` | 代課教師合約未包含此課程 |
| `400147` | `BOOKING_SUB_TEACHER_NO_SLOT` | 代課教師沒有可用的預約時段 |
| `400148` | `BOOKING_SUB_BOOKING_NOT_CONFIRMED` | 只有已確認的預約可以指派代課 |
| `400149` | `BOOKING_SUB_ALREADY_ASSIGNED` | 此預約已有代課紀錄 |

### 403 Forbidden

| Code | Name | Description |
|------|------|-------------|
| `403101` | `BOOKING_FORBIDDEN_NOT_OWN_CANCEL` | 只能取消自己的預約 |
| `403102` | `BOOKING_FORBIDDEN_STUDENT_NOT_OWN` | 學生只能為自己預約 |
| `403103` | `BOOKING_FORBIDDEN_NO_VIEW` | 無權查看此預約 |
| `403104` | `BOOKING_FORBIDDEN_NO_CREATE` | 無權建立預約 |
| `403105` | `BOOKING_FORBIDDEN_STUDENT_NO_UPDATE` | 學生無權更新預約 |
| `403106` | `BOOKING_FORBIDDEN_TEACHER_CONFIRM_ONLY` | 教師僅可將預約狀態更新為已確認 |
| `403107` | `BOOKING_FORBIDDEN_TEACHER_OWN_ONLY` | 教師只能更新自己的預約 |
| `403108` | `BOOKING_FORBIDDEN_NO_STUDENT_INFO` | 無法取得學生資料 |
| `403109` | `BOOKING_LEAVE_FORBIDDEN_APPROVE` | 僅限員工核准請假 |
| `403110` | `BOOKING_LEAVE_FORBIDDEN_REJECT` | 僅限員工駁回請假 |
| `403111` | `BOOKING_LEAVE_FORBIDDEN_NOT_INITIATOR` | 只有發起者可以撤回請假 |
| `403112` | `BOOKING_LEAVE_FORBIDDEN_STUDENT_NOT_OWN` | 學生只能為自己的預約請假 |
| `403113` | `BOOKING_LEAVE_FORBIDDEN_TEACHER_NOT_OWN` | 教師只能為自己的預約請假 |
| `403114` | `BOOKING_LEAVE_FORBIDDEN_CREATE` | 無權建立請假申請 |
| `403115` | `BOOKING_LEAVE_FORBIDDEN_WITHDRAW` | 無權撤回請假 |
| `403116` | `BOOKING_LEAVE_FORBIDDEN_VIEW` | 無權查看此請假紀錄 |
| `403117` | `BOOKING_NOTE_FORBIDDEN_CONFIRM` | 只有該預約的學生或員工可以確認 |
| `403118` | `BOOKING_NOTE_FORBIDDEN_UPLOAD` | 只有該預約的老師可以上傳 |
| `403119` | `BOOKING_NOTE_FORBIDDEN_UPDATE` | 只有該預約的老師可以修改 |
| `403120` | `BOOKING_NOTE_FORBIDDEN_VIEW` | 無權限查看此筆記 |
| `403121` | `BOOKING_SUB_FORBIDDEN_CANCEL` | 僅限員工取消代課 |
| `403122` | `BOOKING_SUB_FORBIDDEN_ASSIGN` | 僅限員工指派代課 |
| `403123` | `BOOKING_SUB_FORBIDDEN_VIEW` | 僅限教師查看 |

### 404 Not Found

| Code | Name | Description |
|------|------|-------------|
| `404101` | `BOOKING_NOT_FOUND` | 預約不存在 |
| `404102` | `BOOKING_SLOT_NOT_FOUND_404` | 教師時段不存在 (404 路徑) |
| `404103` | `BOOKING_LEAVE_NOT_FOUND` | 請假紀錄不存在 |
| `404104` | `BOOKING_NOTE_NOT_UPLOADED` | 尚未上傳課後筆記 |
| `404105` | `BOOKING_NOTE_NOT_UPLOADED_FOR_UPDATE` | 尚未上傳課後筆記，無法修改 |
| `404106` | `BOOKING_SUB_NOT_FOUND` | 代課紀錄不存在 |

### 409 Conflict

| Code | Name | Description |
|------|------|-------------|
| `409101` | `BOOKING_TIME_CONFLICT` | 預約時間衝突 |
| `409102` | `BOOKING_ZOOM_POOL_EXHAUSTED` | Zoom 帳號池當下無可用 |
| `409103` | `BOOKING_NOTE_ALREADY_UPLOADED` | 此預約已上傳過筆記 |
| `409104` | `BOOKING_NOTE_ALREADY_CONFIRMED` | 筆記已被確認過 |
| `409105` | `BOOKING_NOTE_CONFIRMED_NOT_EDITABLE` | 筆記已被確認，無法修改 |
| `409106` | `BOOKING_SUB_TIME_CONFLICT_OTHER_SUB` | 代課教師已有代課安排 |
| `409107` | `BOOKING_SUB_TIME_CONFLICT_OWN_BOOKING` | 代課教師已有預約 |

### 500 Internal Server Error

| Code | Name | Description |
|------|------|-------------|
| `500101` | `BOOKING_INTERNAL` | generic booking 500 |
| `500102` | `BOOKING_CREATE_FAILED` | 建立預約失敗 |
| `500103` | `BOOKING_UPDATE_FAILED` | 更新預約失敗 |
| `500104` | `BOOKING_DELETE_FAILED` | 刪除預約失敗 |
| `500105` | `BOOKING_CANCEL_FAILED` | 取消預約失敗 |
| `500106` | `BOOKING_BATCH_CREATE_FAILED` | 批次建立失敗 |
| `500107` | `BOOKING_BATCH_UPDATE_FAILED` | 批次更新失敗 |
| `500108` | `BOOKING_BATCH_DELETE_FAILED` | 批次刪除失敗 |
| `500109` | `BOOKING_LIST_FAILED` | 取得預約列表失敗 |
| `500110` | `BOOKING_GET_FAILED` | 取得預約失敗 |
| `500111` | `BOOKING_SLOT_AVAILABILITY_FAILED` | 取得時段可用狀態失敗 |
| `500112` | `BOOKING_LEAVE_LIST_FAILED` | 取得請假紀錄失敗 |
| `500113` | `BOOKING_LEAVE_CREATE_FAILED` | 建立請假申請失敗 |
| `500114` | `BOOKING_LEAVE_WITHDRAW_FAILED` | 撤回請假失敗 |
| `500115` | `BOOKING_LEAVE_APPROVE_FAILED` | 核准請假失敗 |
| `500116` | `BOOKING_LEAVE_REJECT_FAILED` | 駁回請假失敗 |
| `500117` | `BOOKING_SUB_LIST_FAILED` | 取得代課紀錄失敗 |
| `500118` | `BOOKING_SUB_MY_LIST_FAILED` | 取得我的代課紀錄失敗 |
| `500119` | `BOOKING_SUB_CANCEL_FAILED` | 取消代課失敗 |
| `500120` | `BOOKING_SUB_CREATE_FAILED` | 建立代課紀錄失敗 |
| `500121` | `BOOKING_SUB_ASSIGN_FAILED` | 指派代課失敗 |

### 502 Bad Gateway

| Code | Name | Description |
|------|------|-------------|
| `502101` | `BOOKING_ZOOM_SERVICE_UNAVAILABLE` | Zoom 服務目前無法建立會議 |

---

## Domain 2 — CONTRACT

共 134 個 code

### 400 Bad Request

| Code | Name | Description |
|------|------|-------------|
| `400201` | `STUDENT_CONTRACT_FILE_FORMAT_INVALID` | 不支援的檔案格式 |
| `400202` | `STUDENT_CONTRACT_ADDENDUM_ONLY_PENDING_EDIT` | 只有待生效附約才可修改 |
| `400203` | `STUDENT_CONTRACT_ADDENDUM_REQUIRES_ACTIVE` | 只有生效中合約才能建附約 |
| `400204` | `STUDENT_CONTRACT_STUDENT_NOT_FOUND` | 學生不存在 |
| `400205` | `STUDENT_CONTRACT_LEAVE_QUOTA_EXCEEDED` | 已達請假上限 |
| `400206` | `STUDENT_CONTRACT_ADDENDUM_END_INVALID` | 新結束日期須 > 原結束 |
| `400207` | `STUDENT_CONTRACT_ADDENDUM_END_BEFORE_PARENT` | 新結束日期須 > 母約結束 |
| `400208` | `STUDENT_CONTRACT_FILE_NOT_UPLOADED` | 檔案尚未上傳至 S3 |
| `400209` | `STUDENT_CONTRACT_COURSE_NOT_ENROLLED` | 此學生尚未選修此課程 |
| `400210` | `STUDENT_CONTRACT_PARENT_NOT_ACTIVE` | 母約狀態不是生效中 |
| `400211` | `STUDENT_CONTRACT_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400212` | `STUDENT_CONTRACT_INVALID_FILE_PATH` | 無效的檔案路徑格式 |
| `400213` | `STUDENT_CONTRACT_TRIAL_ONLY_VIA_CONVERT` | 試上合約只能透過轉正流程啟用 |
| `400214` | `STUDENT_CONTRACT_DUPLICATE_ACTIVE` | 該學生已有生效中合約 |
| `400215` | `STUDENT_CONTRACT_COURSE_NOT_FOUND` | 課程不存在 |
| `400216` | `TEACHER_CONTRACT_WORK_SCHEDULE_OVERLAP` | 工作時段有重疊 |
| `400217` | `TEACHER_CONTRACT_ADDENDUM_ONLY_PENDING_EDIT` | 只有待生效附約可修改 |
| `400218` | `TEACHER_CONTRACT_ADDENDUM_REQUIRES_ACTIVE` | 只有生效中合約才能建附約 |
| `400219` | `TEACHER_CONTRACT_TEACHER_NOT_FOUND` | 教師不存在 |
| `400220` | `TEACHER_CONTRACT_ADDENDUM_END_INVALID` | 新結束日期須 > 原結束 |
| `400221` | `TEACHER_CONTRACT_ADDENDUM_END_BEFORE_PARENT` | 新結束日期須 > 母約結束 |
| `400222` | `TEACHER_CONTRACT_FILE_NOT_UPLOADED` | 檔案尚未上傳至 S3 |
| `400223` | `TEACHER_CONTRACT_PARENT_NOT_ACTIVE` | 母約狀態不是生效中 |
| `400224` | `TEACHER_CONTRACT_OVERTIME_DUPLICATE` | 每份合約只能設一筆加班費 |
| `400225` | `TEACHER_CONTRACT_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400226` | `TEACHER_CONTRACT_INVALID_FILE_PATH` | 無效的檔案路徑格式 |
| `400227` | `TEACHER_CONTRACT_DUPLICATE_ACTIVE` | 該教師已有生效中合約 |
| `400228` | `TEACHER_CONTRACT_COURSE_NOT_FOUND` | 課程不存在 |
| `400229` | `TEACHER_BONUS_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400230` | `TEACHER_DETAIL_FILE_FORMAT_INVALID` | 不支援的檔案格式 |
| `400231` | `TEACHER_DETAIL_FILE_NOT_UPLOADED` | 檔案尚未上傳至 S3 |
| `400232` | `TEACHER_DETAIL_NO_UPDATE_DATA` | 沒有要更新的資料 |

### 403 Forbidden

| Code | Name | Description |
|------|------|-------------|
| `403201` | `STUDENT_CONTRACT_FORBIDDEN_TEACHER_DOWNLOAD` | 教師無權下載學生合約 |
| `403202` | `STUDENT_CONTRACT_FORBIDDEN_TEACHER_VIEW` | 教師無權查看學生合約 |
| `403203` | `STUDENT_CONTRACT_FORBIDDEN_TEACHER_VIEW_DETAIL` | 教師無權查看學生合約明細 |
| `403204` | `STUDENT_CONTRACT_FORBIDDEN_TEACHER_VIEW_LEAVE` | 教師無權查看學生合約請假紀錄 |
| `403205` | `STUDENT_CONTRACT_FORBIDDEN_DOWNLOAD` | 無權下載此合約 |
| `403206` | `STUDENT_CONTRACT_FORBIDDEN_VIEW` | 無權查看此合約 |
| `403207` | `STUDENT_CONTRACT_FORBIDDEN_VIEW_DETAIL` | 無權查看此合約明細 |
| `403208` | `STUDENT_CONTRACT_FORBIDDEN_VIEW_LEAVE` | 無權查看此合約請假紀錄 |
| `403209` | `TEACHER_CONTRACT_FORBIDDEN_STUDENT_DOWNLOAD` | 學生無權下載教師合約 |
| `403210` | `TEACHER_CONTRACT_FORBIDDEN_STUDENT_VIEW` | 學生無權查看教師合約 |
| `403211` | `TEACHER_CONTRACT_FORBIDDEN_STUDENT_VIEW_SCHEDULE` | 學生無權查看教師合約工作時段 |
| `403212` | `TEACHER_CONTRACT_FORBIDDEN_STUDENT_VIEW_DETAIL` | 學生無權查看教師合約明細 |
| `403213` | `TEACHER_CONTRACT_FORBIDDEN_DOWNLOAD` | 無權下載此合約 |
| `403214` | `TEACHER_CONTRACT_FORBIDDEN_VIEW` | 無權查看此合約 |
| `403215` | `TEACHER_CONTRACT_FORBIDDEN_VIEW_SCHEDULE` | 無權查看此合約工作時段 |
| `403216` | `TEACHER_CONTRACT_FORBIDDEN_VIEW_DETAIL` | 無權查看此合約明細 |
| `403217` | `TEACHER_BONUS_FORBIDDEN_VIEW` | 無權查看此獎金紀錄 |
| `403218` | `TEACHER_DETAIL_FORBIDDEN_DOWNLOAD` | 無權下載此文件 |
| `403219` | `TEACHER_DETAIL_FORBIDDEN_VIEW_OTHER` | 無權查看其他教師的明細 |

### 404 Not Found

| Code | Name | Description |
|------|------|-------------|
| `404201` | `STUDENT_CONTRACT_NOT_FOUND` | 學生合約不存在 |
| `404202` | `STUDENT_CONTRACT_DETAIL_NOT_FOUND` | 合約明細不存在 |
| `404203` | `STUDENT_CONTRACT_FILE_NOT_UPLOADED_404` | 此合約尚未上傳檔案 |
| `404204` | `STUDENT_CONTRACT_ADDENDUM_FILE_NOT_UPLOADED` |  |
| `404205` | `STUDENT_CONTRACT_ADDENDUM_PDF_FAILED_404` | 產生附約 PDF 失敗 (404 路徑) |
| `404206` | `STUDENT_CONTRACT_LEAVE_NOT_FOUND` | 請假紀錄不存在 |
| `404207` | `STUDENT_CONTRACT_ADDENDUM_NOT_FOUND` | 附約不存在 |
| `404208` | `TEACHER_CONTRACT_NOT_FOUND` | 教師合約不存在 |
| `404209` | `TEACHER_CONTRACT_DETAIL_NOT_FOUND` | 合約明細不存在 |
| `404210` | `TEACHER_CONTRACT_FILE_NOT_UPLOADED_404` | 此合約尚未上傳檔案 |
| `404211` | `TEACHER_CONTRACT_ADDENDUM_FILE_NOT_UPLOADED` | 此附約尚未上傳檔案 |
| `404212` | `TEACHER_CONTRACT_ADDENDUM_PDF_FAILED_404` | 產生附約 PDF 失敗 (404 路徑) |
| `404213` | `TEACHER_CONTRACT_ADDENDUM_NOT_FOUND` | 附約不存在 |
| `404214` | `TEACHER_BONUS_NOT_FOUND` | 獎金紀錄不存在 |
| `404215` | `TEACHER_BONUS_TEACHER_NOT_FOUND` | 教師不存在 |
| `404216` | `TEACHER_DETAIL_TEACHER_NOT_FOUND` | 教師不存在 |
| `404217` | `TEACHER_DETAIL_NOT_FOUND` | 教師明細不存在 |
| `404218` | `TEACHER_DETAIL_FILE_NOT_UPLOADED_404` | 此明細尚無上傳檔案 |

### 500 Internal Server Error

| Code | Name | Description |
|------|------|-------------|
| `500201` | `STUDENT_CONTRACT_INTERNAL` | 通用 str(e) |
| `500202` | `STUDENT_CONTRACT_DETAIL_DELETE_FAILED` | 刪除合約明細失敗 |
| `500203` | `STUDENT_CONTRACT_DELETE_FAILED` | 刪除學生合約失敗 |
| `500204` | `STUDENT_CONTRACT_LEAVE_DELETE_FAILED` | 刪除請假紀錄失敗 |
| `500205` | `STUDENT_CONTRACT_ADDENDUM_DELETE_FAILED` | 刪除附約失敗 |
| `500206` | `STUDENT_CONTRACT_DOWNLOAD_URL_FAILED` | 取得下載連結失敗 |
| `500207` | `STUDENT_CONTRACT_DETAIL_LIST_FAILED` | 取得合約明細失敗 |
| `500208` | `STUDENT_CONTRACT_LIST_FAILED` | 取得學生合約列表失敗 |
| `500209` | `STUDENT_CONTRACT_GET_FAILED` | 取得學生合約失敗 |
| `500210` | `STUDENT_CONTRACT_LEAVE_LIST_FAILED` | 取得請假紀錄失敗 |
| `500211` | `STUDENT_CONTRACT_ADDENDUM_LIST_FAILED` | 取得附約列表失敗 |
| `500212` | `STUDENT_CONTRACT_ADDENDUM_GET_FAILED` | 取得附約失敗 |
| `500213` | `STUDENT_CONTRACT_CREATE_FAILED` | 建立學生合約失敗 |
| `500214` | `STUDENT_CONTRACT_ADDENDUM_CREATE_FAILED` | 建立附約失敗 |
| `500215` | `STUDENT_CONTRACT_DETAIL_CREATE_FAILED` | 新增合約明細失敗 |
| `500216` | `STUDENT_CONTRACT_LEAVE_CREATE_FAILED` | 新增請假紀錄失敗 |
| `500217` | `STUDENT_CONTRACT_DETAIL_UPDATE_FAILED` | 更新合約明細失敗 |
| `500218` | `STUDENT_CONTRACT_UPDATE_INFO_FAILED` | 更新合約資訊失敗 |
| `500219` | `STUDENT_CONTRACT_UPDATE_FAILED` | 更新學生合約失敗 |
| `500220` | `STUDENT_CONTRACT_ADDENDUM_UPDATE_FAILED` | 更新附約失敗 |
| `500221` | `STUDENT_CONTRACT_UPLOAD_URL_FAILED` | 產生上傳連結失敗 |
| `500222` | `STUDENT_CONTRACT_GENERATE_DOWNLOAD_URL_FAILED` | 產生下載連結失敗 |
| `500223` | `STUDENT_CONTRACT_DOCX_FAILED` | 產生合約 DOCX 失敗 |
| `500224` | `STUDENT_CONTRACT_PDF_FAILED` | 產生合約 PDF 失敗 |
| `500225` | `STUDENT_CONTRACT_ADDENDUM_PDF_FAILED_500` | 產生附約 PDF 失敗 |
| `500226` | `STUDENT_CONTRACT_UPLOAD_CONFIRM_FAILED` | 確認上傳失敗 |
| `500227` | `TEACHER_CONTRACT_INTERNAL` | 通用 str(e) |
| `500228` | `TEACHER_CONTRACT_DETAIL_DELETE_FAILED` | 刪除合約明細失敗 |
| `500229` | `TEACHER_CONTRACT_DELETE_FAILED` | 刪除教師合約失敗 |
| `500230` | `TEACHER_CONTRACT_ADDENDUM_DELETE_FAILED` | 刪除附約失敗 |
| `500231` | `TEACHER_CONTRACT_DOWNLOAD_URL_FAILED` | 取得下載連結失敗 |
| `500232` | `TEACHER_CONTRACT_DETAIL_LIST_FAILED` | 取得合約明細失敗 |
| `500233` | `TEACHER_CONTRACT_WORK_SCHEDULE_GET_FAILED` | 取得工作時段失敗 |
| `500234` | `TEACHER_CONTRACT_LIST_FAILED` | 取得教師合約列表失敗 |
| `500235` | `TEACHER_CONTRACT_GET_FAILED` | 取得教師合約失敗 |
| `500236` | `TEACHER_CONTRACT_ADDENDUM_LIST_FAILED` | 取得附約列表失敗 |
| `500237` | `TEACHER_CONTRACT_ADDENDUM_GET_FAILED` | 取得附約失敗 |
| `500238` | `TEACHER_CONTRACT_CREATE_FAILED` | 建立教師合約失敗 |
| `500239` | `TEACHER_CONTRACT_ADDENDUM_CREATE_FAILED` | 建立附約失敗 |
| `500240` | `TEACHER_CONTRACT_DETAIL_CREATE_FAILED` | 新增合約明細失敗 |
| `500241` | `TEACHER_CONTRACT_DETAIL_UPDATE_FAILED` | 更新合約明細失敗 |
| `500242` | `TEACHER_CONTRACT_UPDATE_INFO_FAILED` | 更新合約資訊失敗 |
| `500243` | `TEACHER_CONTRACT_WORK_SCHEDULE_UPDATE_FAILED` | 更新工作時段失敗 |
| `500244` | `TEACHER_CONTRACT_UPDATE_FAILED` | 更新教師合約失敗 |
| `500245` | `TEACHER_CONTRACT_ADDENDUM_UPDATE_FAILED` | 更新附約失敗 |
| `500246` | `TEACHER_CONTRACT_WORK_SCHEDULE_CLEAR_FAILED` | 清除工作時段失敗 |
| `500247` | `TEACHER_CONTRACT_UPLOAD_URL_FAILED` | 產生上傳連結失敗 |
| `500248` | `TEACHER_CONTRACT_GENERATE_DOWNLOAD_URL_FAILED` | 產生下載連結失敗 |
| `500249` | `TEACHER_CONTRACT_PDF_FAILED` | 產生合約 PDF 失敗 |
| `500250` | `TEACHER_CONTRACT_ADDENDUM_PDF_FAILED_500` | 產生附約 PDF 失敗 |
| `500251` | `TEACHER_CONTRACT_UPLOAD_CONFIRM_FAILED` | 確認上傳失敗 |
| `500252` | `TEACHER_BONUS_DELETE_FAILED` | 刪除教師獎金失敗 |
| `500253` | `TEACHER_BONUS_LIST_FAILED` | 取得教師獎金列表失敗 |
| `500254` | `TEACHER_BONUS_GET_FAILED` | 取得教師獎金失敗 |
| `500255` | `TEACHER_BONUS_TEACHER_OPTIONS_FAILED` | 取得教師選項失敗 |
| `500256` | `TEACHER_BONUS_CREATE_FAILED` | 新增教師獎金失敗 |
| `500257` | `TEACHER_BONUS_UPDATE_FAILED` | 更新教師獎金失敗 |
| `500258` | `TEACHER_DETAIL_DELETE_FAILED` | 刪除教師明細失敗 |
| `500259` | `TEACHER_DETAIL_GET_FAILED` | 取得教師明細失敗 |
| `500260` | `TEACHER_DETAIL_CREATE_FAILED` | 新增教師明細失敗 |
| `500261` | `TEACHER_DETAIL_UPDATE_FAILED` | 更新教師明細失敗 |
| `500262` | `TEACHER_DETAIL_FILE_INFO_UPDATE_FAILED` | 更新檔案資訊失敗 |
| `500263` | `TEACHER_DETAIL_UPLOAD_URL_FAILED` | 產生上傳連結失敗 |
| `500264` | `TEACHER_DETAIL_DOWNLOAD_URL_FAILED` | 產生下載連結失敗 |
| `500265` | `TEACHER_DETAIL_UPLOAD_CONFIRM_FAILED` | 確認上傳失敗 |

---

## Domain 3 — TEACHER

共 52 個 code

### 400 Bad Request

| Code | Name | Description |
|------|------|-------------|
| `400301` | `SLOT_TEACHER_NOT_FOUND_OR_DISABLED` | 教師不存在或已停用 |
| `400302` | `SLOT_TEACHER_NO_ACTIVE_CONTRACT` | 教師沒有 active 合約 |
| `400303` | `SLOT_TEACHER_NO_VALID_CONTRACT_UPDATE` | 教師沒有有效合約，無法更新時段合約 |
| `400304` | `SLOT_TEACHER_NO_VALID_CONTRACT_CREATE` | 教師無有效合約，無法建立時段 |
| `400305` | `SLOT_HAS_BOOKING_CANNOT_EDIT` | 有預約的時段無法修改日期或時間 |
| `400306` | `SLOT_HAS_BOOKING_CANNOT_DELETE` | 有預約的時段無法刪除 |
| `400307` | `SLOT_NO_UPDATE_CONTENT` | 沒有指定要更新的內容 |
| `400308` | `SLOT_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400309` | `SLOT_UPDATE_CONTENT_REQUIRED` | 請指定要更新的內容 |
| `400310` | `SLOT_SELECT_SLOTS_TO_DELETE` | 請選擇要刪除的時段 |
| `400311` | `SLOT_SELECT_SLOTS_TO_UPDATE` | 請選擇要更新的時段 |
| `400312` | `SLOT_NO_MATCHING_WEEKDAY` | 選定日期範圍內沒有符合的星期 |
| `400313` | `TEACHER_EMPLOYMENT_TYPE_INVALID` | employment_type 只能 hourly / full_time |
| `400314` | `TEACHER_AVATAR_FORMAT_INVALID` | 不支援的圖片格式 |
| `400315` | `TEACHER_NO_DUPLICATE` | 教師編號已存在 |
| `400316` | `TEACHER_FILE_NOT_UPLOADED` | 檔案尚未上傳至 S3 |
| `400317` | `TEACHER_EMAIL_USED_BY_TEACHER` | Email 已被其他教師使用 |
| `400318` | `TEACHER_EMAIL_USED_BY_EMPLOYEE` | Email 已被員工使用 |
| `400319` | `TEACHER_EMAIL_USED_BY_STUDENT` | Email 已被學生使用 |
| `400320` | `TEACHER_NO_UPDATE_DATA` | 沒有要更新的資料 |

### 403 Forbidden

| Code | Name | Description |
|------|------|-------------|
| `403301` | `SLOT_FORBIDDEN_NO_TEACHER_DATA` | 找不到教師資料 |
| `403302` | `SLOT_FORBIDDEN_TEACHER_NOT_OWN_DELETE` | 教師只能刪除自己的時段 |
| `403303` | `SLOT_FORBIDDEN_TEACHER_NOT_OWN_UPDATE` | 教師只能更新自己的時段 |
| `403304` | `SLOT_FORBIDDEN_NOT_VIEWABLE` | 此時段不可查看 |
| `403305` | `SLOT_FORBIDDEN_DELETE` | 無權刪除教師時段 |
| `403306` | `SLOT_FORBIDDEN_CREATE` | 無權建立教師時段 |
| `403307` | `SLOT_FORBIDDEN_UPDATE` | 無權更新教師時段 |
| `403308` | `SLOT_FORBIDDEN_VIEW` | 無權查看此時段 |
| `403309` | `TEACHER_FORBIDDEN_NO_TEACHER_DATA` | 找不到對應的教師資料 |

### 404 Not Found

| Code | Name | Description |
|------|------|-------------|
| `404301` | `SLOT_NOT_FOUND` | 教師時段不存在 |
| `404302` | `TEACHER_NOT_FOUND` | 教師不存在 |

### 409 Conflict

| Code | Name | Description |
|------|------|-------------|
| `409301` | `SLOT_CONFLICT` | slot 時間衝突（str(e) 內含詳細） |

### 500 Internal Server Error

| Code | Name | Description |
|------|------|-------------|
| `500301` | `SLOT_INTERNAL` | 通用 str(e) |
| `500302` | `SLOT_DELETE_FAILED` | 刪除教師時段失敗 |
| `500303` | `SLOT_LIST_FAILED` | 取得教師時段列表失敗 |
| `500304` | `SLOT_GET_FAILED` | 取得教師時段失敗 |
| `500305` | `SLOT_CREATE_FAILED` | 建立教師時段失敗 |
| `500306` | `SLOT_BATCH_DELETE_FAILED` | 批次刪除教師時段失敗 |
| `500307` | `SLOT_BATCH_CREATE_FAILED` | 批次建立教師時段失敗 |
| `500308` | `SLOT_BATCH_UPDATE_FAILED` | 批次更新教師時段失敗 |
| `500309` | `SLOT_UPDATE_FAILED` | 更新教師時段失敗 |
| `500310` | `TEACHER_DELETE_FAILED` | 刪除教師失敗 |
| `500311` | `TEACHER_LIST_FAILED` | 取得教師列表失敗 |
| `500312` | `TEACHER_GET_FAILED` | 取得教師失敗 |
| `500313` | `TEACHER_OVERVIEW_LIST_FAILED` | 取得教師綜合檢視失敗 |
| `500314` | `TEACHER_OVERVIEW_FAILED` | 取得教師總覽失敗 |
| `500315` | `TEACHER_CREATE_FAILED` | 建立教師失敗 |
| `500316` | `TEACHER_UPDATE_FAILED` | 更新教師失敗 |
| `500317` | `TEACHER_INFO_UPDATE_FAILED` | 更新教師資料失敗 |
| `500318` | `TEACHER_AVATAR_UPDATE_FAILED` | 更新頭像失敗 |
| `500319` | `TEACHER_UPLOAD_URL_FAILED` | 產生上傳連結失敗 |
| `500320` | `TEACHER_AVATAR_CONFIRM_FAILED` | 確認頭像上傳失敗 |

---

## Domain 4 — STUDENT

共 48 個 code

### 400 Bad Request

| Code | Name | Description |
|------|------|-------------|
| `400401` | `STUDENT_TRIAL_BOOKING_TYPE_REQUIRED` | 只能選擇試上類型的預約 |
| `400402` | `STUDENT_CONTRACT_ID_INVALID` | 合約 ID 格式錯誤 |
| `400403` | `STUDENT_CONTRACT_NOT_OWNED` | 合約不屬於此學生 |
| `400404` | `STUDENT_CONTRACT_NEEDS_PDF` | 合約必須先上傳 PDF 才能轉正 |
| `400405` | `STUDENT_NO_DUPLICATE` | 學生編號已存在 |
| `400406` | `STUDENT_EMAIL_USED_BY_STUDENT` | Email 已被其他學生使用 |
| `400407` | `STUDENT_EMAIL_USED_BY_EMPLOYEE` | Email 已被員工使用 |
| `400408` | `STUDENT_EMAIL_USED_BY_TEACHER` | Email 已被教師使用 |
| `400409` | `STUDENT_NOT_TRIAL` | 此學生非試上學生，無法執行轉正 |
| `400410` | `STUDENT_BOOKING_ALREADY_CONVERTED` | 此預約已被標記為轉正 |
| `400411` | `STUDENT_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400412` | `STUDENT_BOOKING_NOT_COMPLETED` | 預約狀態必須為已完成 |
| `400413` | `STUDENT_COURSE_STUDENT_NOT_FOUND` | 學生不存在 |
| `400414` | `STUDENT_COURSE_ALREADY_ENROLLED` | 此學生已選修此課程 |
| `400415` | `STUDENT_COURSE_COURSE_NOT_FOUND` | 課程不存在 |
| `400416` | `STUDENT_PREF_TEACHER_PRIMARY_NOT_FOUND` | 主要教師不存在 |
| `400417` | `STUDENT_PREF_TEACHERS_NOT_FOUND` | 以下教師不存在 |
| `400418` | `STUDENT_PREF_STUDENT_NOT_FOUND` | 學生不存在 |
| `400419` | `STUDENT_PREF_ALL_TEACHERS_DUPLICATE` | 所有選擇的教師已存在於偏好中 |
| `400420` | `STUDENT_PREF_TEACHER_DUPLICATE` | 此學生已指定該教師 |
| `400421` | `STUDENT_PREF_SCOPE_DUPLICATE` | 此學生已有 N 等級偏好設定 |
| `400422` | `STUDENT_PREF_TEACHER_DUPLICATE_UPDATE` | 此學生已有該教師的偏好設定 |
| `400423` | `STUDENT_PREF_NO_UPDATE_DATA` | 沒有需要更新的欄位 |
| `400424` | `STUDENT_PREF_LEVEL_MODE_REQUIRES_MIN` | 等級模式必須提供 min_teacher_level |
| `400425` | `STUDENT_PREF_COURSE_NOT_FOUND` | 課程不存在 |

### 403 Forbidden

| Code | Name | Description |
|------|------|-------------|
| `403401` | `STUDENT_COURSE_FORBIDDEN_VIEW_OTHER` | 無權查看其他學生的選課 |

### 404 Not Found

| Code | Name | Description |
|------|------|-------------|
| `404401` | `STUDENT_NOT_FOUND` | 學生不存在 |
| `404402` | `STUDENT_PENDING_CONTRACT_NOT_FOUND` | 找不到 pending 合約 |
| `404403` | `STUDENT_BOOKING_NOT_FOUND` | 預約不存在 (students.py 路徑) |
| `404404` | `STUDENT_COURSE_NOT_FOUND` | 選課紀錄不存在 |
| `404405` | `STUDENT_PREF_NOT_FOUND` | 偏好設定不存在 |

### 500 Internal Server Error

| Code | Name | Description |
|------|------|-------------|
| `500401` | `STUDENT_DELETE_FAILED` | 刪除學生失敗 |
| `500402` | `STUDENT_LIST_FAILED` | 取得學生列表失敗 |
| `500403` | `STUDENT_GET_FAILED` | 取得學生失敗 |
| `500404` | `STUDENT_OVERVIEW_LIST_FAILED` | 取得學生綜合檢視失敗 |
| `500405` | `STUDENT_OVERVIEW_FAILED` | 取得學生總覽失敗 |
| `500406` | `STUDENT_CREATE_FAILED` | 建立學生失敗 |
| `500407` | `STUDENT_UPDATE_FAILED` | 更新學生失敗 |
| `500408` | `STUDENT_CONVERT_FAILED` | 試上轉正失敗 |
| `500409` | `STUDENT_COURSE_INTERNAL` | 通用 str(e) |
| `500410` | `STUDENT_COURSE_LIST_FAILED` | 取得學生選課列表失敗 |
| `500411` | `STUDENT_COURSE_GET_FAILED` | 取得學生選課失敗 |
| `500412` | `STUDENT_COURSE_CREATE_FAILED` | 新增學生選課失敗 |
| `500413` | `STUDENT_COURSE_DELETE_FAILED` | 移除學生選課失敗 |
| `500414` | `STUDENT_PREF_INTERNAL` | 通用 str(e) |
| `500415` | `STUDENT_PREF_DELETE_FAILED` | 刪除偏好失敗 |
| `500416` | `STUDENT_PREF_CREATE_FAILED` | 建立偏好失敗 |
| `500417` | `STUDENT_PREF_UPDATE_FAILED` | 更新偏好失敗 |

---

## Domain 5 — EMPLOYEE

共 57 個 code

### 400 Bad Request

| Code | Name | Description |
|------|------|-------------|
| `400501` | `EMPLOYEE_NO_DUPLICATE` | 員工編號已存在 |
| `400502` | `EMPLOYEE_EMAIL_USED_BY_EMPLOYEE` | Email 已被其他員工使用 |
| `400503` | `EMPLOYEE_EMAIL_USED_BY_STUDENT` | Email 已被學生使用 |
| `400504` | `EMPLOYEE_EMAIL_USED_BY_TEACHER` | Email 已被教師使用 |
| `400505` | `EMPLOYEE_NO_ACCOUNT_FOR_ROLE` | 此員工尚未建立帳號 |
| `400506` | `EMPLOYEE_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400507` | `PERM_ROLE_IN_USE` | 角色使用中無法刪除 |
| `400508` | `PERM_NO_UPDATE_FIELDS` | 沒有可更新的欄位 |
| `400509` | `PERM_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400510` | `PERM_ROLE_KEY_DUPLICATE` | 角色 key 已存在 |
| `400511` | `PERM_PAGE_KEY_DUPLICATE` | 頁面 key 已存在 (create) |
| `400512` | `PERM_PAGE_KEY_DUPLICATE_UPDATE` | 頁面 key 已存在 (update) |
| `400513` | `INVITE_ENTITY_TYPE_INVALID` | 不支援的實體類型 |
| `400514` | `INVITE_EMAIL_HAS_ACCOUNT` | email 已有登入帳號 |
| `400515` | `INVITE_ACCOUNT_VERIFIED` | 此帳號已驗證 |
| `400516` | `INVITE_ACCOUNT_VERIFIED_RESEND` | 此帳號已驗證，無需重新邀請 |
| `400517` | `INVITE_NO_EMAIL` | 該筆資料沒有 email |
| `400518` | `INVITE_DATA_NOT_FOUND` | 資料不存在或已被刪除 |
| `400519` | `INVITE_LINK_INVALID` | 邀請連結無效或已過期 |
| `400520` | `USER_NO_UPDATE_DATA` | 沒有要更新的資料 |

### 403 Forbidden

| Code | Name | Description |
|------|------|-------------|
| `403501` | `EMPLOYEE_FORBIDDEN_STAFF_ONLY` | 僅限員工存取 |
| `403502` | `EMPLOYEE_FORBIDDEN_ADMIN_ONLY` | 僅限管理員操作 |
| `403503` | `PERM_SYSTEM_ROLE_PROTECTED` | 系統內建角色無法刪除 |
| `403504` | `USER_FORBIDDEN_PROTECTED_UPDATE` | 受保護無法修改 |
| `403505` | `USER_FORBIDDEN_PROTECTED_DISABLE` | 受保護無法停用 |

### 404 Not Found

| Code | Name | Description |
|------|------|-------------|
| `404501` | `EMPLOYEE_NOT_FOUND` | 員工不存在 |
| `404502` | `PERM_ROLE_NOT_FOUND` | 角色不存在 |
| `404503` | `PERM_PAGE_NOT_FOUND` | 頁面不存在 |
| `404504` | `INVITE_ENTITY_NOT_FOUND` | entity 不存在 |
| `404505` | `USER_NOT_FOUND` | 帳號不存在 |

### 500 Internal Server Error

| Code | Name | Description |
|------|------|-------------|
| `500501` | `EMPLOYEE_DELETE_FAILED` | 刪除員工失敗 |
| `500502` | `EMPLOYEE_LIST_FAILED` | 取得員工列表失敗 |
| `500503` | `EMPLOYEE_GET_FAILED` | 取得員工失敗 |
| `500504` | `EMPLOYEE_ROLES_LIST_FAILED` | 取得角色列表失敗 |
| `500505` | `EMPLOYEE_CREATE_FAILED` | 建立員工失敗 |
| `500506` | `EMPLOYEE_UPDATE_FAILED` | 更新員工失敗 |
| `500507` | `PERM_DISABLE_FAILED` | 停用失敗 |
| `500508` | `PERM_DISABLE_PAGE_FAILED` | 停用頁面失敗 |
| `500509` | `PERM_DELETE_ROLE_FAILED` | 刪除角色失敗 |
| `500510` | `PERM_GET_FAILED` | 取得權限失敗 |
| `500511` | `PERM_GET_USER_OVERRIDES_FAILED` | 取得用戶覆寫失敗 |
| `500512` | `PERM_ROLES_LIST_FAILED` | 取得角色列表失敗 |
| `500513` | `PERM_ROLE_PAGES_FAILED` | 取得角色頁面失敗 |
| `500514` | `PERM_PAGES_LIST_FAILED` | 取得頁面列表失敗 |
| `500515` | `PERM_CREATE_ROLE_FAILED` | 建立角色失敗 |
| `500516` | `PERM_CREATE_PAGE_FAILED` | 建立頁面失敗 |
| `500517` | `PERM_UPDATE_FAILED` | 更新失敗 (generic) |
| `500518` | `PERM_UPDATE_ROLE_FAILED` | 更新角色失敗 |
| `500519` | `PERM_UPDATE_PAGE_FAILED` | 更新頁面失敗 |
| `500520` | `PERM_SET_USER_OVERRIDES_FAILED` | 設定用戶覆寫失敗 |
| `500521` | `PERM_SET_ROLE_PAGES_FAILED` | 設定角色頁面失敗 |
| `500522` | `INVITE_CREATE_ACCOUNT_FAILED` | 建立帳號失敗 |
| `500523` | `INVITE_LINK_GENERATE_FAILED` | 產生邀請連結失敗 |
| `500524` | `INVITE_ROLE_NOT_FOUND` | 角色不存在 (500 路徑) |
| `500525` | `USER_DISABLE_FAILED` | 停用帳號失敗 |
| `500526` | `USER_LIST_FAILED` | 列出帳號失敗 |
| `500527` | `USER_UPDATE_FAILED` | 更新帳號失敗 |

---

## Domain 6 — COURSE

共 9 個 code

### 400 Bad Request

| Code | Name | Description |
|------|------|-------------|
| `400601` | `COURSE_DUPLICATE_CODE` | 課程代碼已存在 |
| `400602` | `COURSE_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400603` | `COURSE_INTERNAL_400` | generic 400 (multi-line detail 抓不到) |

### 404 Not Found

| Code | Name | Description |
|------|------|-------------|
| `404601` | `COURSE_NOT_FOUND` | 課程不存在 |

### 500 Internal Server Error

| Code | Name | Description |
|------|------|-------------|
| `500601` | `COURSE_DELETE_FAILED` | 刪除課程失敗 |
| `500602` | `COURSE_LIST_FAILED` | 取得課程列表失敗 |
| `500603` | `COURSE_GET_FAILED` | 取得課程失敗 |
| `500604` | `COURSE_CREATE_FAILED` | 建立課程失敗 |
| `500605` | `COURSE_UPDATE_FAILED` | 更新課程失敗 |

---

## Domain 7 — EXTERNAL

共 39 個 code

### 400 Bad Request

| Code | Name | Description |
|------|------|-------------|
| `400701` | `ZOOM_OAUTH_TOKEN_FAILED` | OAuth token 換取失敗 |
| `400702` | `ZOOM_OAUTH_NOT_CONFIGURED` | OAuth 尚未設定 |
| `400703` | `ZOOM_S2S_CONNECTION_FAILED` | S2S 連線失敗 |
| `400704` | `ZOOM_BATCH_SIZE_INVALID` | booking_ids 必須 1~100 筆 |
| `400705` | `ZOOM_BOOKING_STATUS_INVALID` | 只有待確認/已確認可建會議 |
| `400706` | `ZOOM_NO_UPDATE_DATA` | 沒有要更新的資料 |
| `400707` | `ZOOM_BOOKING_IN_PAST` | 無法為過去的預約建立 |
| `400708` | `ZOOM_OAUTH_STATE_MISSING` | 缺少 state 參數 |
| `400709` | `GDRIVE_OAUTH_NOT_CONFIGURED` | OAuth 尚未設定 |
| `400710` | `GDRIVE_OAUTH_NO_CLIENT_ID` | 缺少 CLIENT_ID |
| `400711` | `GDRIVE_NO_REFRESH_TOKEN` | 未取得 refresh_token |

### 403 Forbidden

| Code | Name | Description |
|------|------|-------------|
| `403701` | `ZOOM_INVALID_SECRET` | Invalid secret (webhook) |
| `403702` | `ZOOM_FORBIDDEN_VIEW_BOOKING` | 無權查看此預約的 Zoom |

### 404 Not Found

| Code | Name | Description |
|------|------|-------------|
| `404701` | `ZOOM_MEETING_NOT_FOUND` | Meeting not found |
| `404702` | `ZOOM_ACCOUNT_NOT_FOUND` | Zoom 帳號不存在 |
| `404703` | `ZOOM_RECORDING_NOT_READY` | 尚無可用的錄影 |
| `404704` | `ZOOM_TEACHER_NOT_FOUND_OAUTH` | 找不到對應的教師紀錄 (OAuth callback) |
| `404705` | `ZOOM_TEACHER_NOT_FOUND` | 找不到教師紀錄 |
| `404706` | `ZOOM_NO_MEETING_FOR_BOOKING` | 此預約尚無 Zoom 會議 |
| `404707` | `ZOOM_NO_RECORDING_FILE` | 無可用錄影檔案 |
| `404708` | `ZOOM_BOOKING_NOT_FOUND` | 預約不存在 (zoom.py 路徑) |
| `404709` | `GDRIVE_NOT_BOUND` | 未綁定 Google Drive |
| `404710` | `GDRIVE_BIND_REQUIRED` | 請先綁定 Google Drive |

### 500 Internal Server Error

| Code | Name | Description |
|------|------|-------------|
| `500701` | `ZOOM_ACCOUNT_DELETE_FAILED` | 刪除 Zoom 帳號失敗 |
| `500702` | `ZOOM_ACCOUNT_LIST_FAILED` | 取得 Zoom 帳號列表失敗 |
| `500703` | `ZOOM_DOWNLOAD_TOKEN_FAILED` | 取得下載 token 失敗 |
| `500704` | `ZOOM_MEETING_LIST_FAILED` | 取得會議紀錄失敗 |
| `500705` | `ZOOM_RECORDING_GET_FAILED` | 取得錄影失敗 |
| `500706` | `ZOOM_MEETING_CREATE_FAILED` | 建立 Zoom 會議失敗 |
| `500707` | `ZOOM_BATCH_QUERY_FAILED` | 批次查詢失敗 |
| `500708` | `ZOOM_ACCOUNT_CREATE_FAILED` | 新增 Zoom 帳號失敗 |
| `500709` | `ZOOM_ACCOUNT_UPDATE_FAILED` | 更新 Zoom 帳號失敗 |
| `500710` | `ZOOM_MEETING_QUERY_FAILED` | 查詢 Zoom 會議失敗 |
| `500711` | `ZOOM_TEST_CONNECTION_FAILED` | 測試 Zoom 連線失敗 |
| `500712` | `ZOOM_TOKEN_FAILED` | 無法取得 Zoom token |
| `500713` | `ZOOM_RECORDING_UPDATE_FAILED` | 錄影資訊更新失敗 |
| `500714` | `GDRIVE_TOKEN_EXCHANGE_FAILED` | token exchange 失敗 |

### 503 Service Unavailable

| Code | Name | Description |
|------|------|-------------|
| `503701` | `LINE_CHANNEL_DISABLED` | 頻道功能未啟用 |
| `503702` | `LINE_LOGIN_DISABLED` | Line 登入功能未啟用 |

---

## Domain 9 — SYSTEM

共 6 個 code

### 400 Bad Request

| Code | Name | Description |
|------|------|-------------|
| `400901` | `AUTH_CURRENT_PASSWORD_WRONG` | 當前密碼錯誤 |

### 404 Not Found

| Code | Name | Description |
|------|------|-------------|
| `404901` | `ALERT_NOT_FOUND` | 告警不存在 |

### 500 Internal Server Error

| Code | Name | Description |
|------|------|-------------|
| `500901` | `ALERT_LIST_FAILED` | 取得告警列表失敗 |
| `500902` | `ALERT_UNREAD_COUNT_FAILED` | 取得未讀數量失敗 |
| `500903` | `ALERT_MARK_FAILED` | 標記失敗 |
| `500904` | `AUTH_PASSWORD_UPDATE_FAILED` | 密碼更新失敗 |

---
