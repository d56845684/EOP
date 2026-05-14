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
