from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import settings
from app.api.v1.router import api_router
from app.services.redis_service import redis_service
from app.middleware.auth_middleware import AuthMiddleware, RateLimitMiddleware
from app.core.exceptions import AuthException
import logging

# 設定日誌
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
    
    yield
    
    # 關閉時
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

# CORS — 從 FRONTEND_URL 環境變數動態組合，支援逗號分隔多個 origin
_default_origins = [
    "http://localhost:3000",
    "http://localhost:4173",
    "http://localhost:5173",
]
_extra_origins = [o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()]
_all_origins = list(dict.fromkeys(_default_origins + _extra_origins))  # 去重保序

app.add_middleware(
    CORSMiddleware,
    allow_origins=_all_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 速率限制
app.add_middleware(RateLimitMiddleware, requests_per_minute=300)

# 認證中間件
app.add_middleware(AuthMiddleware)

# ========== 例外處理 ==========

@app.exception_handler(AuthException)
async def auth_exception_handler(request: Request, exc: AuthException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": "AUTH_ERROR"
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"未處理的例外: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "伺服器內部錯誤",
            "error_code": "INTERNAL_ERROR"
        }
    )

# ========== 路由 ==========

app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running"
    }