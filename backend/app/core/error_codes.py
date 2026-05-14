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

    # ================================================================
    # Domain 2 — CONTRACT (student_contracts.py / teacher_contracts.py /
    #                       teacher_bonus.py / teacher_details.py)
    # ================================================================

    # --- 400 Student contract validation ---
    STUDENT_CONTRACT_FILE_FORMAT_INVALID = 400201     # 不支援的檔案格式
    STUDENT_CONTRACT_ADDENDUM_ONLY_PENDING_EDIT = 400202  # 只有待生效附約才可修改
    STUDENT_CONTRACT_ADDENDUM_REQUIRES_ACTIVE = 400203 # 只有生效中合約才能建附約
    STUDENT_CONTRACT_STUDENT_NOT_FOUND = 400204       # 學生不存在
    STUDENT_CONTRACT_LEAVE_QUOTA_EXCEEDED = 400205    # 已達請假上限
    STUDENT_CONTRACT_ADDENDUM_END_INVALID = 400206    # 新結束日期須 > 原結束
    STUDENT_CONTRACT_ADDENDUM_END_BEFORE_PARENT = 400207  # 新結束日期須 > 母約結束
    STUDENT_CONTRACT_FILE_NOT_UPLOADED = 400208       # 檔案尚未上傳至 S3
    STUDENT_CONTRACT_COURSE_NOT_ENROLLED = 400209     # 此學生尚未選修此課程
    STUDENT_CONTRACT_PARENT_NOT_ACTIVE = 400210       # 母約狀態不是生效中
    STUDENT_CONTRACT_NO_UPDATE_DATA = 400211          # 沒有要更新的資料
    STUDENT_CONTRACT_INVALID_FILE_PATH = 400212       # 無效的檔案路徑格式
    STUDENT_CONTRACT_TRIAL_ONLY_VIA_CONVERT = 400213  # 試上合約只能透過轉正流程啟用
    STUDENT_CONTRACT_DUPLICATE_ACTIVE = 400214        # 該學生已有生效中合約
    STUDENT_CONTRACT_COURSE_NOT_FOUND = 400215        # 課程不存在

    # --- 403 Student contract forbidden ---
    STUDENT_CONTRACT_FORBIDDEN_TEACHER_DOWNLOAD = 403201      # 教師無權下載學生合約
    STUDENT_CONTRACT_FORBIDDEN_TEACHER_VIEW = 403202          # 教師無權查看學生合約
    STUDENT_CONTRACT_FORBIDDEN_TEACHER_VIEW_DETAIL = 403203   # 教師無權查看學生合約明細
    STUDENT_CONTRACT_FORBIDDEN_TEACHER_VIEW_LEAVE = 403204    # 教師無權查看學生合約請假紀錄
    STUDENT_CONTRACT_FORBIDDEN_DOWNLOAD = 403205              # 無權下載此合約
    STUDENT_CONTRACT_FORBIDDEN_VIEW = 403206                  # 無權查看此合約
    STUDENT_CONTRACT_FORBIDDEN_VIEW_DETAIL = 403207           # 無權查看此合約明細
    STUDENT_CONTRACT_FORBIDDEN_VIEW_LEAVE = 403208            # 無權查看此合約請假紀錄

    # --- 404 Student contract not found ---
    STUDENT_CONTRACT_NOT_FOUND = 404201               # 學生合約不存在
    STUDENT_CONTRACT_DETAIL_NOT_FOUND = 404202        # 合約明細不存在
    STUDENT_CONTRACT_FILE_NOT_UPLOADED_404 = 404203   # 此合約尚未上傳檔案
    STUDENT_CONTRACT_ADDENDUM_FILE_NOT_UPLOADED = 404204
    STUDENT_CONTRACT_ADDENDUM_PDF_FAILED_404 = 404205 # 產生附約 PDF 失敗 (404 路徑)
    STUDENT_CONTRACT_LEAVE_NOT_FOUND = 404206         # 請假紀錄不存在
    STUDENT_CONTRACT_ADDENDUM_NOT_FOUND = 404207      # 附約不存在

    # --- 500 Student contract internal ---
    STUDENT_CONTRACT_INTERNAL = 500201                # 通用 str(e)
    STUDENT_CONTRACT_DETAIL_DELETE_FAILED = 500202    # 刪除合約明細失敗
    STUDENT_CONTRACT_DELETE_FAILED = 500203           # 刪除學生合約失敗
    STUDENT_CONTRACT_LEAVE_DELETE_FAILED = 500204     # 刪除請假紀錄失敗
    STUDENT_CONTRACT_ADDENDUM_DELETE_FAILED = 500205  # 刪除附約失敗
    STUDENT_CONTRACT_DOWNLOAD_URL_FAILED = 500206     # 取得下載連結失敗
    STUDENT_CONTRACT_DETAIL_LIST_FAILED = 500207      # 取得合約明細失敗
    STUDENT_CONTRACT_LIST_FAILED = 500208             # 取得學生合約列表失敗
    STUDENT_CONTRACT_GET_FAILED = 500209              # 取得學生合約失敗
    STUDENT_CONTRACT_LEAVE_LIST_FAILED = 500210       # 取得請假紀錄失敗
    STUDENT_CONTRACT_ADDENDUM_LIST_FAILED = 500211    # 取得附約列表失敗
    STUDENT_CONTRACT_ADDENDUM_GET_FAILED = 500212     # 取得附約失敗
    STUDENT_CONTRACT_CREATE_FAILED = 500213           # 建立學生合約失敗
    STUDENT_CONTRACT_ADDENDUM_CREATE_FAILED = 500214  # 建立附約失敗
    STUDENT_CONTRACT_DETAIL_CREATE_FAILED = 500215    # 新增合約明細失敗
    STUDENT_CONTRACT_LEAVE_CREATE_FAILED = 500216     # 新增請假紀錄失敗
    STUDENT_CONTRACT_DETAIL_UPDATE_FAILED = 500217    # 更新合約明細失敗
    STUDENT_CONTRACT_UPDATE_INFO_FAILED = 500218      # 更新合約資訊失敗
    STUDENT_CONTRACT_UPDATE_FAILED = 500219           # 更新學生合約失敗
    STUDENT_CONTRACT_ADDENDUM_UPDATE_FAILED = 500220  # 更新附約失敗
    STUDENT_CONTRACT_UPLOAD_URL_FAILED = 500221       # 產生上傳連結失敗
    STUDENT_CONTRACT_GENERATE_DOWNLOAD_URL_FAILED = 500222  # 產生下載連結失敗
    STUDENT_CONTRACT_DOCX_FAILED = 500223             # 產生合約 DOCX 失敗
    STUDENT_CONTRACT_PDF_FAILED = 500224              # 產生合約 PDF 失敗
    STUDENT_CONTRACT_ADDENDUM_PDF_FAILED_500 = 500225 # 產生附約 PDF 失敗
    STUDENT_CONTRACT_UPLOAD_CONFIRM_FAILED = 500226   # 確認上傳失敗

    # --- 400 Teacher contract validation ---
    TEACHER_CONTRACT_WORK_SCHEDULE_OVERLAP = 400216         # 工作時段有重疊
    TEACHER_CONTRACT_ADDENDUM_ONLY_PENDING_EDIT = 400217    # 只有待生效附約可修改
    TEACHER_CONTRACT_ADDENDUM_REQUIRES_ACTIVE = 400218      # 只有生效中合約才能建附約
    TEACHER_CONTRACT_TEACHER_NOT_FOUND = 400219             # 教師不存在
    TEACHER_CONTRACT_ADDENDUM_END_INVALID = 400220          # 新結束日期須 > 原結束
    TEACHER_CONTRACT_ADDENDUM_END_BEFORE_PARENT = 400221    # 新結束日期須 > 母約結束
    TEACHER_CONTRACT_FILE_NOT_UPLOADED = 400222             # 檔案尚未上傳至 S3
    TEACHER_CONTRACT_PARENT_NOT_ACTIVE = 400223             # 母約狀態不是生效中
    TEACHER_CONTRACT_OVERTIME_DUPLICATE = 400224            # 每份合約只能設一筆加班費
    TEACHER_CONTRACT_NO_UPDATE_DATA = 400225                # 沒有要更新的資料
    TEACHER_CONTRACT_INVALID_FILE_PATH = 400226             # 無效的檔案路徑格式
    TEACHER_CONTRACT_DUPLICATE_ACTIVE = 400227              # 該教師已有生效中合約
    TEACHER_CONTRACT_COURSE_NOT_FOUND = 400228              # 課程不存在

    # --- 403 Teacher contract forbidden ---
    TEACHER_CONTRACT_FORBIDDEN_STUDENT_DOWNLOAD = 403209       # 學生無權下載教師合約
    TEACHER_CONTRACT_FORBIDDEN_STUDENT_VIEW = 403210           # 學生無權查看教師合約
    TEACHER_CONTRACT_FORBIDDEN_STUDENT_VIEW_SCHEDULE = 403211  # 學生無權查看教師合約工作時段
    TEACHER_CONTRACT_FORBIDDEN_STUDENT_VIEW_DETAIL = 403212    # 學生無權查看教師合約明細
    TEACHER_CONTRACT_FORBIDDEN_DOWNLOAD = 403213               # 無權下載此合約
    TEACHER_CONTRACT_FORBIDDEN_VIEW = 403214                   # 無權查看此合約
    TEACHER_CONTRACT_FORBIDDEN_VIEW_SCHEDULE = 403215          # 無權查看此合約工作時段
    TEACHER_CONTRACT_FORBIDDEN_VIEW_DETAIL = 403216            # 無權查看此合約明細

    # --- 404 Teacher contract not found ---
    TEACHER_CONTRACT_NOT_FOUND = 404208                      # 教師合約不存在
    TEACHER_CONTRACT_DETAIL_NOT_FOUND = 404209               # 合約明細不存在
    TEACHER_CONTRACT_FILE_NOT_UPLOADED_404 = 404210          # 此合約尚未上傳檔案
    TEACHER_CONTRACT_ADDENDUM_FILE_NOT_UPLOADED = 404211     # 此附約尚未上傳檔案
    TEACHER_CONTRACT_ADDENDUM_PDF_FAILED_404 = 404212        # 產生附約 PDF 失敗 (404 路徑)
    TEACHER_CONTRACT_ADDENDUM_NOT_FOUND = 404213             # 附約不存在

    # --- 500 Teacher contract internal ---
    TEACHER_CONTRACT_INTERNAL = 500227                       # 通用 str(e)
    TEACHER_CONTRACT_DETAIL_DELETE_FAILED = 500228           # 刪除合約明細失敗
    TEACHER_CONTRACT_DELETE_FAILED = 500229                  # 刪除教師合約失敗
    TEACHER_CONTRACT_ADDENDUM_DELETE_FAILED = 500230         # 刪除附約失敗
    TEACHER_CONTRACT_DOWNLOAD_URL_FAILED = 500231            # 取得下載連結失敗
    TEACHER_CONTRACT_DETAIL_LIST_FAILED = 500232             # 取得合約明細失敗
    TEACHER_CONTRACT_WORK_SCHEDULE_GET_FAILED = 500233       # 取得工作時段失敗
    TEACHER_CONTRACT_LIST_FAILED = 500234                    # 取得教師合約列表失敗
    TEACHER_CONTRACT_GET_FAILED = 500235                     # 取得教師合約失敗
    TEACHER_CONTRACT_ADDENDUM_LIST_FAILED = 500236           # 取得附約列表失敗
    TEACHER_CONTRACT_ADDENDUM_GET_FAILED = 500237            # 取得附約失敗
    TEACHER_CONTRACT_CREATE_FAILED = 500238                  # 建立教師合約失敗
    TEACHER_CONTRACT_ADDENDUM_CREATE_FAILED = 500239         # 建立附約失敗
    TEACHER_CONTRACT_DETAIL_CREATE_FAILED = 500240           # 新增合約明細失敗
    TEACHER_CONTRACT_DETAIL_UPDATE_FAILED = 500241           # 更新合約明細失敗
    TEACHER_CONTRACT_UPDATE_INFO_FAILED = 500242             # 更新合約資訊失敗
    TEACHER_CONTRACT_WORK_SCHEDULE_UPDATE_FAILED = 500243    # 更新工作時段失敗
    TEACHER_CONTRACT_UPDATE_FAILED = 500244                  # 更新教師合約失敗
    TEACHER_CONTRACT_ADDENDUM_UPDATE_FAILED = 500245         # 更新附約失敗
    TEACHER_CONTRACT_WORK_SCHEDULE_CLEAR_FAILED = 500246     # 清除工作時段失敗
    TEACHER_CONTRACT_UPLOAD_URL_FAILED = 500247              # 產生上傳連結失敗
    TEACHER_CONTRACT_GENERATE_DOWNLOAD_URL_FAILED = 500248   # 產生下載連結失敗
    TEACHER_CONTRACT_PDF_FAILED = 500249                     # 產生合約 PDF 失敗
    TEACHER_CONTRACT_ADDENDUM_PDF_FAILED_500 = 500250        # 產生附約 PDF 失敗
    TEACHER_CONTRACT_UPLOAD_CONFIRM_FAILED = 500251          # 確認上傳失敗

    # --- Teacher bonus (teacher_bonus.py) ---
    TEACHER_BONUS_NO_UPDATE_DATA = 400229                    # 沒有要更新的資料
    TEACHER_BONUS_FORBIDDEN_VIEW = 403217                    # 無權查看此獎金紀錄
    TEACHER_BONUS_NOT_FOUND = 404214                         # 獎金紀錄不存在
    TEACHER_BONUS_TEACHER_NOT_FOUND = 404215                 # 教師不存在
    TEACHER_BONUS_DELETE_FAILED = 500252                     # 刪除教師獎金失敗
    TEACHER_BONUS_LIST_FAILED = 500253                       # 取得教師獎金列表失敗
    TEACHER_BONUS_GET_FAILED = 500254                        # 取得教師獎金失敗
    TEACHER_BONUS_TEACHER_OPTIONS_FAILED = 500255            # 取得教師選項失敗
    TEACHER_BONUS_CREATE_FAILED = 500256                     # 新增教師獎金失敗
    TEACHER_BONUS_UPDATE_FAILED = 500257                     # 更新教師獎金失敗

    # --- Teacher details (teacher_details.py) ---
    TEACHER_DETAIL_FILE_FORMAT_INVALID = 400230              # 不支援的檔案格式
    TEACHER_DETAIL_FILE_NOT_UPLOADED = 400231                # 檔案尚未上傳至 S3
    TEACHER_DETAIL_NO_UPDATE_DATA = 400232                   # 沒有要更新的資料
    TEACHER_DETAIL_FORBIDDEN_DOWNLOAD = 403218               # 無權下載此文件
    TEACHER_DETAIL_FORBIDDEN_VIEW_OTHER = 403219             # 無權查看其他教師的明細
    TEACHER_DETAIL_TEACHER_NOT_FOUND = 404216                # 教師不存在
    TEACHER_DETAIL_NOT_FOUND = 404217                        # 教師明細不存在
    TEACHER_DETAIL_FILE_NOT_UPLOADED_404 = 404218            # 此明細尚無上傳檔案
    TEACHER_DETAIL_DELETE_FAILED = 500258                    # 刪除教師明細失敗
    TEACHER_DETAIL_GET_FAILED = 500259                       # 取得教師明細失敗
    TEACHER_DETAIL_CREATE_FAILED = 500260                    # 新增教師明細失敗
    TEACHER_DETAIL_UPDATE_FAILED = 500261                    # 更新教師明細失敗
    TEACHER_DETAIL_FILE_INFO_UPDATE_FAILED = 500262          # 更新檔案資訊失敗
    TEACHER_DETAIL_UPLOAD_URL_FAILED = 500263                # 產生上傳連結失敗
    TEACHER_DETAIL_DOWNLOAD_URL_FAILED = 500264              # 產生下載連結失敗
    TEACHER_DETAIL_UPLOAD_CONFIRM_FAILED = 500265            # 確認上傳失敗

    # ================================================================
    # Domain 3 — TEACHER (teacher_slots.py / teachers.py)
    # ================================================================

    # --- 400 Teacher slot validation ---
    SLOT_TEACHER_NOT_FOUND_OR_DISABLED = 400301        # 教師不存在或已停用
    SLOT_TEACHER_NO_ACTIVE_CONTRACT = 400302           # 教師沒有 active 合約
    SLOT_TEACHER_NO_VALID_CONTRACT_UPDATE = 400303     # 教師沒有有效合約，無法更新時段合約
    SLOT_TEACHER_NO_VALID_CONTRACT_CREATE = 400304     # 教師無有效合約，無法建立時段
    SLOT_HAS_BOOKING_CANNOT_EDIT = 400305              # 有預約的時段無法修改日期或時間
    SLOT_HAS_BOOKING_CANNOT_DELETE = 400306            # 有預約的時段無法刪除
    SLOT_NO_UPDATE_CONTENT = 400307                    # 沒有指定要更新的內容
    SLOT_NO_UPDATE_DATA = 400308                       # 沒有要更新的資料
    SLOT_UPDATE_CONTENT_REQUIRED = 400309              # 請指定要更新的內容
    SLOT_SELECT_SLOTS_TO_DELETE = 400310               # 請選擇要刪除的時段
    SLOT_SELECT_SLOTS_TO_UPDATE = 400311               # 請選擇要更新的時段
    SLOT_NO_MATCHING_WEEKDAY = 400312                  # 選定日期範圍內沒有符合的星期

    # --- 403 Teacher slot forbidden ---
    SLOT_FORBIDDEN_NO_TEACHER_DATA = 403301            # 找不到教師資料
    SLOT_FORBIDDEN_TEACHER_NOT_OWN_DELETE = 403302     # 教師只能刪除自己的時段
    SLOT_FORBIDDEN_TEACHER_NOT_OWN_UPDATE = 403303     # 教師只能更新自己的時段
    SLOT_FORBIDDEN_NOT_VIEWABLE = 403304               # 此時段不可查看
    SLOT_FORBIDDEN_DELETE = 403305                     # 無權刪除教師時段
    SLOT_FORBIDDEN_CREATE = 403306                     # 無權建立教師時段
    SLOT_FORBIDDEN_UPDATE = 403307                     # 無權更新教師時段
    SLOT_FORBIDDEN_VIEW = 403308                       # 無權查看此時段

    # --- 404 Teacher slot not found ---
    SLOT_NOT_FOUND = 404301                            # 教師時段不存在

    # --- 409 Teacher slot conflict ---
    SLOT_CONFLICT = 409301                             # slot 時間衝突（str(e) 內含詳細）

    # --- 500 Teacher slot internal ---
    SLOT_INTERNAL = 500301                             # 通用 str(e)
    SLOT_DELETE_FAILED = 500302                        # 刪除教師時段失敗
    SLOT_LIST_FAILED = 500303                          # 取得教師時段列表失敗
    SLOT_GET_FAILED = 500304                           # 取得教師時段失敗
    SLOT_CREATE_FAILED = 500305                        # 建立教師時段失敗
    SLOT_BATCH_DELETE_FAILED = 500306                  # 批次刪除教師時段失敗
    SLOT_BATCH_CREATE_FAILED = 500307                  # 批次建立教師時段失敗
    SLOT_BATCH_UPDATE_FAILED = 500308                  # 批次更新教師時段失敗
    SLOT_UPDATE_FAILED = 500309                        # 更新教師時段失敗

    # --- 400 Teacher validation ---
    TEACHER_EMPLOYMENT_TYPE_INVALID = 400313           # employment_type 只能 hourly / full_time
    TEACHER_AVATAR_FORMAT_INVALID = 400314             # 不支援的圖片格式
    TEACHER_NO_DUPLICATE = 400315                      # 教師編號已存在
    TEACHER_FILE_NOT_UPLOADED = 400316                 # 檔案尚未上傳至 S3
    TEACHER_EMAIL_USED_BY_TEACHER = 400317             # Email 已被其他教師使用
    TEACHER_EMAIL_USED_BY_EMPLOYEE = 400318             # Email 已被員工使用
    TEACHER_EMAIL_USED_BY_STUDENT = 400319             # Email 已被學生使用
    TEACHER_NO_UPDATE_DATA = 400320                    # 沒有要更新的資料

    # --- 403 Teacher forbidden ---
    TEACHER_FORBIDDEN_NO_TEACHER_DATA = 403309         # 找不到對應的教師資料

    # --- 404 Teacher not found ---
    TEACHER_NOT_FOUND = 404302                         # 教師不存在

    # --- 500 Teacher internal ---
    TEACHER_DELETE_FAILED = 500310                     # 刪除教師失敗
    TEACHER_LIST_FAILED = 500311                       # 取得教師列表失敗
    TEACHER_GET_FAILED = 500312                        # 取得教師失敗
    TEACHER_OVERVIEW_LIST_FAILED = 500313              # 取得教師綜合檢視失敗
    TEACHER_OVERVIEW_FAILED = 500314                   # 取得教師總覽失敗
    TEACHER_CREATE_FAILED = 500315                     # 建立教師失敗
    TEACHER_UPDATE_FAILED = 500316                     # 更新教師失敗
    TEACHER_INFO_UPDATE_FAILED = 500317                # 更新教師資料失敗
    TEACHER_AVATAR_UPDATE_FAILED = 500318              # 更新頭像失敗
    TEACHER_UPLOAD_URL_FAILED = 500319                 # 產生上傳連結失敗
    TEACHER_AVATAR_CONFIRM_FAILED = 500320             # 確認頭像上傳失敗

    # ================================================================
    # Domain 4 — STUDENT (students.py / student_courses.py / student_teacher_preferences.py)
    # ================================================================

    # --- 400 Student validation (students.py) ---
    STUDENT_TRIAL_BOOKING_TYPE_REQUIRED = 400401       # 只能選擇試上類型的預約
    STUDENT_CONTRACT_ID_INVALID = 400402               # 合約 ID 格式錯誤
    STUDENT_CONTRACT_NOT_OWNED = 400403                # 合約不屬於此學生
    STUDENT_CONTRACT_NEEDS_PDF = 400404                # 合約必須先上傳 PDF 才能轉正
    STUDENT_NO_DUPLICATE = 400405                      # 學生編號已存在
    STUDENT_EMAIL_USED_BY_STUDENT = 400406             # Email 已被其他學生使用
    STUDENT_EMAIL_USED_BY_EMPLOYEE = 400407             # Email 已被員工使用
    STUDENT_EMAIL_USED_BY_TEACHER = 400408             # Email 已被教師使用
    STUDENT_NOT_TRIAL = 400409                         # 此學生非試上學生，無法執行轉正
    STUDENT_BOOKING_ALREADY_CONVERTED = 400410         # 此預約已被標記為轉正
    STUDENT_NO_UPDATE_DATA = 400411                    # 沒有要更新的資料
    STUDENT_BOOKING_NOT_COMPLETED = 400412             # 預約狀態必須為已完成

    # --- 404 Student not found ---
    STUDENT_NOT_FOUND = 404401                         # 學生不存在
    STUDENT_PENDING_CONTRACT_NOT_FOUND = 404402        # 找不到 pending 合約
    STUDENT_BOOKING_NOT_FOUND = 404403                 # 預約不存在 (students.py 路徑)

    # --- 500 Student internal ---
    STUDENT_DELETE_FAILED = 500401                     # 刪除學生失敗
    STUDENT_LIST_FAILED = 500402                       # 取得學生列表失敗
    STUDENT_GET_FAILED = 500403                        # 取得學生失敗
    STUDENT_OVERVIEW_LIST_FAILED = 500404              # 取得學生綜合檢視失敗
    STUDENT_OVERVIEW_FAILED = 500405                   # 取得學生總覽失敗
    STUDENT_CREATE_FAILED = 500406                     # 建立學生失敗
    STUDENT_UPDATE_FAILED = 500407                     # 更新學生失敗
    STUDENT_CONVERT_FAILED = 500408                    # 試上轉正失敗

    # --- 400 Student courses (student_courses.py) ---
    STUDENT_COURSE_STUDENT_NOT_FOUND = 400413          # 學生不存在
    STUDENT_COURSE_ALREADY_ENROLLED = 400414           # 此學生已選修此課程
    STUDENT_COURSE_COURSE_NOT_FOUND = 400415           # 課程不存在

    # --- 403 Student courses forbidden ---
    STUDENT_COURSE_FORBIDDEN_VIEW_OTHER = 403401       # 無權查看其他學生的選課

    # --- 404 Student course not found ---
    STUDENT_COURSE_NOT_FOUND = 404404                  # 選課紀錄不存在

    # --- 500 Student courses internal ---
    STUDENT_COURSE_INTERNAL = 500409                   # 通用 str(e)
    STUDENT_COURSE_LIST_FAILED = 500410                # 取得學生選課列表失敗
    STUDENT_COURSE_GET_FAILED = 500411                 # 取得學生選課失敗
    STUDENT_COURSE_CREATE_FAILED = 500412              # 新增學生選課失敗
    STUDENT_COURSE_DELETE_FAILED = 500413              # 移除學生選課失敗

    # --- 400 Student-teacher preferences ---
    STUDENT_PREF_TEACHER_PRIMARY_NOT_FOUND = 400416    # 主要教師不存在
    STUDENT_PREF_TEACHERS_NOT_FOUND = 400417            # 以下教師不存在
    STUDENT_PREF_STUDENT_NOT_FOUND = 400418             # 學生不存在
    STUDENT_PREF_ALL_TEACHERS_DUPLICATE = 400419        # 所有選擇的教師已存在於偏好中
    STUDENT_PREF_TEACHER_DUPLICATE = 400420             # 此學生已指定該教師
    STUDENT_PREF_SCOPE_DUPLICATE = 400421               # 此學生已有 N 等級偏好設定
    STUDENT_PREF_TEACHER_DUPLICATE_UPDATE = 400422      # 此學生已有該教師的偏好設定
    STUDENT_PREF_NO_UPDATE_DATA = 400423                # 沒有需要更新的欄位
    STUDENT_PREF_LEVEL_MODE_REQUIRES_MIN = 400424       # 等級模式必須提供 min_teacher_level
    STUDENT_PREF_COURSE_NOT_FOUND = 400425              # 課程不存在

    # --- 404 Preference not found ---
    STUDENT_PREF_NOT_FOUND = 404405                     # 偏好設定不存在

    # --- 500 Preference internal ---
    STUDENT_PREF_INTERNAL = 500414                      # 通用 str(e)
    STUDENT_PREF_DELETE_FAILED = 500415                 # 刪除偏好失敗
    STUDENT_PREF_CREATE_FAILED = 500416                 # 建立偏好失敗
    STUDENT_PREF_UPDATE_FAILED = 500417                 # 更新偏好失敗


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
