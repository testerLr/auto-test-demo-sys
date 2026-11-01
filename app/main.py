import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.db import SessionLocal, get_db, init_db
from app.core.errors import BusinessError
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.cart.router import router as cart_router
from app.modules.catalog.router import router as catalog_router
from app.modules.orders.router import router as orders_router
from app.modules.payments.router import router as payments_router
from app.modules.seed import data as seed_data

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger("app")

API_PREFIX = "/api/v1"

HTTP_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
}

OPENAPI_TAGS = [
    {"name": "认证", "description": "注册、登录、当前用户"},
    {"name": "商品", "description": "分类与商品查询（公开）"},
    {"name": "购物车", "description": "购物车增删改查（需登录）"},
    {"name": "订单", "description": "订单创建、查询、取消、确认收货（需登录）"},
    {"name": "支付", "description": "模拟支付、回调、退款（需登录，回调除外）"},
    {"name": "管理", "description": "商品管理与测试数据重置（需管理员）"},
    {"name": "系统", "description": "健康检查与服务信息"},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        if seed_data.seed_if_empty(db):
            logger.info("种子数据已初始化")
    logger.info("应用启动完成，数据库：%s", settings.sqlalchemy_url.rsplit("@", 1)[-1])
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "可被自动化接口测试驱动的电商 demo 后端。\n\n"
        "- 业务链路：注册 → 登录 → 商品 → 购物车 → 下单 → 支付 → 确认收货 / 退款\n"
        "- 支付为内置模拟网关（`mock_result` 控制结果）\n"
        "- 种子账号：`admin/admin123`、`testuser/123456`\n"
        "- 测试用重置接口：`POST /api/v1/admin/reset`（需 TEST_MODE=true）"
    ),
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)


@app.exception_handler(BusinessError)
async def business_error_handler(_: Request, exc: BusinessError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": jsonable_encoder(exc.detail),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "detail": jsonable_encoder(exc.errors()),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(
    _: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": HTTP_CODE_MAP.get(exc.status_code, "HTTP_ERROR"),
            "message": str(exc.detail),
            "detail": None,
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理的异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "服务器内部错误", "detail": None},
    )


for router in (
    auth_router,
    catalog_router,
    cart_router,
    orders_router,
    payments_router,
    admin_router,
):
    app.include_router(router, prefix=API_PREFIX)


@app.get("/", tags=["系统"], summary="服务信息")
def root() -> dict:
    return {"name": settings.app_name, "version": app.version, "docs": "/docs"}


@app.get("/health", tags=["系统"], summary="健康检查")
def health(db: Session = Depends(get_db)) -> dict:
    database = "up"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database = "down"
    return {
        "status": "ok" if database == "up" else "degraded",
        "database": database,
        "test_mode": settings.test_mode,
        "version": app.version,
    }
