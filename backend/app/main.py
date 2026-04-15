from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import asyncio
from app.config import settings
from app.api.v1.router import api_router
from app.services.redis_service import redis_service
from app.middleware.auth_middleware import AuthMiddleware, RateLimitMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.core.exceptions import AuthException, AppException
from app.core.error_codes import ErrorCode, infer_error_code
from app.core.logging import setup_logging, get_logger

# 設定統一 JSON Logger
setup_logging(settings.DEBUG)
logger = get_logger(__name__)

async def ensure_super_admin():
    """確保超級管理員帳號存在（冪等）"""
    from app.services.supabase_service import supabase_service

    if not settings.SUPER_ADMIN_EMAIL or not settings.SUPER_ADMIN_PASSWORD:
        logger.info("SUPER_ADMIN_EMAIL 未設定，跳過超級管理員建立")
        return

    email = settings.SUPER_ADMIN_EMAIL
    password = settings.SUPER_ADMIN_PASSWORD

    try:
        # 檢查 users 表是否已存在
        existing = await supabase_service.pool.fetch(
            "SELECT id FROM public.users WHERE email = $1", email
        )

        if existing:
            user_id = str(existing[0]["id"])
            logger.info(f"Super admin already exists: {email}")

            # 更新密碼（每次啟動以環境變數為準）
            from passlib.hash import bcrypt
            hashed = bcrypt.using(rounds=10).hash(password)
            await supabase_service.pool.execute(
                "UPDATE public.users SET encrypted_password = $1, updated_at = NOW() WHERE id = $2",
                hashed, existing[0]["id"],
            )

            # 確保 is_protected = TRUE
            await supabase_service.pool.execute(
                "UPDATE user_profiles SET is_protected = TRUE WHERE id = $1",
                existing[0]["id"],
            )
            return

        # 建立新 super admin
        # 1. 建 public.users
        auth_response = await supabase_service.sign_up(email, password, {"full_name": "Super Admin", "role": "admin"})
        if not auth_response.user:
            logger.error("Super admin sign_up failed")
            return

        user_id = auth_response.user.id

        # 2. 建 employees 記錄
        import uuid as _uuid
        emp_id = str(_uuid.uuid4())
        await supabase_service.table_insert(
            table="employees",
            data={
                "id": emp_id,
                "employee_no": "SUPER-ADMIN",
                "employee_type": "admin",
                "name": "Super Admin",
                "email": email,
                "hire_date": "2020-01-01",
                "is_active": True,
            },
        )

        # 3. 建 user_profiles（使用 role_id UUID）
        admin_role_id = await supabase_service.pool.fetchval(
            "SELECT id FROM roles WHERE key = 'admin'"
        )
        await supabase_service.table_insert(
            table="user_profiles",
            data={
                "id": user_id,
                "role_id": str(admin_role_id),
                "employee_id": emp_id,
                "employee_subtype": "admin",
                "is_active": True,
                "is_protected": True,
            },
        )

        logger.info(f"Super admin created: {email}")

    except Exception as e:
        logger.error(f"ensure_super_admin failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時
    logger.info("🚀 啟動應用...")

    # 連接 Database
    from app.services.supabase_service import supabase_service
    try:
        await supabase_service.connect(settings.DATABASE_URL)
        logger.info("Database connected")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    # 連接 Redis
    try:
        await redis_service.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    # 確保超級管理員帳號存在
    try:
        await ensure_super_admin()
    except Exception as e:
        logger.error(f"ensure_super_admin error: {e}")

    # 啟動 Zoom 超時會議自動結束排程
    zoom_task = None
    if settings.zoom_enabled:
        async def zoom_auto_end_loop():
            from app.services.zoom_service import zoom_service
            while True:
                try:
                    await zoom_service.auto_end_overdue_meetings()
                except Exception as e:
                    logger.error(f"Zoom auto-end 排程錯誤: {e}")
                await asyncio.sleep(60)  # 每 60 秒檢查一次

        zoom_task = asyncio.create_task(zoom_auto_end_loop())
        logger.info("Zoom 超時會議自動結束排程已啟動（每 60 秒）")

    # 啟動通知佇列 worker
    async def notification_worker_loop():
        from app.services.notification_worker import process_notification_queue
        while True:
            try:
                await process_notification_queue()
            except Exception as e:
                logger.error(f"Notification worker 錯誤: {e}")
            await asyncio.sleep(5)

    notification_task = asyncio.create_task(notification_worker_loop())
    logger.info("Notification queue worker 已啟動（每 5 秒）")

    yield

    # 關閉時
    notification_task.cancel()
    try:
        await notification_task
    except asyncio.CancelledError:
        pass
    if zoom_task:
        zoom_task.cancel()
        try:
            await zoom_task
        except asyncio.CancelledError:
            pass
    logger.info("🛑 關閉應用...")
    await redis_service.disconnect()
    
    # 關閉 DB pool
    await supabase_service.close()

# 建立 FastAPI 應用
app = FastAPI(
    title=settings.APP_NAME,
    description="教育管理系統 API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# ========== 中間件 ==========
# Starlette middleware 執行順序：最後 add 的最先執行（LIFO）
# 期望順序：CORS → Logging → Auth → RateLimit → app
# 所以 add 順序要反過來：RateLimit → Auth → Logging → CORS

# CORS — 從 FRONTEND_URL 環境變數動態組合，支援逗號分隔多個 origin
_default_origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:4173",
    "http://localhost:5173",
]
_extra_origins = [o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()]
_all_origins = list(dict.fromkeys(_default_origins + _extra_origins))  # 去重保序

# 速率限制（最內層）
app.add_middleware(RateLimitMiddleware, requests_per_minute=300)

# 認證中間件
app.add_middleware(AuthMiddleware)

# Request Logging
app.add_middleware(LoggingMiddleware)

# CORS（最外層，最後加入 = 最先執行，確保所有 response 都帶 CORS headers）
app.add_middleware(
    CORSMiddleware,
    allow_origins=_all_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 例外處理 ==========

def _error_response(status_code: int, message: str, error_code: str) -> JSONResponse:
    """統一錯誤回傳格式：message 向後相容、detail 相容前端 parseErrorDetail"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "detail": message,
            "error_code": error_code,
        }
    )

@app.exception_handler(AuthException)
async def auth_exception_handler(request: Request, exc: AuthException):
    error_code = getattr(exc, "error_code", None) or ErrorCode.AUTH_ERROR
    return _error_response(exc.status_code, exc.detail, error_code)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """攔截所有 HTTPException：5xx 錯誤隱藏內部細節，4xx 正常回傳"""
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code} on {request.method} {request.url.path}: {detail}")
        return _error_response(exc.status_code, "伺服器內部錯誤，請稍後再試", ErrorCode.INTERNAL_ERROR)

    # 優先使用 AppException 明確指定的 error_code，否則自動推斷
    explicit_code = getattr(exc, "error_code", None)
    error_code = explicit_code or infer_error_code(exc.status_code, detail)
    return _error_response(exc.status_code, detail, error_code)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"未處理的例外: {exc}")
    return _error_response(500, "伺服器內部錯誤", ErrorCode.INTERNAL_ERROR)

# ========== 路由 ==========

app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running"
    }