"""
上下文管理器
管理外部数据源接入和上下文信息
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import aiohttp
import asyncpg

from ..connectors.base_connector import BaseConnector
from ..connectors.usgs_connector import USGSConnector


@dataclass
class DataSource:
    """数据源定义"""
    source_id: str
    source_type: str  # usgs, mwr, file, database, api
    name: str
    config: Dict[str, Any]
    last_sync: datetime = None
    sync_interval: int = 300  # 5分钟
    status: str = "active"  # active, inactive, error
    priority: int = 1

    def __post_init__(self):
        if self.last_sync is None:
            self.last_sync = datetime.now()


@dataclass
class ContextSession:
    """上下文会话"""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    context_data: Dict[str, Any] = field(default_factory=dict)
    active_data_sources: List[str] = field(default_factory=list)


class ContextManager:
    """上下文管理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 数据源管理
        self.data_sources: Dict[str, DataSource] = {}
        self.connectors: Dict[str, BaseConnector] = {}

        # 上下文会话管理
        self.sessions: Dict[str, ContextSession] = {}

        # 缓存管理
        self.cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}

        # 初始化默认数据源
        self._init_default_data_sources()

    def _init_default_data_sources(self):
        """初始化默认数据源"""
        # USGS数据源
        usgs_source = DataSource(
            source_id="usgs_default",
            source_type="usgs",
            name="USGS水文数据",
            config={
                'base_url': 'https://waterservices.usgs.gov',
                'format': 'json',
                'sites': ['01646500']  # Potomac River
            }
        )
        self.data_sources[usgs_source.source_id] = usgs_source
        self.connectors[usgs_source.source_id] = USGSConnector()

    async def load_data(self, data_type: str, **params) -> Dict[str, Any]:
        """
        加载数据

        Args:
            data_type: 数据类型
            **params: 参数

        Returns:
            加载的数据
        """
        self.logger.info(f"加载数据 - 类型: {data_type}, 参数: {params}")

        # 检查缓存
        cache_key = f"{data_type}:{json.dumps(params, sort_keys=True)}"
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            self.logger.info(f"从缓存获取数据: {cache_key}")
            return cached_data

        try:
            if data_type == "hydrological":
                result = await self._load_hydrological_data(**params)
            elif data_type == "reservoir":
                result = await self._load_reservoir_data(**params)
            elif data_type == "historical":
                result = await self._load_historical_data(**params)
            elif data_type == "realtime":
                result = await self._load_realtime_data(**params)
            elif data_type == "external_knowledge":
                result = self._load_external_knowledge(**params)
            else:
                result = {"status": "error", "message": f"不支持的数据类型: {data_type}"}

            # 存入缓存
            if result.get("status") == "success":
                self._set_cache(cache_key, result, ttl=300)  # 5分钟缓存

            return result

        except Exception as e:
            self.logger.error(f"数据加载失败: {e}")
            return {"status": "error", "message": str(e)}

    async def _load_hydrological_data(self, stations: List[str], parameters: List[str],
                                   time_range: Dict[str, str], **kwargs) -> Dict[str, Any]:
        """加载水文数据"""
        self.logger.info(f"加载水文数据 - 站点: {stations}, 参数: {parameters}")

        # 从USGS加载数据
        usgs_connector = self.connectors.get("usgs_default")
        if not usgs_connector:
            return {"status": "error", "message": "USGS连接器未配置"}

        all_data = {}
        for station_id in stations:
            try:
                # 转换为USGS站点ID格式
                if station_id == "potomac_river":
                    usgs_site_id = "01646500"
                elif station_id == "colorado_river":
                    usgs_site_id = "09380000"
                else:
                    usgs_site_id = station_id

                data = await usgs_connector.get_hydrological_data(usgs_site_id, parameters)
                all_data[station_id] = data
            except Exception as e:
                self.logger.error(f"加载站点 {station_id} 数据失败: {e}")

        return {
            "status": "success",
            "data": all_data,
            "source": "usgs",
            "loaded_at": datetime.now().isoformat()
        }

    async def _load_reservoir_data(self, reservoir_id: str, **kwargs) -> Dict[str, Any]:
        """加载水库数据"""
        self.logger.info(f"加载水库数据: {reservoir_id}")

        # 这里模拟水库数据，实际应用中应连接到水库数据库
        reservoir_data = {
            "reservoir_id": reservoir_id,
            "name": self._get_reservoir_name(reservoir_id),
            "current_level": 150.5,
            "capacity": 39300000000,  # 立方米（三峡为例）
            "inflow": 15000,  # m³/s
            "outflow": 12000,  # m³/s
            "storage_ratio": 0.75,  # 蓄水比例
            "last_updated": datetime.now().isoformat()
        }

        return {
            "status": "success",
            "data": reservoir_data
        }

    def _get_reservoir_name(self, reservoir_id: str) -> str:
        """获取水库名称"""
        name_map = {
            "three_gorges": "三峡水库",
            "hoover_dam": "胡佛水坝",
            "glen_canyon": "格伦峡谷水坝"
        }
        return name_map.get(reservoir_id, f"水库_{reservoir_id}")

    async def _load_historical_data(self, duration_days: int = 30, stations: List[str] = None,
                                 parameters: List[str] = None, **kwargs) -> Dict[str, Any]:
        """加载历史数据"""
        self.logger.info(f"加载历史数据 - 时长: {duration_days}天")

        # 生成模拟历史数据
        import pandas as pd
        import numpy as np

        end_date = datetime.now()
        start_date = end_date - timedelta(days=duration_days)

        date_range = pd.date_range(start=start_date, end=end_date, freq='H')

        historical_data = {}
        for station in (stations or ['potomac_river']):
            station_data = {
                'timestamps': date_range.tolist(),
                'water_level': (np.random.normal(10, 2, len(date_range)) + np.sin(np.arange(len(date_range)) * 0.1) * 10).tolist(),
                'discharge': (np.random.normal(1000, 200, len(date_range)) + np.cos(np.arange(len(date_range)) * 0.1) * 500).tolist(),
                'temperature': (np.random.normal(15, 3, len(date_range)) + np.sin(np.arange(len(date_range)) * 0.05) * 5).tolist()
            }
            historical_data[station] = station_data

        return {
            "status": "success",
            "data": historical_data,
            "duration_days": duration_days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }

    async def _load_realtime_data(self, stations: List[str], parameters: List[str], **kwargs) -> Dict[str, Any]:
        """加载实时数据"""
        self.logger.info(f"加载实时数据 - 站点: {stations}")

        # 从USGS获取实时数据
        return await self._load_hydrological_data(
            stations=stations,
            parameters=parameters,
            time_range={'start': 'latest', 'end': 'latest'}
        )

    def _load_external_knowledge(self, knowledge_type: str, query: str, **kwargs) -> Dict[str, Any]:
        """加载外部知识库数据"""
        self.logger.info(f"加载外部知识 - 类型: {knowledge_type}, 查询: {query}")

        # 模拟外部知识库查询
        knowledge_base = {
            "flood_protection": {
                "prevention_measures": ["加固堤坝", "疏通河道", "预泄腾库"],
                "emergency_response": ["人员疏散", "物资调配", "应急预案"],
                "case_studies": ["1998年长江洪水", "2005年卡特里娜", "2011年泰国洪水"]
            },
            "dam_safety": {
                "inspection_items": ["坝体裂缝", "渗漏", "位移监测", "渗压"],
                "safety_standards": ["设计标准", "运行规程", "应急预案"]
            },
            "hydrology_theory": {
                "flood_routing": ["圣维南方程组", "马斯京根法", "滞后演算法"],
                "design_flood": ["频率分析", "暴雨推求", "典型洪水"]
            }
        }

        result = knowledge_base.get(knowledge_type, {})

        return {
            "status": "success",
            "knowledge_type": knowledge_type,
            "query": query,
            "results": result,
            "confidence": 0.85
        }

    def create_session(self, user_id: str, **context) -> str:
        """
        创建上下文会话

        Args:
            user_id: 用户ID
            **context: 上下文数据

        Returns:
            会话ID
        """
        import uuid
        session_id = str(uuid.uuid4())

        session = ContextSession(
            session_id=session_id,
            user_id=user_id,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            context_data=context
        )

        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[ContextSession]:
        """获取会话"""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now()
        return session

    def update_session_context(self, session_id: str, **context):
        """更新会话上下文"""
        session = self.sessions.get(session_id)
        if session:
            session.context_data.update(context)
            session.last_activity = datetime.now()

    def get_session_context(self, session_id: str, key: str = None) -> Any:
        """获取会话上下文"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        if key:
            return session.context_data.get(key)
        return session.context_data

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if key in self.cache and key in self.cache_ttl:
            if datetime.now() < self.cache_ttl[key]:
                return self.cache[key]
            else:
                # 过期，删除
                del self.cache[key]
                del self.cache_ttl[key]
        return None

    def _set_cache(self, key: str, value: Any, ttl: int = 300):
        """设置缓存"""
        self.cache[key] = value
        self.cache_ttl[key] = datetime.now() + timedelta(seconds=ttl)

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        self.cache_ttl.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cache_size": len(self.cache),
            "entries": list(self.cache.keys())
        }

    def get_data_sources(self) -> List[Dict[str, Any]]:
        """获取数据源列表"""
        return [
            {
                "source_id": ds.source_id,
                "source_type": ds.source_type,
                "name": ds.name,
                "status": ds.status,
                "last_sync": ds.last_sync.isoformat() if ds.last_sync else None
            }
            for ds in self.data_sources.values()
        ]

    def add_data_source(self, data_source: DataSource):
        """添加数据源"""
        self.data_sources[data_source.source_id] = data_source

        # 根据类型创建连接器
        if data_source.source_type == "usgs":
            self.connectors[data_source.source_id] = USGSConnector()
        # 可以扩展其他连接器类型

    def remove_data_source(self, source_id: str):
        """删除数据源"""
        if source_id in self.data_sources:
            del self.data_sources[source_id]
        if source_id in self.connectors:
            del self.connectors[source_id]
