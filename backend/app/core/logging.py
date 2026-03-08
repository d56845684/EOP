"""統一 Logger 設定：JSON 格式 + per-request context"""

import logging
import json
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

# Per-request context variables
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
client_ip_var: ContextVar[str] = ContextVar("client_ip", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
method_var: ContextVar[str] = ContextVar("method", default="")
path_var: ContextVar[str] = ContextVar("path", default="")


class JSONFormatter(logging.Formatter):
    """每行輸出一個 JSON object，自動帶入 request context"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 從 contextvars 帶入 request context
        for key, var in [
            ("request_id", request_id_var),
            ("client_ip", client_ip_var),
            ("user_id", user_id_var),
            ("method", method_var),
            ("path", path_var),
        ]:
            val = var.get("")
            if val:
                log_entry[key] = val

        # 附帶 exception traceback
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(debug: bool = False) -> None:
    """初始化統一 logging，取代 basicConfig"""
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    # 移除既有 handler，避免重複
    root.handlers.clear()
    root.addHandler(handler)

    # 將 uvicorn 的 logger 也納入統一 handler
    for uv_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(uv_name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True

    # 降低第三方套件的 log 等級
    for noisy in ("uvicorn.access", "httpcore", "httpx", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """便利函式，等同 logging.getLogger"""
    return logging.getLogger(name)
