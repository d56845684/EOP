from fastapi import HTTPException, status

class AuthException(HTTPException):
    def __init__(self, detail: str = "認證失敗"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class TokenExpiredException(AuthException):
    def __init__(self):
        super().__init__(detail="Token 已過期")

class InvalidTokenException(AuthException):
    def __init__(self):
        super().__init__(detail="無效的 Token")

class SessionExpiredException(AuthException):
    def __init__(self):
        super().__init__(detail="Session 已過期，請重新登入")

class IdleTimeoutException(AuthException):
    def __init__(self):
        super().__init__(detail="閒置超時，系統已自動登出")

class SessionReplacedException(AuthException):
    def __init__(self):
        super().__init__(detail="帳號已在其他裝置登入，您已被登出")

class PermissionDeniedException(HTTPException):
    def __init__(self, detail: str = "權限不足"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

class UserNotFoundException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用戶不存在"
        )