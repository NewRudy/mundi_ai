"""
Orchestrator路由
将核心架构层暴露为FastAPI端点
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from pydantic import BaseModel
import json

from src.dependencies.session import verify_session_required
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])

# 禁用：这些依赖项不在当前设置中
# 请在完整的生产设置中启用

class UserQueryRequest(BaseModel):
    """用户查询请求"""
    query: str
    context: Optional[Dict[str, Any]] = {}

class TaskExecutionRequest(BaseModel):
    """任务执行请求"""
    tasks: List[Dict[str, Any]]

@router.post("/parse-query")
async def parse_user_query(
    request: UserQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """解析用户自然语言查询"""
    try:
        user_req = orchestrator.parse_user_request(request.query, **request.context)

        return {
            "success": True,
            "request_id": user_req.request_id,
            "query": user_req.user_query,
            "intent": user_req.context.get('intent', 'unknown'),
            "entities": user_req.context.get('entities', {}),
            "timestamp": user_req.timestamp.isoformat()
        }

    except Exception as e:
        logger.error(f"Parse query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/decompose-tasks")
async def decompose_tasks(
    request: UserQueryRequest,
    current_user: User = Depends(get_current_user)
):
    """将用户查询分解为可执行任务"""
    try:
        user_req = orchestrator.parse_user_request(request.query, **request.context)
        tasks = orchestrator.decompose_task(user_req)

        return {
            "success": True,
            "request_id": user_req.request_id,
            "task_count": len(tasks),
            "tasks": [
                {
                    "task_id": task.task_id,
                    "type": task.task_type,
                    "description": task.description,
                    "priority": task.priority,
                    "dependencies": task.dependencies
                }
                for task in tasks
            ]
        }

    except Exception as e:
        logger.error(f"Decompose tasks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute-workflow")
async def execute_workflow(
    request: UserQueryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """执行完整工作流（异步）"""
    try:
        user_req = orchestrator.parse_user_request(request.query, **request.context)
        tasks = orchestrator.decompose_task(user_req)

        # 异步执行任务
        background_tasks.add_task(_execute_workflow_background, tasks, user_req.request_id)

        return {
            "success": True,
            "request_id": user_req.request_id,
            "status": "started",
            "message": "Workflow execution started in background",
            "task_count": len(tasks)
        }

    except Exception as e:
        logger.error(f"Execute workflow error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _execute_workflow_background(tasks: List[Task], request_id: str):
    """后台执行工作流"""
    try:
        logger.info(f"Starting workflow execution for request {request_id}")
        result = await orchestrator.execute_tasks(tasks)
        logger.info(f"Workflow {request_id} completed: {result}")
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")

@router.get("/workflow-status/{request_id}")
async def get_workflow_status(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取工作流执行状态"""
    try:
        status = orchestrator.get_workflow_status()

        return {
            "success": True,
            "request_id": request_id,
            "status": status
        }

    except Exception as e:
        logger.error(f"Get workflow status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/data/load")
async def load_data(
    data_type: str,
    params: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """加载外部数据"""
    try:
        result = await context_manager.load_data(data_type, **params)

        return {
            "success": True,
            "data_type": data_type,
            "result": result
        }

    except Exception as e:
        logger.error(f"Load data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/model/call")
async def call_model(
    model_id: str,
    parameters: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """调用专业模型"""
    try:
        result = await mcp_client.call_model(model_id, **parameters)

        return {
            "success": True,
            "model_id": model_id,
            "result": result
        }

    except Exception as e:
        logger.error(f"Call model error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def get_available_models(
    current_user: User = Depends(get_current_user)
):
    """获取可用模型列表"""
    try:
        info = mcp_client.get_model_info()

        return {
            "success": True,
            "models": info.get('models', [])
        }

    except Exception as e:
        logger.error(f"Get models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/visualization/generate")
async def generate_visualization(
    viz_type: str,
    parameters: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """生成可视化"""
    try:
        result = await viz_orchestrator.generate_visualization(viz_type, **parameters)

        return {
            "success": True,
            "viz_type": viz_type,
            "result": result
        }

    except Exception as e:
        logger.error(f"Generate visualization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/report/generate")
async def generate_report(
    report_type: str,
    parameters: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """生成报告"""
    try:
        result = await viz_orchestrator.generate_report(report_type, **parameters)

        return {
            "success": True,
            "report_type": report_type,
            "result": result
        }

    except Exception as e:
        logger.error(f"Generate report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interaction/record")
async def record_interaction(
    user_id: str,
    interaction_type: str,
    target: str,
    context: Optional[Dict[str, Any]] = {},
    current_user: User = Depends(get_current_user)
):
    """记录用户交互"""
    try:
        interaction_id = interaction_handler.record_interaction(
            user_id=user_id,
            interaction_type=interaction_type,
            target=target,
            **context
        )

        return {
            "success": True,
            "interaction_id": interaction_id,
            "message": "Interaction recorded"
        }

    except Exception as e:
        logger.error(f"Record interaction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/interaction/suggestions")
async def get_suggestions(
    user_id: str,
    context: Optional[Dict[str, Any]] = {},
    current_user: User = Depends(get_current_user)
):
    """获取智能交互建议"""
    try:
        result = interaction_handler.generate_suggestions(user_id, context)

        return {
            "success": True,
            "user_id": user_id,
            "suggestions": result
        }

    except Exception as e:
        logger.error(f"Get suggestions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ui/adapt")
async def adapt_ui(
    user_id: str,
    current_state: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """自适应界面调整"""
    try:
        result = interaction_handler.adapt_interface(user_id, current_state)

        return {
            "success": True,
            "user_id": user_id,
            "adaptation": result
        }

    except Exception as e:
        logger.error(f"Adapt UI error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/stats")
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """获取缓存统计"""
    try:
        stats = context_manager.get_cache_stats()

        return {
            "success": True,
            "cache_stats": stats
        }

    except Exception as e:
        logger.error(f"Get cache stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cache/clear")
async def clear_cache(
    current_user: User = Depends(get_current_user)
):
    """清空缓存"""
    try:
        context_manager.clear_cache()

        return {
            "success": True,
            "message": "Cache cleared"
        }

    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
