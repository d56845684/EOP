"""
統一錯誤碼定義

所有 API 錯誤回傳都包含 error_code，方便前端程式化處理。
error_code 為英文 UPPER_SNAKE_CASE，message 維持中文給使用者看。
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    # === Auth (401) ===
    AUTH_ERROR = "AUTH_ERROR"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"
    AUTH_IDLE_TIMEOUT = "AUTH_IDLE_TIMEOUT"
    AUTH_SESSION_REPLACED = "AUTH_SESSION_REPLACED"
    AUTH_LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    AUTH_API_KEY_INVALID = "AUTH_API_KEY_INVALID"

    # === Forbidden (403) ===
    FORBIDDEN = "FORBIDDEN"
    FORBIDDEN_ROLE = "FORBIDDEN_ROLE"
    FORBIDDEN_OWNER = "FORBIDDEN_OWNER"
    FORBIDDEN_PROTECTED = "FORBIDDEN_PROTECTED"
    FORBIDDEN_PAGE = "FORBIDDEN_PAGE"

    # === Not Found (404) ===
    NOT_FOUND = "NOT_FOUND"

    # === Validation / Bad Request (400) ===
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    NO_UPDATE_DATA = "NO_UPDATE_DATA"
    INVALID_STATE = "INVALID_STATE"
    INVALID_FILE = "INVALID_FILE"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    WRONG_PASSWORD = "WRONG_PASSWORD"

    # === Conflict (409) ===
    CONFLICT = "CONFLICT"

    # === Rate Limit (429) ===
    RATE_LIMITED = "RATE_LIMITED"

    # === Service (503) ===
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # === Server (500) ===
    INTERNAL_ERROR = "INTERNAL_ERROR"


def infer_error_code(status_code: int, detail: str) -> str:
    """從 HTTP status code 和中文錯誤訊息自動推斷 error_code。

    用於全域 exception handler，讓現有的 raise HTTPException(...)
    不需修改也能自動帶上 error_code。
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
