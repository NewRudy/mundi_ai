/**
 * 健康检查路由
 * 提供详细的服务健康状态
 */

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core.database import check_database_health, get_connection_pool_stats
from ..core.event_bus import check_event_bus_connection
from ..core.cache import get_cache_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthStatus(BaseModel):
    """健康状态"""
    status: str
    timestamp: str
    uptime_seconds: float
    version: str = "1.0.0"
    checks: Dict[str, Any]


class ServiceHealth(BaseModel):
    """服务健康详情"""
    service: str
    status: str
    last_check: str
    response_time_ms: float
    details: Dict[str, Any]


@router.get("/live")
async def liveness_probe():
    """Kubernetes存活探针"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "service": "kg-service"
    }


@router.get("/ready")
async def readiness_probe():
    """Kubernetes就绪探针"""
    try:
        # 检查关键依赖
        checks = {}

        # 数据库健康检查
        db_health = await check_database_health()
        checks["database"] = db_health

        # 事件总线健康检查
        event_bus_healthy = await check_event_bus_connection()
        checks["event_bus"] = {"status": "healthy" if event_bus_healthy else "unhealthy"}

        # 缓存健康检查
        try:
            cache_manager = get_cache_manager()
            await cache_manager.redis.ping()
            checks["cache"] = {"status": "healthy"}
        except Exception as e:
            checks["cache"] = {"status": "unhealthy", "error": str(e)}

        # 总体状态判断
        all_healthy = all(
            check.get("status") == "healthy" or
            all(sub_check.get("status") == "healthy" for sub_check in check.values() if isinstance(check, dict))
            for check in checks.values()
        )

        status = "ready" if all_healthy else "not_ready"

        return {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "checks": checks
        }

    except Exception as e:
        logger.error(f"❌ 就绪探针失败: {e}")
        return {
            "status": "not_ready",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


@router.get("/startup")
async def startup_probe():
    """Kubernetes启动探针"""
    return {
        "status": "started",
        "timestamp": datetime.now().isoformat(),
        "service": "kg-service"
    }


@router.get("/detailed")
async def detailed_health_check():
    """详细健康检查"""
    try:
        start_time = datetime.now()

        # 数据库详细检查
        db_stats = await get_connection_pool_stats()
        db_health = await check_database_health()

        # 事件总线检查
        event_bus_healthy = await check_event_bus_connection()

        # 缓存检查
        cache_status = {"status": "unknown"}
        try:
            cache_manager = get_cache_manager()
            await cache_manager.redis.ping()
            cache_status = {"status": "healthy"}
        except Exception as e:
            cache_status = {"status": "unhealthy", "error": str(e)}

        response_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "response_time_ms": round(response_time, 2),
            "services": {
                "database": {
                    "status": "healthy" if all(check.get("status") == "healthy" for check in db_health.values()) else "unhealthy",
                    "stats": db_stats,
                    "health": db_health
                },
                "event_bus": {
                    "status": "healthy" if event_bus_healthy else "unhealthy",
                    "connected": event_bus_healthy
                },
                "cache": cache_status
            }
        }

    except Exception as e:
        logger.error(f"❌ 详细健康检查失败: {e}")
        raise HTTPException(status_code=503, detail=f"健康检查失败: {str(e)}")


@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus指标端点"""
    try:
        # 获取连接池统计
        db_stats = await get_connection_pool_stats()

        # 构建Prometheus格式的指标
        metrics = f"""
# HELP kg_service_health_status KG服务健康状态
# TYPE kg_service_health_status gauge
kg_service_health_status 1

# HELP kg_database_connections_active 活跃数据库连接数
# TYPE kg_database_connections_active gauge
kg_database_connections_active {db_stats.get('postgres', {}).get('active_connections', 0)}

# HELP kg_database_connections_idle 空闲数据库连接数
# TYPE kg_database_connections_idle gauge
kg_database_connections_idle {db_stats.get('postgres', {}).get('idle_connections', 0)}

# HELP kg_database_pool_size 数据库连接池大小
# TYPE kg_database_pool_size gauge
kg_database_pool_size {db_stats.get('postgres', {}).get('pool_size', 0)}

# HELP kg_service_uptime_seconds 服务运行时间（秒）
# TYPE kg_service_uptime_seconds gauge
kg_service_uptime_seconds {(datetime.now() - datetime.fromtimestamp(0)).total_seconds()}
"""

        return Response(
            content=metrics.strip(),
            media_type="text/plain"
        )

    except Exception as e:
        logger.error(f"❌ 指标端点失败: {e}")
        return Response(
            content=f"# Error generating metrics: {e}",
            media_type="text/plain",
            status_code=500
        )


# 健康检查装饰器（可用于其他路由）
def require_service_healthy(func):
    """要求服务健康的装饰器"""
    async def wrapper(*args, **kwargs):
        # 快速健康检查
        try:
            from ..core.database import check_db_connection
            if not await check_db_connection():
                raise HTTPException(status_code=503, detail="数据库连接不可用")
        except Exception as e:
            logger.error(f"❌ 服务健康检查失败: {e}")
            raise HTTPException(status_code=503, detail="服务不可用")

        return await func(*args, **kwargs)
    return wrapper


# 健康检查服务类
class HealthCheckService:
    """健康检查服务"""

    def __init__(self):
        self.start_time = datetime.now()
        self.check_history = []

    async def perform_health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        check_result = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {}
        }

        try:
            # 数据库检查
            db_healthy = await check_db_connection()
            check_result["checks"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "connected": db_healthy
            }

            # 事件总线检查
            from ..core.event_bus import check_event_bus_connection
            event_bus_healthy = await check_event_bus_connection()
            check_result["checks"]["event_bus"] = {
                "status": "healthy" if event_bus_healthy else "unhealthy",
                "connected": event_bus_healthy
            }

            # 总体状态
            all_healthy = db_healthy and event_bus_healthy
            check_result["status"] = "healthy" if all_healthy else "unhealthy"

        except Exception as e:
            check_result["status"] = "unhealthy"
            check_result["error"] = str(e)

        # 记录历史
        self.check_history.append(check_result)
        if len(self.check_history) > 100:  # 保留最近100条记录
            self.check_history.pop(0)

        return check_result

    def get_uptime_seconds(self) -> float:
        """获取运行时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()

    def get_check_history(self, limit: int = 10) -> list:
        """获取健康检查历史"""
        return self.check_history[-limit:]


# 全局健康检查服务
health_service = HealthCheckService()


# 启动时注册健康检查
@router.on_event("startup")
async def startup_health_check():
    """启动健康检查"""
    logger.info("🚀 健康检查服务启动")


@router.on_event("shutdown")
async def shutdown_health_check():
    """关闭健康检查"""
    logger.info("🛑 健康检查服务关闭")"}