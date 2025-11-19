/**
 * HydroKGIntegrationService - 水电知识图谱集成服务
 * 提供水电场景与知识图谱的深度业务逻辑集成
 */

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..core.database import execute_neo4j_query, execute_postgres_query
from ..core.event_bus import publish_event, EventType
from ..core.security import validate_spatial_request, validate_coordinates
from ..core.cache import get_cache_manager

logger = logging.getLogger(__name__)

class HydroAnalysisType(Enum):
    """水电分析类型"""
    FLOOD_RISK = "flood_risk"
    MONITORING_STATIONS = "monitoring_stations"
    SPATIAL_RELATIONS = "spatial_relations"
    WATER_QUALITY = "water_quality"
    FLOW_ANALYSIS = "flow_analysis"
    RESERVOIR_MONITORING = "reservoir_monitoring"

class RiskLevel(Enum):
    """风险等级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class HydroSceneContext:
    """水电场景上下文"""
    scene_id: str
    location: Dict[str, float]  # lat, lng
    viewport: Dict[str, float]  # west, south, east, north
    active_layers: List[str]
    timestamp: datetime
    elevation_data: Optional[Dict[str, Any]] = None
    weather_data: Optional[Dict[str, Any]] = None

@dataclass
class KGInsight:
    """知识图谱洞察"""
    id: str
    type: str
    title: str
    description: str
    confidence: float
    data: Dict[str, Any]
    timestamp: datetime
    risk_level: RiskLevel = RiskLevel.LOW
    actionable: bool = False
    recommendations: List[str] = None

class HydroKGIntegrationService:
    """水电知识图谱集成服务"""

    def __init__(self):
        self.cache = get_cache_manager()
        self.risk_thresholds = {
            'rainfall': 50.0,  # mm/h
            'water_level': 2.0,  # meters above normal
            'flow_rate': 1000.0,  # m³/s
            'reservoir_level': 0.9  # 90% capacity
        }

    async def analyze_hydro_scene(self, scene_context: HydroSceneContext) -> List[KGInsight]:
        """分析水电场景并生成洞察"""
        insights = []

        try:
            # 验证输入
            if not self._validate_scene_context(scene_context):
                raise ValueError("Invalid scene context")

            logger.info(f"开始分析水电场景: {scene_context.scene_id}")

            # 并行执行多种分析
            analysis_tasks = [
                self._analyze_flood_risk(scene_context),
                self._analyze_monitoring_stations(scene_context),
                self._analyze_spatial_relations(scene_context),
                self._analyze_water_systems(scene_context),
                self._analyze_historical_patterns(scene_context)
            ]

            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"分析任务 {i} 失败: {result}")
                    continue

                if result:
                    insights.extend(result)

            # 生成综合洞察
            comprehensive_insight = await self._generate_comprehensive_insight(scene_context, insights)
            if comprehensive_insight:
                insights.insert(0, comprehensive_insight)

            # 缓存结果
            await self._cache_insights(scene_context.scene_id, insights)

            logger.info(f"水电场景分析完成: {len(insights)} 个洞察")

            return insights

        except Exception as e:
            logger.error(f"水电场景分析失败: {e}")
            return [self._create_error_insight(str(e))]

    async def _analyze_flood_risk(self, scene_context: HydroSceneContext) -> List[KGInsight]:
        """分析洪水风险"""
        insights = []

        try:
            # 查询知识图谱中的洪水风险区域
            flood_query = """
            MATCH (risk:FloodRisk)-[:LOCATED_AT]-(location:Location)
            WHERE location.longitude >= $west AND location.longitude <= $east
            AND location.latitude >= $south AND location.latitude <= $north
            AND risk.severity >= 2
            RETURN risk, location
            ORDER BY risk.severity DESC
            LIMIT 20
            """

            flood_results = await execute_neo4j_query(flood_query, {
                'west': scene_context.viewport['west'],
                'south': scene_context.viewport['south'],
                'east': scene_context.viewport['east'],
                'north': scene_context.viewport['north']
            })

            if flood_results:
                # 计算风险评分
                max_severity = max(result['risk'].get('severity', 0) for result in flood_results)
                avg_severity = sum(result['risk'].get('severity', 0) for result in flood_results) / len(flood_results)

                # 生成风险洞察
                if max_severity >= 3:  # 高风险
                    insight = KGInsight(
                        id=f"flood_risk_{scene_context.scene_id}_{datetime.now().timestamp()}",
                        type="flood_risk",
                        title="洪水高风险区域",
                        description=f"视口范围内发现 {len(flood_results)} 个高风险洪水区域，最高严重程度 {max_severity}",
                        confidence=0.85,
                        data={
                            "risk_areas": flood_results,
                            "max_severity": max_severity,
                            "avg_severity": avg_severity,
                            "total_areas": len(flood_results),
                            "viewport": scene_context.viewport
                        },
                        timestamp=datetime.utcnow(),
                        risk_level=RiskLevel.HIGH if max_severity >= 3 else RiskLevel.MEDIUM,
                        actionable=True,
                        recommendations=[
                            "建议启用实时洪水监测系统",
                            "关注气象预报和降雨预警",
                            "准备应急响应预案"
                        ]
                    )
                    insights.append(insight)

                    # 发布警报事件
                    await publish_event(
                        EventType.HYDRO_ALERT_TRIGGERED,
                        {
                            "alert_type": "flood_risk",
                            "severity": "high" if max_severity >= 3 else "medium",
                            "risk_areas": flood_results,
                            "scene_id": scene_context.scene_id,
                            "recommendations": insight.recommendations
                        }
                    )

            return insights

        except Exception as e:
            logger.error(f"洪水风险分析失败: {e}")
            return [self._create_error_insight(f"洪水风险分析失败: {e}")]

    async def _analyze_monitoring_stations(self, scene_context: HydroSceneContext) -> List[KGInsight]:
        """分析监测站点"""
        insights = []

        try:
            # 查询监测站点
            station_query = """
            MATCH (station:MonitoringStation)-[:LOCATED_AT]-(location:Location)
            WHERE location.longitude >= $west AND location.longitude <= $east
            AND location.latitude >= $south AND location.latitude <= $north
            AND station.type IN ['hydrology', 'meteorology', 'water_quality']
            RETURN station, location
            ORDER BY station.importance DESC, station.name ASC
            LIMIT 50
            """

            station_results = await execute_neo4j_query(station_query, {
                'west': scene_context.viewport['west'],
                'south': scene_context.viewport['south'],
                'east': scene_context.viewport['east'],
                'north': scene_context.viewport['north']
            })

            if station_results:
                # 按类型分类
                hydrology_stations = [s for s in station_results if s['station'].get('type') == 'hydrology']
                meteorology_stations = [s for s in station_results if s['station'].get('type') == 'meteorology']
                water_quality_stations = [s for s in station_results if s['station'].get('type') == 'water_quality']

                # 检查数据时效性
                outdated_stations = []
                for station in station_results:
                    last_update = station['station'].get('last_update')
                    if last_update:
                        try:
                            update_time = datetime.fromisoformat(last_update)
                            if datetime.utcnow() - update_time > timedelta(hours=24):
                                outdated_stations.append(station)
                        except:
                            pass

                # 生成监测洞察
                insight = KGInsight(
                    id=f"monitoring_{scene_context.scene_id}_{datetime.now().timestamp()}",
                    type="monitoring_stations",
                    title="监测站点分析",
                    description=f"视口范围内发现 {len(station_results)} 个监测站点，其中 {len(outdated_stations)} 个数据可能过时",
                    confidence=0.9,
                    data={
                        "total_stations": len(station_results),
                        "hydrology_stations": len(hydrology_stations),
                        "meteorology_stations": len(meteorology_stations),
                        "water_quality_stations": len(water_quality_stations),
                        "outdated_stations": len(outdated_stations),
                        "stations": station_results
                    },
                    timestamp=datetime.utcnow(),
                    risk_level=RiskLevel.MEDIUM if len(outdated_stations) > 0 else RiskLevel.LOW,
                    actionable=True,
                    recommendations=[
                        f"建议检查 {len(outdated_stations)} 个数据过时站点",
                        "确保关键监测站点正常运行",
                        "建立数据质量监控机制"
                    ] if outdated_stations else [
                        "所有监测站点数据正常",
                        "建议定期检查站点状态"
                    ]
                )
                insights.append(insight)

                # 发布数据更新事件
                await publish_event(
                    EventType.HYDRO_DATA_UPDATED,
                    {
                        "update_type": "stations_discovered",
                        "stations": station_results,
                        "outdated_count": len(outdated_stations),
                        "scene_id": scene_context.scene_id
                    }
                )

            return insights

        except Exception as e:
            logger.error(f"监测站点分析失败: {e}")
            return [self._create_error_insight(f"监测站点分析失败: {e}")]

    async def _analyze_spatial_relations(self, scene_context: HydroSceneContext) -> List[KGInsight]:
        """分析空间关系"""
        insights = []

        try:
            # 查询空间关系
            spatial_query = """
            MATCH (a)-[r:NEARBY|CONTAINS|FLOWS_INTO|CONTRIBUTES_TO]-(b)
            WHERE a.longitude >= $west AND a.longitude <= $east
            AND a.latitude >= $south AND a.latitude <= $north
            AND distance(
                point({longitude: a.longitude, latitude: a.latitude}),
                point({longitude: b.longitude, latitude: b.latitude})
            ) < $max_distance * 1000
            RETURN a, type(r) as relationship, b, r.distance_km as distance
            ORDER BY distance ASC
            LIMIT 100
            """

            spatial_results = await execute_neo4j_query(spatial_query, {
                'west': scene_context.viewport['west'],
                'south': scene_context.viewport['south'],
                'east': scene_context.viewport['east'],
                'north': scene_context.viewport['north'],
                'max_distance': 10  # 10km
            })

            if spatial_results:
                # 分析空间关系类型
                relation_types = {}
                for result in spatial_results:
                    rel_type = result['relationship']
                    relation_types[rel_type] = relation_types.get(rel_type, 0) + 1

                # 识别关键空间关系
                critical_relations = [r for r in spatial_results if r.get('relationship') in ['FLOWS_INTO', 'CONTRIBUTES_TO']]

                insight = KGInsight(
                    id=f"spatial_relations_{scene_context.scene_id}_{datetime.now().timestamp()}",
                    type="spatial_relations",
                    title="空间关系分析",
                    description=f"发现 {len(spatial_results)} 个空间关系，其中 {len(critical_relations)} 个为关键水文关系",
                    confidence=0.8,
                    data={
                        "total_relations": len(spatial_results),
                        "critical_relations": len(critical_relations),
                        "relation_types": relation_types,
                        "relations": spatial_results[:20]  # 限制显示数量
                    },
                    timestamp=datetime.utcnow(),
                    risk_level=RiskLevel.LOW,
                    actionable=True,
                    recommendations=[
                        "关注关键水文连接关系",
                        "分析上下游影响范围",
                        "建立空间关系监测机制"
                    ] if critical_relations else [
                        "空间关系正常",
                        "建议定期更新空间数据"
                    ]
                )
                insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"空间关系分析失败: {e}")
            return [self._create_error_insight(f"空间关系分析失败: {e}")]

    async def _analyze_water_systems(self, scene_context: HydroSceneContext) -> List[KGInsight]:
        """分析水系系统"""
        insights = []

        try:
            # 查询河流和水库系统
            water_system_query = """
            MATCH (water:WaterSystem)-[:LOCATED_AT]-(location:Location)
            WHERE location.longitude >= $west AND location.longitude <= $east
            AND location.latitude >= $south AND location.latitude <= $north
            RETURN water, location
            ORDER BY water.importance DESC
            LIMIT 30
            """

            water_results = await execute_neo4j_query(water_system_query, {
                'west': scene_context.viewport['west'],
                'south': scene_context.viewport['south'],
                'east': scene_context.viewport['east'],
                'north': scene_context.viewport['north']
            })

            if water_results:
                # 分析水系连通性
                connected_systems = [w for w in water_results if w['water'].get('connectivity_status') == 'connected']
                disconnected_systems = [w for w in water_results if w['water'].get('connectivity_status') == 'disconnected']

                insight = KGInsight(
                    id=f"water_systems_{scene_context.scene_id}_{datetime.now().timestamp()}",
                    type="water_systems",
                    title="水系系统分析",
                    description=f"发现 {len(water_results)} 个水系，其中 {len(connected_systems)} 个连通，{len(disconnected_systems)} 个断连",
                    confidence=0.85,
                    data={
                        "total_systems": len(water_results),
                        "connected_systems": len(connected_systems),
                        "disconnected_systems": len(disconnected_systems),
                        "systems": water_results
                    },
                    timestamp=datetime.utcnow(),
                    risk_level=RiskLevel.MEDIUM if disconnected_systems else RiskLevel.LOW,
                    actionable=True,
                    recommendations=[
                        f"关注 {len(disconnected_systems)} 个断连水系",
                        "评估水系连通性影响因素",
                        "制定水系修复计划"
                    ] if disconnected_systems else [
                        "水系连通性良好",
                        "建议定期监测水系状态"
                    ]
                )
                insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"水系系统分析失败: {e}")
            return [self._create_error_insight(f"水系系统分析失败: {e}")]

    async def _analyze_historical_patterns(self, scene_context: HydroSceneContext) -> List[KGInsight]:
        """分析历史模式"""
        insights = []

        try:
            # 查询历史洪水事件
            historical_query = """
            MATCH (event:HistoricalEvent)-[:OCCURRED_AT]-(location:Location)
            WHERE location.longitude >= $west AND location.longitude <= $east
            AND location.latitude >= $south AND location.latitude <= $north
            AND event.event_type IN ['flood', 'heavy_rain', 'dam_failure']
            AND event.date >= datetime().epochMillis - (365 * 24 * 60 * 60 * 1000)  // 最近一年
            RETURN event, location
            ORDER BY event.severity DESC, event.date DESC
            LIMIT 20
            """

            historical_results = await execute_neo4j_query(historical_query, {
                'west': scene_context.viewport['west'],
                'south': scene_context.viewport['south'],
                'east': scene_context.viewport['east'],
                'north': scene_context.viewport['north']
            })

            if historical_results:
                # 分析历史模式
                recent_events = [e for e in historical_results if e['event'].get('date')]
                severe_events = [e for e in historical_results if e['event'].get('severity', 0) >= 3]

                # 季节性分析
                seasonal_events = {}
                for event in historical_results:
                    try:
                        date_str = event['event'].get('date')
                        if date_str:
                            event_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            month = event_date.month
                            seasonal_events[month] = seasonal_events.get(month, 0) + 1
                    except:
                        pass

                # 找到高发季节
                peak_month = max(seasonal_events.items(), key=lambda x: x[1])[0] if seasonal_events else None

                insight = KGInsight(
                    id=f"historical_patterns_{scene_context.scene_id}_{datetime.now().timestamp()}",
                    type="historical_patterns",
                    title="历史模式分析",
                    description=f"最近一年发现 {len(historical_results)} 个历史事件，其中 {len(severe_events)} 个为严重事件",
                    confidence=0.8,
                    data={
                        "total_events": len(historical_results),
                        "severe_events": len(severe_events),
                        "recent_events": len(recent_events),
                        "seasonal_distribution": seasonal_events,
                        "peak_month": peak_month,
                        "events": historical_results
                    },
                    timestamp=datetime.utcnow(),
                    risk_level=RiskLevel.MEDIUM if severe_events else RiskLevel.LOW,
                    actionable=True,
                    recommendations=[
                        f"{peak_month}月为历史高发期，需特别关注" if peak_month else "",
                        f"关注历史严重事件区域",
                        "建立历史事件预警机制"
                    ] if peak_month or severe_events else [
                        "历史事件较少",
                        "建议继续收集历史数据"
                    ]
                )
                insights.append(insight)

            return insights

        except Exception as e:
            logger.error(f"历史模式分析失败: {e}")
            return [self._create_error_insight(f"历史模式分析失败: {e}")]

    async def _generate_comprehensive_insight(self, scene_context: HydroSceneContext, insights: List[KGInsight]) -> Optional[KGInsight]:
        """生成综合洞察"""
        if not insights:
            return None

        try:
            # 计算综合风险评分
            risk_scores = [insight.risk_level.value for insight in insights]
            avg_risk = sum(risk_scores) / len(risk_scores)
            max_risk = max(risk_scores)

            # 统计洞察类型
            insight_types = {}
            for insight in insights:
                insight_types[insight.type] = insight_types.get(insight.type, 0) + 1

            # 生成综合建议
            recommendations = []
            if max_risk >= RiskLevel.HIGH.value:
                recommendations.append("存在高风险因素，建议立即采取预防措施")
            if avg_risk >= RiskLevel.MEDIUM.value:
                recommendations.append("建议加强监测和预警")

            # 添加具体建议
            for insight in insights:
                if insight.recommendations:
                    recommendations.extend(insight.recommendations[:2])  # 限制数量

            # 去重
            recommendations = list(set(recommendations))

            return KGInsight(
                id=f"comprehensive_{scene_context.scene_id}_{datetime.now().timestamp()}",
                type="comprehensive_analysis",
                title="综合分析报告",
                description=f"基于知识图谱的水电场景分析完成，平均风险等级 {self._get_risk_level_name(RiskLevel(int(avg_risk)))}",
                confidence=0.9,
                data={
                    "total_insights": len(insights),
                    "risk_distribution": {
                        "low": sum(1 for r in risk_scores if r == RiskLevel.LOW.value),
                        "medium": sum(1 for r in risk_scores if r == RiskLevel.MEDIUM.value),
                        "high": sum(1 for r in risk_scores if r >= RiskLevel.HIGH.value)
                    },
                    "insight_types": insight_types,
                    "avg_risk_score": avg_risk,
                    "max_risk_score": max_risk
                },
                timestamp=datetime.utcnow(),
                risk_level=RiskLevel(int(avg_risk)),
                actionable=True,
                recommendations=recommendations[:5]  # 限制建议数量
            )

        except Exception as e:
            logger.error(f"综合洞察生成失败: {e}")
            return None

    def _validate_scene_context(self, scene_context: HydroSceneContext) -> bool:
        """验证场景上下文"""
        try:
            # 验证坐标
            if not validate_coordinates(scene_context.location['lat'], scene_context.location['lng']):
                return False

            # 验证视口
            viewport = scene_context.viewport
            if not validate_spatial_request({
                'west': viewport['west'],
                'south': viewport['south'],
                'east': viewport['east'],
                'north': viewport['north']
            }):
                return False

            # 验证时间戳
            if not isinstance(scene_context.timestamp, datetime):
                return False

            return True

        except Exception as e:
            logger.error(f"场景上下文验证失败: {e}")
            return False

    def _create_error_insight(self, error_message: str) -> KGInsight:
        """创建错误洞察"""
        return KGInsight(
            id=f"error_{datetime.now().timestamp()}",
            type="error",
            title="分析错误",
            description=f"分析过程中发生错误: {error_message}",
            confidence=0,
            data={"error": error_message},
            timestamp=datetime.utcnow(),
            risk_level=RiskLevel.CRITICAL,
            actionable=False,
            recommendations=["请检查系统状态并重试", "联系技术支持"]
        )

    def _get_risk_level_name(self, risk_level: RiskLevel) -> str:
        """获取风险等级名称"""
        risk_names = {
            RiskLevel.LOW: "低",
            RiskLevel.MEDIUM: "中等",
            RiskLevel.HIGH: "高",
            RiskLevel.CRITICAL: "严重"
        }
        return risk_names.get(risk_level, "未知")

    async def _cache_insights(self, scene_id: str, insights: List[KGInsight]) -> None:
        """缓存洞察结果"""
        try:
            cache_key = f"hydro_kg_insights:{scene_id}"
            insights_data = [
                {
                    "id": insight.id,
                    "type": insight.type,
                    "title": insight.title,
                    "description": insight.description,
                    "confidence": insight.confidence,
                    "data": insight.data,
                    "timestamp": insight.timestamp.isoformat(),
                    "risk_level": insight.risk_level.value,
                    "actionable": insight.actionable,
                    "recommendations": insight.recommendations
                }
                for insight in insights
            ]

            await self.cache.set_json(cache_key, insights_data, expire=3600)  # 缓存1小时

        except Exception as e:
            logger.warning(f"洞察缓存失败: {e}")

    async def get_cached_insights(self, scene_id: str) -> Optional[List[KGInsight]]:
        """获取缓存的洞察"""
        try:
            cache_key = f"hydro_kg_insights:{scene_id}"
            cached_data = await self.cache.get_json(cache_key)

            if cached_data:
                insights = []
                for item in cached_data:
                    insight = KGInsight(
                        id=item["id"],
                        type=item["type"],
                        title=item["title"],
                        description=item["description"],
                        confidence=item["confidence"],
                        data=item["data"],
                        timestamp=datetime.fromisoformat(item["timestamp"]),
                        risk_level=RiskLevel(item["risk_level"]),
                        actionable=item["actionable"],
                        recommendations=item["recommendations"]
                    )
                    insights.append(insight)
                return insights

        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")

        return None

    async def generate_real_time_alerts(self, scene_context: HydroSceneContext, current_data: Dict[str, Any]) -> List[KGInsight]:
        """生成实时警报"""
        alerts = []

        try:
            # 检查降雨量
            rainfall = current_data.get('rainfall', 0)
            if rainfall > self.risk_thresholds['rainfall']:
                alert = KGInsight(
                    id=f"rainfall_alert_{scene_context.scene_id}_{datetime.now().timestamp()}",
                    type="rainfall_alert",
                    title="降雨量警报",
                    description=f"当前降雨量 {rainfall}mm/h，超过阈值 {self.risk_thresholds['rainfall']}mm/h",
                    confidence=0.95,
                    data={
                        "current_rainfall": rainfall,
                        "threshold": self.risk_thresholds['rainfall'],
                        "severity": "high"
                    },
                    timestamp=datetime.utcnow(),
                    risk_level=RiskLevel.HIGH,
                    actionable=True,
                    recommendations=[
                        "立即启动防汛应急响应",
                        "通知下游地区做好准备",
                        "加强监测频率"
                    ]
                )
                alerts.append(alert)

                # 发布警报事件
                await publish_event(
                    EventType.HYDRO_ALERT_TRIGGERED,
                    {
                        "alert_type": "rainfall",
                        "severity": "high",
                        "current_value": rainfall,
                        "threshold": self.risk_thresholds['rainfall'],
                        "scene_id": scene_context.scene_id
                    }
                )

            # 检查水位
            water_level = current_data.get('water_level', 0)
            if water_level > self.risk_thresholds['water_level']:
                alert = KGInsight(
                    id=f"water_level_alert_{scene_context.scene_id}_{datetime.now().timestamp()}",
                    type="water_level_alert",
                    title="水位警报",
                    description=f"当前水位 {water_level}m，超过正常水位 {self.risk_thresholds['water_level']}m",
                    confidence=0.9,
                    data={
                        "current_level": water_level,
                        "threshold": self.risk_thresholds['water_level'],
                        "severity": "medium"
                    },
                    timestamp=datetime.utcnow(),
                    risk_level=RiskLevel.MEDIUM,
                    actionable=True,
                    recommendations=[
                        "加强水位监测",
                        "准备排涝措施",
                        "通知相关部门"
                    ]
                )
                alerts.append(alert)

            return alerts

        except Exception as e:
            logger.error(f"实时警报生成失败: {e}")
            return []

# 全局服务实例
hydro_kg_service = HydroKGIntegrationService()

async def analyze_hydro_scene_with_kg(scene_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """分析水电场景（供外部调用）"""
    try:
        # 转换场景上下文
        context = HydroSceneContext(
            scene_id=scene_context['scene_id'],
            location=scene_context['location'],
            viewport=scene_context['viewport'],
            active_layers=scene_context.get('active_layers', []),
            timestamp=datetime.fromisoformat(scene_context.get('timestamp', datetime.utcnow().isoformat()))
        )

        # 检查缓存
        cached_insights = await hydro_kg_service.get_cached_insights(context.scene_id)
        if cached_insights:
            logger.info(f"使用缓存的洞察结果: {context.scene_id}")
            return cached_insights

        # 执行分析
        insights = await hydro_kg_service.analyze_hydro_scene(context)
        return insights

    except Exception as e:
        logger.error(f"水电场景分析调用失败: {e}")
        return [hydro_kg_service._create_error_insight(str(e))]

async def generate_real_time_hydro_alerts(scene_context: Dict[str, Any], current_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """生成实时水电警报"""
    try:
        context = HydroSceneContext(
            scene_id=scene_context['scene_id'],
            location=scene_context['location'],
            viewport=scene_context['viewport'],
            active_layers=scene_context.get('active_layers', []),
            timestamp=datetime.fromisoformat(scene_context.get('timestamp', datetime.utcnow().isoformat()))
        )

        alerts = await hydro_kg_service.generate_real_time_alerts(context, current_data)
        return alerts

    except Exception as e:
        logger.error(f"实时警报生成调用失败: {e}")
        return []