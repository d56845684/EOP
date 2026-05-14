from fastapi import HTTPException, status
from app.core.error_codes import ErrorCode


# ============================================================
# Base Exception
# ============================================================

class AppException(HTTPException):
    """帶有 error_code 的統一例外基底類別。

    全域 exception handler 會讀取 self.error_code 寫入回傳 JSON。
    """
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: int | ErrorCode,
        headers: dict | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        # 統一存成 int，JSON serializer 直接輸出數字
        self.error_code: int = int(error_code)


# ============================================================
# Auth Exceptions (401)
# ============================================================

class AuthException(AppException):
    def __init__(self, detail: str = "認證失敗", error_code: int | ErrorCode = ErrorCode.AUTH_ERROR):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code,
            headers={"WWW-Authenticate": "Bearer"},
        )

class TokenExpiredException(AuthException):
    def __init__(self):
        super().__init__(detail="Token 已過期", error_code=ErrorCode.AUTH_TOKEN_EXPIRED)

class InvalidTokenException(AuthException):
    def __init__(self):
        super().__init__(detail="無效的 Token", error_code=ErrorCode.AUTH_TOKEN_INVALID)

class SessionExpiredException(AuthException):
    def __init__(self):
        super().__init__(detail="Session 已過期，請重新登入", error_code=ErrorCode.AUTH_SESSION_EXPIRED)

class IdleTimeoutException(AuthException):
    def __init__(self):
        super().__init__(detail="閒置超時，系統已自動登出", error_code=ErrorCode.AUTH_IDLE_TIMEOUT)

class SessionReplacedException(AuthException):
    def __init__(self):
        super().__init__(detail="帳號已在其他裝置登入，您已被登出", error_code=ErrorCode.AUTH_SESSION_REPLACED)


# ============================================================
# Permission Exception (403)
# ============================================================

class PermissionDeniedException(AppException):
    def __init__(self, detail: str = "權限不足", error_code: int | ErrorCode = ErrorCode.FORBIDDEN):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code,
        )


# ============================================================
# Not Found Exception (404)
# ============================================================

class UserNotFoundException(AppException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在",
            error_code=ErrorCode.NOT_FOUND,
        )


# ============================================================
# 便利工廠函式 — 讓新 code 可以簡潔地拋出標準化錯誤
# ============================================================

def not_found(resource: str = "資源") -> AppException:
    """404 — 資源不存在"""
    return AppException(404, f"{resource}不存在", ErrorCode.NOT_FOUND)

def duplicate(field: str) -> AppException:
    """400 — 資料已存在"""
    return AppException(400, f"{field}已存在", ErrorCode.DUPLICATE_ENTRY)

def forbidden(detail: str = "權限不足", error_code: int | ErrorCode = ErrorCode.FORBIDDEN) -> AppException:
    """403 — 權限不足"""
    return AppException(403, detail, error_code)

def bad_request(detail: str, error_code: int | ErrorCode = ErrorCode.VALIDATION_ERROR) -> AppException:
    """400 — 通用驗證/業務邏輯錯誤"""
    return AppException(400, detail, error_code)

def conflict(detail: str) -> AppException:
    """409 — 資源衝突"""
    return AppException(409, detail, ErrorCode.CONFLICT)
