/**
 * KG服务核心路由
 * 提供松耦合的REST API接口
 */

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request
from pydantic import BaseModel, Field

from ..core.event_bus import EventType, publish_event, get_event_bus
from ..core.database import execute_neo4j_query, execute_postgres_query
from ..core.cache import get_cache_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# 请求/响应模型

class KGSearchRequest(BaseModel):
    """KG搜索请求"""
    query: str = Field(..., description="搜索查询")
    node_types: Optional[List[str]] = Field(None, description="节点类型过滤")
    limit: int = Field(50, ge=1, le=1000, description="结果数量限制")
    include_relationships: bool = Field(True, description="是否包含关系")


class KGSearchResponse(BaseModel):
    """KG搜索响应"""
    request_id: str
    results: List[Dict[str, Any]]
    total_count: int
    execution_time_ms: float


class SpatialAnalysisRequest(BaseModel):
    """空间分析请求"""
    west: float = Field(..., description="西边界")
    south: float = Field(..., description="南边界")
    east: float = Field(..., description="东边界")
    north: float = Field(..., description="北边界")
    analysis_type: str = Field("hydro_monitoring", description="分析类型")
    max_distance_km: float = Field(10.0, description="最大分析距离(km)")


class SpatialAnalysisResponse(BaseModel):
    """空间分析响应"""
    request_id: str
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    execution_time_ms: float


class HydroKGQueryRequest(BaseModel):
    """水电KG查询请求"""
    query_type: str = Field(..., description="查询类型: monitoring_stations, flood_risk, spatial_relations")
    location: Dict[str, float] = Field(..., description="查询位置 {lat, lng}")
    radius_km: float = Field(5.0, ge=0.1, le=50.0, description="查询半径(km)")
    time_window: Optional[str] = Field(None, description="时间窗口，如 '24h', '7d'")


class HydroKGQueryResponse(BaseModel):
    """水电KG查询响应"""
    request_id: str
    query_type: str
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    execution_time_ms: float


# 路由定义

