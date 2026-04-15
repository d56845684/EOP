"""Request/Response Logging 中間件"""

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import (
    get_logger,
    request_id_var,
    client_ip_var,
    user_id_var,
    method_var,
    path_var,
)

logger = get_logger(__name__)

# 排除 logging 的路徑
EXCLUDED_PATHS = {"/api/v1/health"}


class LoggingMiddleware(BaseHTTPMiddleware):
    """最外層中間件：注入 request context、記錄 request/response log"""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # 排除 health check
        if path in EXCLUDED_PATHS:
            return await call_next(request)

        # 生成 request_id（uuid4 短碼 8 字元）
        rid = uuid.uuid4().hex[:8]

        # 取得 client IP（優先 X-Forwarded-For）
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else "unknown"
        )

        # 設定 contextvars
        tok_rid = request_id_var.set(rid)
        tok_ip = client_ip_var.set(client_ip)
        tok_method = method_var.set(request.method)
        tok_path = path_var.set(path)

        start = time.monotonic()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(f"{request.method} {path} unhandled exception")
            raise

        elapsed_ms = (time.monotonic() - start) * 1000

        # 從 request.state 取 user_id（由 AuthMiddleware 或 contextvars 設定）
        uid = user_id_var.get("")
        if not uid:
            uid = getattr(request.state, "user_id", "") or ""
            if uid:
                user_id_var.set(uid)

        # 添加 X-Request-ID header
        response.headers["X-Request-ID"] = rid

        # 記錄 response log
        msg = f"{request.method} {path} {response.status_code} {elapsed_ms:.0f}ms"
        if elapsed_ms > 3000:
            logger.warning(msg)
        else:
            logger.info(msg)

        # 重置 contextvars
        request_id_var.reset(tok_rid)
        client_ip_var.reset(tok_ip)
        method_var.reset(tok_method)
        path_var.reset(tok_path)

        return response
