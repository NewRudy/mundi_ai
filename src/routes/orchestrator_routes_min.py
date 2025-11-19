"""
Orchestrator路由 (最小化实现)
"""
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])

@router.get("/health")
async def health():
    return {"status": "ok", "service": "orchestrator"}
