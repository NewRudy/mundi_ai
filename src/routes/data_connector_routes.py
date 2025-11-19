"""
数据连接器路由
暴露所有数据连接器为FastAPI端点
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import io
import pandas as pd

from src.dependencies.session import verify_session_required
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["data-connectors"])

# 禁用：这些依赖项不在当前设置中

@router.get("/mwr/stations")
async def get_mwr_stations(
    current_user: User = Depends(get_current_user)
):
    """获取水利部水文站点列表"""
    try:
        stations = mwr_connector.get_supported_stations()

        return {
            "success": True,
            "source": "mwr",
            "stations": stations,
            "count": len(stations),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Get MWR stations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mwr/hydrological")
async def get_mwr_hydrological_data(
    station_id: str = Form(...),
    parameters: str = Form("water_level,discharge"),
    start_time: Optional[str] = Form(None),
    end_time: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """获取水利部水文数据"""
    try:
        param_list = parameters.split(",") if parameters else ['water_level', 'discharge']

        result = await mwr_connector.get_hydrological_data(
            station_id=station_id,
            parameters=param_list,
            start_time=start_time,
            end_time=end_time
        )

        if result.get('status') == 'success':
            return {
                "success": True,
                "source": "mwr",
                "data": result['data'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('message', 'Unknown error'))

    except Exception as e:
        logger.error(f"Get MWR hydrological data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mwr/reservoir")
async def get_mwr_reservoir_data(
    reservoir_id: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """获取水利部大型水库数据"""
    try:
        result = await mwr_connector.get_reservoir_data(reservoir_id)

        if result.get('status') == 'success':
            return {
                "success": True,
                "source": "mwr",
                "data": result['data'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('message', 'Unknown error'))

    except Exception as e:
        logger.error(f"Get MWR reservoir data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/file/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form("auto"),
    current_user: User = Depends(get_current_user)
):
    """上传文件（CSV/JSON/Excel）"""
    try:
        contents = await file.read()
        file_path = f"/tmp/{file.filename}"

        with open(file_path, 'wb') as f:
            f.write(contents)

        if file_type == "auto":
            file_type = await file_connector.detect_file_format(file_path)

        if file_type == 'csv':
            result = await file_connector.load_csv(file_path)
        elif file_type == 'json':
            result = await file_connector.load_json(file_path)
        elif file_type in ['excel', 'xlsx', 'xls']:
            result = await file_connector.load_excel(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

        if result.get('status') == 'success':
            return {
                "success": True,
                "file_name": file.filename,
                "format": result['format'],
                "data_summary": {
                    "rows": result['data'].get('rows', 0),
                    "columns": result['data'].get('columns', []),
                    "time_columns": result['data'].get('time_columns', []),
                    "numeric_columns": result['data'].get('numeric_columns', [])
                },
                "sample_data": result['data'].get('sample_data', []),
                "statistics": result['data'].get('statistics', {})
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('message', 'Unknown error'))

    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/file/parse-excel-sheet")
async def parse_excel_sheet(
    file: UploadFile = File(...),
    sheet_name: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """解析Excel特定Sheet"""
    try:
        contents = await file.read()
        file_path = f"/tmp/{file.filename}"

        with open(file_path, 'wb') as f:
            f.write(contents)

        result = await file_connector.load_excel(file_path, sheet_name=sheet_name)

        if result.get('status') == 'success':
            return {
                "success": True,
                "file_name": file.filename,
                "sheet_name": sheet_name,
                "data_summary": {
                    "rows": result['data'].get('rows', 0),
                    "columns": result['data'].get('columns', [])
                },
                "sample_data": result['data'].get('sample_data', [])
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('message', 'Unknown error'))

    except Exception as e:
        logger.error(f"Parse Excel sheet error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/knowledge/query")
async def query_knowledge(
    query: str = Form(...),
    source_ids: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """查询外部知识库"""
    try:
        source_list = source_ids.split(",") if source_ids else None

        result = await knowledge_connector.query_knowledge(query, source_ids=source_list)

        return {
            "success": True,
            "query": query,
            "results": result.get('results', []),
            "count": result.get('total_count', 0),
            "sources_queried": result.get('sources_queried', 0)
        }

    except Exception as e:
        logger.error(f"Query knowledge error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/flood-control")
async def get_flood_control_knowledge(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """获取防洪知识"""
    try:
        result = await knowledge_connector.get_flood_control_knowledge(query)

        return {
            "success": True,
            "type": result['type'],
            "content": result['content']
        }

    except Exception as e:
        logger.error(f"Get flood control knowledge error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/dam-safety")
async def get_dam_safety_guidelines(
    current_user: User = Depends(get_current_user)
):
    """获取大坝安全指南"""
    try:
        result = await knowledge_connector.get_dam_safety_guidelines()

        return {
            "success": True,
            "guidelines": result['guidelines'],
            "reference_standards": result['reference_standards']
        }

    except Exception as e:
        logger.error(f"Get dam safety guidelines error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mwr/health")
async def get_mwr_health(
    current_user: User = Depends(get_current_user)
):
    """检查水利部连接器健康状态"""
    try:
        is_healthy = await mwr_connector.connect()

        return {
            "success": True,
            "health": {
                "status": "healthy" if is_healthy else "unhealthy",
                "service": "mwr_api",
                "timestamp": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"MWR health check error: {e}")
        return {
            "success": False,
            "health": {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        }
