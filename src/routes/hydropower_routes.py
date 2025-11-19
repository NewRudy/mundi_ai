"""
水电专业路由
提供水电工程相关的API端点
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/hydropower", tags=["hydropower"])


@router.get("/health")
async def get_health():
    """健康检查端点"""
    return {
        "success": True,
        "status": "healthy",
        "message": "Hydropower service is running"
    }
