"""
基础数据连接器
提供数据连接器的通用功能和接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import aiohttp
import json
from dataclasses import dataclass

@dataclass
class DataPoint:
    """标准数据点格式"""
    timestamp: datetime
    value: float
    unit: str
    parameter_code: str
    source: str
    quality: int = 100
    metadata: Dict[str, Any] = None

@dataclass
class DataQuality:
    """数据质量评估结果"""
    completeness: float
    accuracy: float
    consistency: float
    timeliness: float
    overall_score: float
    issues: List[str] = None

class BaseConnector(ABC):
    """基础数据连接器类"""

    def __init__(self, name: str, base_url: str = None):
        self.name = name
        self.base_url = base_url
        self.session = None
        self.cache = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        await self._setup_cache()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def _setup_cache(self):
        """设置缓存机制"""
        # 这里可以接入现有的缓存系统
        self.cache = {}

    @abstractmethod
    async def fetch_data(self, identifiers: List[str], **kwargs) -> Dict[str, List[DataPoint]]:
        """获取数据 - 子类必须实现"""
        pass

    @abstractmethod
    def parse_data(self, raw_data: Any) -> List[DataPoint]:
        """解析原始数据 - 子类必须实现"""
        pass

    async def validate_data(self, data_points: List[DataPoint]) -> DataQuality:
        """验证数据质量"""
        if not data_points:
            return DataQuality(0, 0, 0, 0, 0, ["No data points"])

        # 完整性检查
        completeness = len([dp for dp in data_points if dp.quality > 0]) / len(data_points)

        # 准确性检查（基于数值范围）
        accuracy = self._check_accuracy(data_points)

        # 一致性检查（基于时间连续性）
        consistency = self._check_consistency(data_points)

        # 时效性检查
        timeliness = self._check_timeliness(data_points)

        # 总体评分
        overall_score = (completeness + accuracy + consistency + timeliness) / 4

        issues = []
        if completeness < 0.9:
            issues.append(f"Data completeness is {completeness:.2f}")
        if accuracy < 0.8:
            issues.append(f"Data accuracy is {accuracy:.2f}")
        if consistency < 0.8:
            issues.append(f"Data consistency is {consistency:.2f}")
        if timeliness < 0.8:
            issues.append(f"Data timeliness is {timeliness:.2f}")

        return DataQuality(completeness, accuracy, consistency, timeliness, overall_score, issues)

    def _check_accuracy(self, data_points: List[DataPoint]) -> float:
        """检查数据准确性"""
        valid_points = 0
        for dp in data_points:
            if self._is_value_valid(dp.value, dp.parameter_code):
                valid_points += 1
        return valid_points / len(data_points) if data_points else 0

    def _is_value_valid(self, value: float, parameter_code: str) -> bool:
        """检查数值是否在合理范围内"""
        # 子类可以重写此方法，提供特定参数的有效性检查
        return not (math.isnan(value) or math.isinf(value))

    def _check_consistency(self, data_points: List[DataPoint]) -> float:
        """检查数据一致性"""
        if len(data_points) < 2:
            return 1.0

        # 检查时间连续性
        sorted_points = sorted(data_points, key=lambda x: x.timestamp)
        time_gaps = []
        for i in range(1, len(sorted_points)):
            gap = (sorted_points[i].timestamp - sorted_points[i-1].timestamp).total_seconds()
            time_gaps.append(gap)

        if not time_gaps:
            return 1.0

        # 检查是否有异常大的时间间隔
        max_reasonable_gap = 3600  # 1小时
        consistent_gaps = sum(1 for gap in time_gaps if gap <= max_reasonable_gap)
        return consistent_gaps / len(time_gaps)

    def _check_timeliness(self, data_points: List[DataPoint]) -> float:
        """检查数据时效性"""
        if not data_points:
            return 0.0

        from datetime import timezone
        now = datetime.now(timezone.utc)
        max_age = timedelta(hours=24)  # 24小时内为及时

        timely_points = sum(1 for dp in data_points if (now - dp.timestamp) <= max_age)
        return timely_points / len(data_points)

    async def get_data_summary(self, data_points: List[DataPoint]) -> Dict[str, Any]:
        """获取数据摘要"""
        if not data_points:
            return {"count": 0, "time_range": None, "parameters": []}

        return {
            "count": len(data_points),
            "time_range": {
                "start": min(dp.timestamp for dp in data_points).isoformat(),
                "end": max(dp.timestamp for dp in data_points).isoformat()
            },
            "parameters": list(set(dp.parameter_code for dp in data_points)),
            "quality_score": (await self.validate_data(data_points)).overall_score,
            "source": self.name
        }