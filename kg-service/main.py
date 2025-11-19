"""
KG服务主入口文件
松耦合的知识图谱微服务
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# 配置日志
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局应用实例
app: FastAPI = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    logger.info("🚀 启动KG服务...")

    try:
        # 初始化服务
        await initialize_services()
        logger.info("✅ KG服务初始化完成")
        yield
    except Exception as e:
        logger.error(f"❌ KG服务启动失败: {e}")
        raise
    finally:
        logger.info("🛑 关闭KG服务...")
        await shutdown_services()


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    global app

    app = FastAPI(
        title="Mundi.ai KG Service",
        description="松耦合知识图谱微服务",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 添加中间件
    setup_middleware(app)

    # 注册路由
    setup_routes(app)

    return app


def setup_middleware(app: FastAPI) -> None:
    """配置中间件"""

    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 在生产环境中需要配置具体的域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"],
    )

    # GZIP压缩
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 自定义中间件
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """添加处理时间头部"""
        import time
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Response-Time"] = f"{process_time:.3f}s"
        return response

    @app.middleware("http")
    async def add_request_id_header(request: Request, call_next):
        """添加请求ID头部"""
        import uuid
        request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def setup_routes(app: FastAPI) -> None:
    """注册路由"""

    # 健康检查
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "healthy",
            "service": "kg-service",
            "version": "1.0.0",
            "timestamp": asyncio.get_event_loop().time()
        }

    @app.get("/ready")
    async def readiness_check():
        """就绪检查端点"""
        try:
            # 检查数据库连接
            from src.core.database import check_db_connection
            db_healthy = await check_db_connection()

            # 检查Redis连接
            from src.core.event_bus import check_event_bus_connection
            redis_healthy = await check_event_bus_connection()

            return {
                "status": "ready" if db_healthy and redis_healthy else "not_ready",
                "checks": {
                    "database": db_healthy,
                    "event_bus": redis_healthy
                }
            }
        except Exception as e:
            logger.error(f"就绪检查失败: {e}")
            return {
                "status": "not_ready",
                "error": str(e)
            }

    # API根路径
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "message": "Mundi.ai KG Service",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "ready": "/ready"
        }

    # 导入并注册主要路由
    try:
        from src.routes import kg_routes, health_routes, event_routes

        # 注册路由
        app.include_router(kg_routes.router, prefix="/api/kg", tags=["Knowledge Graph"])
        app.include_router(health_routes.router, prefix="/api/health", tags=["Health"])
        app.include_router(event_routes.router, prefix="/api/events", tags=["Events"])

        logger.info("✅ 路由注册完成")
    except ImportError as e:
        logger.error(f"❌ 路由注册失败: {e}")
        raise


async def initialize_services() -> None:
    """初始化服务"""
    try:
        # 初始化数据库连接
        from src.core.database import init_database
        await init_database()
        logger.info("✅ 数据库连接初始化完成")

        # 初始化事件总线
        from src.core.event_bus import init_event_bus
        await init_event_bus()
        logger.info("✅ 事件总线初始化完成")

        # 初始化缓存
        from src.core.cache import init_cache
        await init_cache()
        logger.info("✅ 缓存初始化完成")

        # 初始化其他服务...
        logger.info("✅ 所有服务初始化完成")

    except Exception as e:
        logger.error(f"❌ 服务初始化失败: {e}")
        raise


async def shutdown_services() -> None:
    """关闭服务"""
    try:
        # 关闭数据库连接
        from src.core.database import close_database
        await close_database()
        logger.info("✅ 数据库连接关闭完成")

        # 关闭事件总线
        from src.core.event_bus import close_event_bus
        await close_event_bus()
        logger.info("✅ 事件总线关闭完成")

        # 关闭缓存
        from src.core.cache import close_cache
        await close_cache()
        logger.info("✅ 缓存关闭完成")

        logger.info("✅ 所有服务关闭完成")

    except Exception as e:
        logger.error(f"❌ 服务关闭失败: {e}")


# 错误处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局错误处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": "服务器遇到了意外错误",
            "request_id": request.headers.get("X-Request-ID", "unknown"),
            "timestamp": asyncio.get_event_loop().time()
        }
    )


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    # 运行服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=int(os.getenv("WORKERS", "2")),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
        reload=False,  # 生产环境关闭reload
        timeout_keep_alive=30,
        timeout_notify=30
    )