@router.get("/health")
async def health_check():
    """KG服务健康检查"""
    return {
        "service": "kg-service",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/search", response_model=KGSearchResponse)
async def search_knowledge_graph(
    request: KGSearchRequest,
    background_tasks: BackgroundTasks
):
    """搜索知识图谱"""
    try:
        request_id = f"kg_search_{datetime.now().timestamp()}"
        start_time = datetime.now()

        logger.info(f"🔍 KG搜索请求: {request.query}")

        # 基础Cypher查询
        query = """
        CALL db.index.fulltext.queryNodes('nodeIndex', $query) YIELD node, score
        WHERE score > 0.5
        RETURN node, score
        ORDER BY score DESC
        LIMIT $limit
        """

        parameters = {
            "query": request.query,
            "limit": request.limit
        }

        # 执行查询
        results = await execute_neo4j_query(query, parameters)

        # 如果包含关系，查询相关关系
        if request.include_relationships and results:
            node_ids = [record['node']['id'] for record in results[:10]]  # 限制前10个节点
            relationships = await _get_node_relationships(node_ids)

            # 合并结果
            for i, record in enumerate(results):
                if i < len(relationships):
                    record['relationships'] = relationships[i]

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(f"✅ KG搜索完成: {len(results)} 个结果")

        return KGSearchResponse(
            request_id=request_id,
            results=results,
            total_count=len(results),
            execution_time_ms=execution_time
        )

    except Exception as e:
        logger.error(f"❌ KG搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/spatial-analysis", response_model=SpatialAnalysisResponse)
async def analyze_spatial_data(
    request: SpatialAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """分析空间数据"""
    try:
        request_id = f"spatial_analysis_{datetime.now().timestamp()}"
        start_time = datetime.now()

        logger.info(f"🌍 空间分析请求: {request.analysis_type}")

        # 根据分析类型执行不同的查询
        if request.analysis_type == "hydro_monitoring":
            results = await _analyze_hydro_monitoring_stations(request)
        elif request.analysis_type == "flood_risk":
            results = await _analyze_flood_risk_areas(request)
        elif request.analysis_type == "spatial_relations":
            results = await _analyze_spatial_relations(request)
        else:
            raise HTTPException(status_code=400, detail="不支持的分析类型")

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        # 生成摘要
        summary = {
            "total_features": len(results),
            "analysis_type": request.analysis_type,
            "bounds": {
                "west": request.west,
                "south": request.south,
                "east": request.east,
                "north": request.north
            },
            "max_distance_km": request.max_distance_km
        }

        logger.info(f"✅ 空间分析完成: {len(results)} 个特征")

        return SpatialAnalysisResponse(
            request_id=request_id,
            results=results,
            summary=summary,
            execution_time_ms=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 空间分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/hydro-query", response_model=HydroKGQueryResponse)
async def query_hydro_knowledge(
    request: HydroKGQueryRequest,
    background_tasks: BackgroundTasks
):
    """水电知识图谱查询"""
    try:
        request_id = f"hydro_kg_query_{datetime.now().timestamp()}"
        start_time = datetime.now()

        logger.info(f"🌊 水电KG查询: {request.query_type}")

        # 根据查询类型执行不同的逻辑
        if request.query_type == "monitoring_stations":
            results = await _query_monitoring_stations(request)
        elif request.query_type == "flood_risk":
            results = await _query_flood_risk_areas(request)
        elif request.query_type == "spatial_relations":
            results = await _query_spatial_relations(request)
        else:
            raise HTTPException(status_code=400, detail="不支持的查询类型")

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        # 生成元数据
        metadata = {
            "query_location": request.location,
            "radius_km": request.radius_km,
            "time_window": request.time_window,
            "result_count": len(results)
        }

        logger.info(f"✅ 水电KG查询完成: {len(results)} 个结果")

        return HydroKGQueryResponse(
            request_id=request_id,
            query_type=request.query_type,
            results=results,
            metadata=metadata,
            execution_time_ms=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 水电KG查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/hydro/stations")
async def get_hydro_stations(
    lat: float = Query(..., description="纬度"),
    lng: float = Query(..., description="经度"),
    radius_km: float = Query(5.0, description="查询半径(km)"),
    station_type: Optional[str] = Query(None, description="站点类型")
):
    """获取水电监测站点"""
    try:
        # Cypher查询获取监测站点
        query = """
        MATCH (station:MonitoringStation)-[:LOCATED_AT]-(location:Location)
        WHERE point({longitude: $lng, latitude: $lat}) \u003c-[:LOCATED_AT]-(location)
        AND distance(point({longitude: location.longitude, latitude: location.latitude}),
                     point({longitude: $lng, latitude: $lat})) \u003c $radius_km * 1000
        """

        if station_type:
            query += " AND station.type = $station_type"

        query += """
        RETURN station, location
        ORDER BY distance ASC
        """

        parameters = {
            "lat": lat,
            "lng": lng,
            "radius_km": radius_km,
            "station_type": station_type
        }

        results = await execute_neo4j_query(query, parameters)

        return {
            "stations": results,
            "total_count": len(results),
            "query_bounds": {
                "center": {"lat": lat, "lng": lng},
                "radius_km": radius_km
            }
        }

    except Exception as e:
        logger.error(f"❌ 获取监测站点失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取站点失败: {str(e)}")


@router.post("/events/publish")
async def publish_event_endpoint(
    event_type: str,
    payload: Dict[str, Any],
    source: str = "kg-service",
    correlation_id: Optional[str] = None,
    reply_to: Optional[str] = None
):
    """发布事件（用于测试和集成）"""
    try:
        event_type_enum = EventType(event_type)
        event_id = await publish_event(
            event_type_enum,
            payload,
            source=source,
            correlation_id=correlation_id,
            reply_to=reply_to
        )

        return {
            "event_id": event_id,
            "event_type": event_type,
            "status": "published"
        }

    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的事件类型: {event_type}")
    except Exception as e:
        logger.error(f"❌ 发布事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")


# 私有辅助函数

async def _get_node_relationships(node_ids: list[str]) -> list:
    """获取节点关系"""
    if not node_ids:
        return []

    query = """
    UNWIND $node_ids as node_id
    MATCH (node)-[r]-(related)
    WHERE node.id = node_id
    RETURN node_id, collect({
        relationship: type(r),
        related_node: related,
        properties: properties(r)
    }) as relationships
    """

    parameters = {"node_ids": node_ids}
    results = await execute_neo4j_query(query, parameters)

    return [record["relationships"] for record in results]


async def _analyze_hydro_monitoring_stations(request: SpatialAnalysisRequest) -> list:
    """分析水电监测站点"""
    query = """
    MATCH (station:MonitoringStation)-[:LOCATED_AT]-(location:Location)
    WHERE location.longitude \u003e= $west AND location.longitude \u003c= $east
    AND location.latitude \u003e= $south AND location.latitude \u003c= $north
    AND station.type IN ['hydrology', 'meteorology', 'dam']
    RETURN station, location
    """

    parameters = {
        "west": request.west,
        "south": request.south,
        "east": request.east,
        "north": request.north
    }

    return await execute_neo4j_query(query, parameters)


async def _analyze_flood_risk_areas(request: SpatialAnalysisRequest) -> list:
    """分析洪水风险区域"""
    query = """
    MATCH (risk:FloodRisk)-[:LOCATED_AT]-(location:Location)
    WHERE location.longitude \u003e= $west AND location.longitude \u003c= $east
    AND location.latitude \u003e= $south AND location.latitude \u003c= $north
    AND risk.severity \u003e= 2  # 中等及以上风险
    RETURN risk, location
    ORDER BY risk.severity DESC
    """

    parameters = {
        "west": request.west,
        "south": request.south,
        "east": request.east,
        "north": request.north
    }

    return await execute_neo4j_query(query, parameters)


async def _analyze_spatial_relations(request: SpatialAnalysisRequest) -> list:
    """分析空间关系"""
    query = """
    MATCH (a)-[r:NEARBY|CONTAINS|INTERSECTS]-(b)
    WHERE a.longitude \u003e= $west AND a.longitude \u003c= $east
    AND a.latitude \u003e= $south AND a.latitude \u003c= $north
    AND distance(
        point({longitude: a.longitude, latitude: a.latitude}),
        point({longitude: b.longitude, latitude: b.latitude})
    ) \u003c $max_distance_km * 1000
    RETURN a, type(r) as relationship, b, r.distance_km as distance
    ORDER BY distance ASC
    """

    parameters = {
        "west": request.west,
        "south": request.south,
        "east": request.east,
        "north": request.north,
        "max_distance_km": request.max_distance_km
    }

    return await execute_neo4j_query(query, parameters)


async def _query_monitoring_stations(request: HydroKGQueryRequest) -> list:
    """查询监测站点"""
    # 简化实现 - 实际应用中需要更复杂的空间查询
    query = """
    MATCH (station:MonitoringStation)-[:LOCATED_AT]-(location:Location)
    WHERE station.type = 'hydrology'
    RETURN station, location
    LIMIT 50
    """

    return await execute_neo4j_query(query)


async def _query_flood_risk_areas(request: HydroKGQueryRequest) -> list:
    """查询洪水风险区域"""
    query = """
    MATCH (area:FloodRiskArea)-[:LOCATED_AT]-(location:Location)
    WHERE area.risk_level \u003e= 2
    RETURN area, location
    ORDER BY area.risk_level DESC
    LIMIT 50
    """

    return await execute_neo4j_query(query)


async def _query_spatial_relations(request: HydroKGQueryRequest) -> list:
    """查询空间关系"""
    query = """
    MATCH (a)-[r:FLOWS_INTO|CONTRIBUTES_TO]-(b)
    WHERE a.type = 'river' AND b.type = 'river'
    RETURN a, type(r) as relationship, b
    LIMIT 50
    """

    return await execute_neo4j_query(query)


# 事件处理器注册
@router.on_event("startup")
async def startup_event():
    """服务启动事件"""
    logger.info("🚀 KG服务路由启动完成")


@router.on_event("shutdown")
async def shutdown_event():
    """服务关闭事件"""
    logger.info("🛑 KG服务路由关闭完成")