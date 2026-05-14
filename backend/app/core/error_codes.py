"""
統一錯誤碼定義（PR A：基礎轉成 IntEnum + 6 位數）

格式：<3-digit HTTP status><3-digit seq>
  401001 = 401 Auth 第 1 號
  403001 = 403 Forbidden 第 1 號
  400001 = 400 Validation 第 1 號
  ...

PR B 會在每個 status 內依 domain 切 sub-range 並補上具體 code（#63 Phase 2b）。

API 回傳時 error_code 序列化為 int。前端 type 也是 number。
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    # === Auth (401xxx) ===
    AUTH_ERROR = 401001
    AUTH_TOKEN_EXPIRED = 401002
    AUTH_TOKEN_INVALID = 401003
    AUTH_SESSION_EXPIRED = 401004
    AUTH_IDLE_TIMEOUT = 401005
    AUTH_SESSION_REPLACED = 401006
    AUTH_LOGIN_FAILED = 401007
    AUTH_API_KEY_INVALID = 401008

    # === Forbidden (403xxx) ===
    FORBIDDEN = 403001
    FORBIDDEN_ROLE = 403002
    FORBIDDEN_OWNER = 403003
    FORBIDDEN_PROTECTED = 403004
    FORBIDDEN_PAGE = 403005

    # === Not Found (404xxx) ===
    NOT_FOUND = 404001

    # === Validation / Bad Request (400xxx) ===
    VALIDATION_ERROR = 400001
    DUPLICATE_ENTRY = 400002
    NO_UPDATE_DATA = 400003
    INVALID_STATE = 400004
    INVALID_FILE = 400005
    QUOTA_EXCEEDED = 400006
    WRONG_PASSWORD = 400007

    # === Conflict (409xxx) ===
    CONFLICT = 409001

    # === Rate Limit (429xxx) ===
    RATE_LIMITED = 429001

    # === Service Unavailable (503xxx) ===
    SERVICE_UNAVAILABLE = 503001

    # === Server (500xxx) ===
    INTERNAL_ERROR = 500001

    # ================================================================
    # Domain 1 — BOOKING (bookings.py / leave_records.py / lesson_notes.py / substitute_details.py)
    # 6 位數 code 規則：<3-status><1-domain=1><2-seq>
    # ================================================================

    # --- 400 Booking validation ---
    BOOKING_INVALID = 400100                          # generic booking 400
    BOOKING_STUDENT_NOT_FOUND_OR_DISABLED = 400101    # 學生不存在或已停用
    BOOKING_TEACHER_NOT_FOUND_OR_DISABLED = 400102    # 教師不存在或已停用
    BOOKING_COURSE_NOT_FOUND_OR_DISABLED = 400103     # 課程不存在或已停用
    BOOKING_STUDENT_COURSE_NOT_ENROLLED = 400104      # 學生未選修此課程
    BOOKING_TEACHER_NOT_QUALIFIED = 400105            # 教師無此課程的授課資格
    BOOKING_STUDENT_CONTRACT_NOT_FOUND = 400106       # 學生合約不存在
    BOOKING_STUDENT_CONTRACT_LESSONS_INSUFFICIENT = 400107  # 學生合約剩餘堂數不足
    BOOKING_FORMAL_STUDENT_REQUIRES_CONTRACT = 400108  # 正式學生必須提供學生合約
    BOOKING_TEACHER_CONTRACT_NOT_FOUND = 400109       # 教師合約不存在
    BOOKING_TEACHER_SLOT_NOT_FOUND = 400110           # 教師時段不存在 (400 路徑)
    BOOKING_TEACHER_SLOT_UNAVAILABLE = 400111         # 教師時段不可用
    BOOKING_DATE_SLOT_MISMATCH = 400112               # 預約日期與時段日期不符
    BOOKING_DURATION_NOT_COURSE_MULTIPLE = 400113     # 預約時長必須是課程時長倍數
    BOOKING_TIME_OUT_OF_SLOT_RANGE = 400114           # 預約時間超出時段範圍
    BOOKING_END_TIME_NOT_30MIN_BOUNDARY = 400115      # 結束時間必須在 30 分鐘邊界上
    BOOKING_END_TIME_BEFORE_START = 400116            # 新結束時間必須晚於開始時間
    BOOKING_SHORTEN_ONLY = 400117                     # 只允許縮短預約
    BOOKING_SHORTENED_DURATION_NOT_MULTIPLE = 400118  # 縮短後時長必須是課程時長倍數
    BOOKING_TEACHER_NOT_IN_STUDENT_PREFERENCES = 400119  # 此教師不在學生的偏好可預約教師範圍內
    BOOKING_SLOT_NO_VALID_CONTRACT = 400120           # 此時段無有效教師有效合約
    BOOKING_TIME_NO_AVAILABLE_SLOT = 400121           # 找不到包含預約時間的可用時段
    BOOKING_NO_UPDATE_DATA = 400122                   # 沒有要更新的資料
    BOOKING_COMPLETED_NOT_EDITABLE = 400123           # 已完成的預約無法修改
    BOOKING_CANCELLED_NOT_EDITABLE = 400124           # 已取消的預約無法修改
    BOOKING_ONLY_PENDING_CAN_CONFIRM = 400125         # 只有待確認的預約可以確認
    BOOKING_ONLY_PENDING_CAN_CANCEL = 400126          # 只有待確認的預約可以取消（已確認走請假）
    BOOKING_ONLY_PENDING_OR_CANCELLED_CAN_DELETE = 400127  # 只有待確認或已取消可刪
    BOOKING_COURSE_ID_REQUIRED = 400128               # 請提供課程 ID
    BOOKING_BOOKING_ID_REQUIRED = 400129              # 請提供預約 ID
    BOOKING_STUDENT_NOT_EXIST = 400130                # 學生不存在 (不同於上面的"或已停用")

    # --- 403 Booking forbidden ---
    BOOKING_FORBIDDEN_NOT_OWN_CANCEL = 403101         # 只能取消自己的預約
    BOOKING_FORBIDDEN_STUDENT_NOT_OWN = 403102        # 學生只能為自己預約
    BOOKING_FORBIDDEN_NO_VIEW = 403103                # 無權查看此預約
    BOOKING_FORBIDDEN_NO_CREATE = 403104              # 無權建立預約
    BOOKING_FORBIDDEN_STUDENT_NO_UPDATE = 403105      # 學生無權更新預約
    BOOKING_FORBIDDEN_TEACHER_CONFIRM_ONLY = 403106   # 教師僅可將預約狀態更新為已確認
    BOOKING_FORBIDDEN_TEACHER_OWN_ONLY = 403107       # 教師只能更新自己的預約
    BOOKING_FORBIDDEN_NO_STUDENT_INFO = 403108        # 無法取得學生資料

    # --- 404 Booking not found ---
    BOOKING_NOT_FOUND = 404101                        # 預約不存在
    BOOKING_SLOT_NOT_FOUND_404 = 404102               # 教師時段不存在 (404 路徑)

    # --- 409 Booking conflict ---
    BOOKING_TIME_CONFLICT = 409101                    # 預約時間衝突
    BOOKING_ZOOM_POOL_EXHAUSTED = 409102              # Zoom 帳號池當下無可用

    # --- 500 Booking internal ---
    BOOKING_INTERNAL = 500101                         # generic booking 500
    BOOKING_CREATE_FAILED = 500102                    # 建立預約失敗
    BOOKING_UPDATE_FAILED = 500103                    # 更新預約失敗
    BOOKING_DELETE_FAILED = 500104                    # 刪除預約失敗
    BOOKING_CANCEL_FAILED = 500105                    # 取消預約失敗
    BOOKING_BATCH_CREATE_FAILED = 500106              # 批次建立失敗
    BOOKING_BATCH_UPDATE_FAILED = 500107              # 批次更新失敗
    BOOKING_BATCH_DELETE_FAILED = 500108              # 批次刪除失敗
    BOOKING_LIST_FAILED = 500109                      # 取得預約列表失敗
    BOOKING_GET_FAILED = 500110                       # 取得預約失敗
    BOOKING_SLOT_AVAILABILITY_FAILED = 500111         # 取得時段可用狀態失敗

    # --- 502 Booking external service ---
    BOOKING_ZOOM_SERVICE_UNAVAILABLE = 502101         # Zoom 服務目前無法建立會議

    # --- 400 Leave records (leave_records.py) ---
    BOOKING_LEAVE_INITIATOR_TYPE_REQUIRED = 400131    # 員工代申請須指定 initiator_type
    BOOKING_LEAVE_PENDING_ALREADY_EXISTS = 400132     # 此預約已有待審核的請假申請
    BOOKING_LEAVE_BOOKING_NOT_CONFIRMED = 400133      # 只有已確認的預約可以請假
    BOOKING_LEAVE_ONLY_PENDING_CAN_WITHDRAW = 400134  # 只有待審核的請假可以撤回
    BOOKING_LEAVE_ONLY_PENDING_CAN_APPROVE = 400135   # 只有待審核的請假可以核准
    BOOKING_LEAVE_ONLY_PENDING_CAN_REJECT = 400136    # 只有待審核的請假可以駁回
    BOOKING_LEAVE_NO_STUDENT_CONTRACT = 400137        # 此預約查無對應的學生合約
    BOOKING_LEAVE_EMERGENCY_QUOTA_EXCEEDED = 400138   # 緊急請假額度已用完
    BOOKING_LEAVE_TOO_LATE = 400139                   # 課程開始前 30 分鐘內無法請假
    BOOKING_LEAVE_RELATED_BOOKING_NOT_EXIST = 400140  # 關聯的預約不存在（與 BOOKING_NOT_FOUND 不同情境）

    # --- 403 Leave forbidden ---
    BOOKING_LEAVE_FORBIDDEN_APPROVE = 403109          # 僅限員工核准請假
    BOOKING_LEAVE_FORBIDDEN_REJECT = 403110           # 僅限員工駁回請假
    BOOKING_LEAVE_FORBIDDEN_NOT_INITIATOR = 403111    # 只有發起者可以撤回請假
    BOOKING_LEAVE_FORBIDDEN_STUDENT_NOT_OWN = 403112  # 學生只能為自己的預約請假
    BOOKING_LEAVE_FORBIDDEN_TEACHER_NOT_OWN = 403113  # 教師只能為自己的預約請假
    BOOKING_LEAVE_FORBIDDEN_CREATE = 403114           # 無權建立請假申請
    BOOKING_LEAVE_FORBIDDEN_WITHDRAW = 403115         # 無權撤回請假
    BOOKING_LEAVE_FORBIDDEN_VIEW = 403116             # 無權查看此請假紀錄

    # --- 404 Leave not found ---
    BOOKING_LEAVE_NOT_FOUND = 404103                  # 請假紀錄不存在
    # 注意：leave_records.py 中的「預約不存在」(404) 沿用 BOOKING_NOT_FOUND = 404101

    # --- 500 Leave internal ---
    BOOKING_LEAVE_LIST_FAILED = 500112                # 取得請假紀錄失敗
    BOOKING_LEAVE_CREATE_FAILED = 500113              # 建立請假申請失敗
    BOOKING_LEAVE_WITHDRAW_FAILED = 500114            # 撤回請假失敗
    BOOKING_LEAVE_APPROVE_FAILED = 500115             # 核准請假失敗
    BOOKING_LEAVE_REJECT_FAILED = 500116              # 駁回請假失敗

    # --- 400 Lesson note validation (lesson_notes.py) ---
    BOOKING_NOTE_INVALID_STATUS_UPLOAD = 400141       # 預約狀態 X 無法上傳筆記
    BOOKING_NOTE_INVALID_STATUS_CONFIRM = 400142      # 預約狀態 X 無法確認筆記

    # --- 403 Lesson note forbidden ---
    BOOKING_NOTE_FORBIDDEN_CONFIRM = 403117           # 只有該預約的學生或員工可以確認
    BOOKING_NOTE_FORBIDDEN_UPLOAD = 403118            # 只有該預約的老師可以上傳
    BOOKING_NOTE_FORBIDDEN_UPDATE = 403119            # 只有該預約的老師可以修改
    BOOKING_NOTE_FORBIDDEN_VIEW = 403120              # 無權限查看此筆記

    # --- 404 Lesson note not found ---
    BOOKING_NOTE_NOT_UPLOADED = 404104                # 尚未上傳課後筆記
    BOOKING_NOTE_NOT_UPLOADED_FOR_UPDATE = 404105     # 尚未上傳課後筆記，無法修改

    # --- 409 Lesson note conflict ---
    BOOKING_NOTE_ALREADY_UPLOADED = 409103            # 此預約已上傳過筆記
    BOOKING_NOTE_ALREADY_CONFIRMED = 409104           # 筆記已被確認過
    BOOKING_NOTE_CONFIRMED_NOT_EDITABLE = 409105      # 筆記已被確認，無法修改

    # --- 400 Substitute validation (substitute_details.py) ---
    BOOKING_SUB_TEACHER_SELF_NOT_ALLOWED = 400143     # 不能指派原教師自己為代課
    BOOKING_SUB_TEACHER_NOT_FOUND = 400144            # 代課教師不存在或未啟用
    BOOKING_SUB_TEACHER_CONTRACT_INVALID = 400145     # 代課教師合約不存在或非有效狀態
    BOOKING_SUB_TEACHER_CONTRACT_NO_COURSE = 400146   # 代課教師合約未包含此課程
    BOOKING_SUB_TEACHER_NO_SLOT = 400147              # 代課教師沒有可用的預約時段
    BOOKING_SUB_BOOKING_NOT_CONFIRMED = 400148        # 只有已確認的預約可以指派代課
    BOOKING_SUB_ALREADY_ASSIGNED = 400149             # 此預約已有代課紀錄

    # --- 403 Substitute forbidden ---
    BOOKING_SUB_FORBIDDEN_CANCEL = 403121             # 僅限員工取消代課
    BOOKING_SUB_FORBIDDEN_ASSIGN = 403122             # 僅限員工指派代課
    BOOKING_SUB_FORBIDDEN_VIEW = 403123               # 僅限教師查看

    # --- 404 Substitute not found ---
    BOOKING_SUB_NOT_FOUND = 404106                    # 代課紀錄不存在

    # --- 409 Substitute conflict ---
    BOOKING_SUB_TIME_CONFLICT_OTHER_SUB = 409106      # 代課教師已有代課安排
    BOOKING_SUB_TIME_CONFLICT_OWN_BOOKING = 409107    # 代課教師已有預約

    # --- 500 Substitute internal ---
    BOOKING_SUB_LIST_FAILED = 500117                  # 取得代課紀錄失敗
    BOOKING_SUB_MY_LIST_FAILED = 500118               # 取得我的代課紀錄失敗
    BOOKING_SUB_CANCEL_FAILED = 500119                # 取消代課失敗
    BOOKING_SUB_CREATE_FAILED = 500120                # 建立代課紀錄失敗
    BOOKING_SUB_ASSIGN_FAILED = 500121                # 指派代課失敗


def infer_error_code(status_code: int, detail: str) -> ErrorCode:
    """從 HTTP status code 和中文錯誤訊息自動推斷 error_code。

    用於全域 exception handler，讓現有的 raise HTTPException(...)
    不需修改也能自動帶上 error_code。

    PR B 之後每個 raise 都會明確指定 code，這個函式會逐步退役。
    """
    if status_code == 401:
        if "閒置超時" in detail:
            return ErrorCode.AUTH_IDLE_TIMEOUT
        if "其他裝置" in detail:
            return ErrorCode.AUTH_SESSION_REPLACED
        if "Token 已過期" in detail:
            return ErrorCode.AUTH_TOKEN_EXPIRED
        if "無效的 Token" in detail or "Token 已失效" in detail:
            return ErrorCode.AUTH_TOKEN_INVALID
        if "Session 已過期" in detail:
            return ErrorCode.AUTH_SESSION_EXPIRED
        if "登入失敗" in detail or "帳號或密碼" in detail:
            return ErrorCode.AUTH_LOGIN_FAILED
        if "API Key" in detail:
            return ErrorCode.AUTH_API_KEY_INVALID
        return ErrorCode.AUTH_ERROR

    if status_code == 403:
        if "頁面權限" in detail:
            return ErrorCode.FORBIDDEN_PAGE
        if "僅限" in detail:
            return ErrorCode.FORBIDDEN_ROLE
        if "受保護" in detail:
            return ErrorCode.FORBIDDEN_PROTECTED
        if "自己的" in detail or "只能" in detail or "無權" in detail:
            return ErrorCode.FORBIDDEN_OWNER
        return ErrorCode.FORBIDDEN

    if status_code == 404:
        return ErrorCode.NOT_FOUND

    if status_code == 409:
        return ErrorCode.CONFLICT

    if status_code == 429:
        return ErrorCode.RATE_LIMITED

    if status_code == 503:
        return ErrorCode.SERVICE_UNAVAILABLE

    if status_code >= 500:
        return ErrorCode.INTERNAL_ERROR

    # 400-level: 根據訊息關鍵字推斷
    if "已存在" in detail:
        return ErrorCode.DUPLICATE_ENTRY
    if any(kw in detail for kw in ("沒有要更新", "沒有需要更新", "沒有可更新", "沒有指定要更新")):
        return ErrorCode.NO_UPDATE_DATA
    if "密碼錯誤" in detail:
        return ErrorCode.WRONG_PASSWORD
    if "已達" in detail and "上限" in detail:
        return ErrorCode.QUOTA_EXCEEDED
    if "額度" in detail and "用完" in detail:
        return ErrorCode.QUOTA_EXCEEDED
    if "檔案" in detail and ("格式" in detail or "上傳" in detail):
        return ErrorCode.INVALID_FILE
    if any(kw in detail for kw in ("只有", "狀態必須", "才可", "才能", "無法修改", "無法刪除")):
        return ErrorCode.INVALID_STATE

    return ErrorCode.VALIDATION_ERROR
