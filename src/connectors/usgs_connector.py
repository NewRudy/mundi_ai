"""
USGS数据连接器
连接美国地质调查局水文数据
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import math
from .base_connector import BaseConnector, DataPoint, DataQuality

class USGSConnector(BaseConnector):
    """USGS数据连接器"""

    def __init__(self):
        super().__init__(
            name="usgs",
            base_url="https://waterservices.usgs.gov/nwis"
        )

        # USGS参数代码映射
        self.parameter_map = {
            '00065': {'name': 'water_level', 'unit': 'ft', 'description': '水位'},
            '00060': {'name': 'discharge', 'unit': 'ft³/s', 'description': '流量'},
            '00010': {'name': 'water_temperature', 'unit': '°C', 'description': '水温'},
            '63680': {'name': 'turbidity', 'unit': 'FNU', 'description': '浊度'},
            '72150': {'name': 'reservoir_storage', 'unit': 'acre-ft', 'description': '水库库容'},
            '00095': {'name': 'specific_conductance', 'unit': 'µS/cm', 'description': '电导率'},
            '00400': {'name': 'ph', 'unit': 'pH', 'description': 'pH值'},
            '00300': {'name': 'dissolved_oxygen', 'unit': 'mg/L', 'description': '溶解氧'}
        }

        # 水电专业站点映射（基于真实USGS站点）
        self.hydropower_sites = {
            'hoover_dam': {
                'upstream': '09404000',  # 胡佛水坝上游
                'downstream': '09404500',  # 胡佛水坝下游
                'colorado_river': '09405000'  # 科罗拉多河
            },
            'glen_canyon': {
                'upstream': '09380000',  # 格伦峡谷水坝上游
                'downstream': '09382000'   # 格伦峡谷水坝下游
            },
            'three_gorges': {
                'upstream': '三峡入库',  # 需要适配中国水利部API
                'downstream': '三峡出库'
            }
        }

    async def fetch_data(self, site_ids: List[str], time_range: str = 'P1D',
                        parameters: List[str] = None) -> Dict[str, List[DataPoint]]:
        """获取USGS实时数据"""

        if parameters is None:
            parameters = ['00065', '00060', '00010']  # 默认参数：水位、流量、水温

        all_data = {}

        for site_id in site_ids:
            try:
                # 构建API请求
                params = {
                    'sites': site_id,
                    'period': time_range,
                    'format': 'json',
                    'parameterCd': ','.join(parameters),
                    'siteStatus': 'active'
                }

                # 检查缓存
                cache_key = f"usgs_{site_id}_{time_range}_{','.join(parameters)}"
                cached_data = await self._get_from_cache(cache_key)
                if cached_data:
                    all_data[site_id] = cached_data
                    continue

                # 获取数据
                url = f"{self.base_url}/iv/"
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        raw_data = await response.json()
                        parsed_data = self.parse_data(raw_data)

                        # 缓存结果（5分钟）
                        await self._set_cache(cache_key, parsed_data, expire=300)

                        all_data[site_id] = parsed_data
                    else:
                        print(f"USGS API error for site {site_id}: {response.status}")
                        all_data[site_id] = []

            except Exception as e:
                print(f"Error fetching USGS data for site {site_id}: {e}")
                all_data[site_id] = []

        return all_data

    def parse_data(self, raw_data: dict) -> List[DataPoint]:
        """解析USGS数据格式"""

        data_points = []
        timeseries = raw_data.get('value', {}).get('timeSeries', [])

        for series in timeseries:
            # 获取参数信息
            param_code = series['variable']['variableCode'][0]['value']
            param_info = self.parameter_map.get(param_code, {'name': 'unknown', 'unit': 'unknown'})

            # 获取站点信息
            site_info = series.get('sourceInfo', {})
            site_name = site_info.get('siteName', 'Unknown Site')
            site_id = site_info.get('siteCode', [{}])[0].get('value', 'unknown')

            # 获取数据值
            if 'values' in series and len(series['values']) > 0:
                values = series['values'][0]['value']

                for value in values:
                    try:
                        # 解析时间戳
                        date_time_str = value['dateTime']
                        if date_time_str.endswith('Z'):
                            date_time_str = date_time_str[:-1] + '+00:00'
                        timestamp = datetime.fromisoformat(date_time_str)

                        # 解析数值
                        numeric_value = float(value['value'])

                        # 获取质量标识
                        quality_flags = value.get('qualifiers', [])
                        quality = self._parse_quality_flags(quality_flags)

                        # 创建数据点
                        data_point = DataPoint(
                            timestamp=timestamp,
                            value=numeric_value,
                            unit=param_info['unit'],
                            parameter_code=param_code,
                            source='usgs',
                            quality=quality,
                            metadata={
                                'site_name': site_name,
                                'site_id': site_id,
                                'parameter_name': param_info['name'],
                                'parameter_description': param_info['description'],
                                'quality_flags': quality_flags
                            }
                        )

                        data_points.append(data_point)

                    except (ValueError, KeyError) as e:
                        print(f"Error parsing USGS value: {e}")
                        continue

        return data_points

    def _parse_quality_flags(self, qualifiers: List[str]) -> int:
        """解析USGS质量标识"""
        if not qualifiers:
            return 100

        # USGS质量标识映射
        quality_map = {
            'A': 100,   # 优秀 - Approved
            'P': 80,    # 良好 - Provisional
            'E': 60,    # 一般 - Estimated
            'B': 40,    # 较差 - Backwater
            'I': 20,    # 差 - Ice affected
            'R': 10     # 极差 - Revised
        }

        for qualifier in qualifiers:
            if qualifier in quality_map:
                return quality_map[qualifier]

        return 90  # 默认良好

    def _is_value_valid(self, value: float, parameter_code: str) -> bool:
        """检查数值是否在合理范围内（水电专业标准）"""

        # 基础检查
        if math.isnan(value) or math.isinf(value):
            return False

        # 水电专业参数范围检查
        valid_ranges = {
            '00065': (-50, 1500),      # 水位: -50到1500英尺
            '00060': (0, 1000000),     # 流量: 0到100万立方英尺/秒
            '00010': (-5, 50),         # 水温: -5到50摄氏度
            '63680': (0, 1000),        # 浊度: 0到1000 FNU
            '72150': (0, 50000000),    # 水库库容: 0到5000万acre-ft
        }

        min_val, max_val = valid_ranges.get(parameter_code, (float('-inf'), float('inf')))
        return min_val <= value <= max_val

    async def get_hydropower_sites(self, region: str = 'us') -> Dict[str, List[str]]:
        """获取水电专业站点列表"""
        if region == 'us':
            return self.hydropower_sites.get('hoover_dam', {})
        elif region == 'china':
            # 这里需要连接中国水利部API
            return self.hydropower_sites.get('three_gorges', {})
        else:
            return {}

    async def get_data_summary(self, data_points: List[DataPoint]) -> Dict[str, any]:
        """获取数据摘要（复用父类方法）"""
        return await super().get_data_summary(data_points)

    async def _get_from_cache(self, key: str) -> Optional[List[DataPoint]]:
        """从缓存获取数据"""
        # 这里可以接入更复杂的缓存系统
        return self.cache.get(key)

    async def _set_cache(self, key: str, data: List[DataPoint], expire: int = 300) -> None:
        """设置缓存"""
        # 这里可以接入更复杂的缓存系统
        self.cache[key] = data

# 使用示例
async def test_usgs_connector():
    """测试USGS数据连接器"""
    async with USGSConnector() as connector:
        # 获取胡佛水坝数据
        data = await connector.fetch_data(
            site_ids=['09404000', '09404500'],
            time_range='P1D',
            parameters=['00065', '00060', '00010']
        )

        for site_id, points in data.items():
            print(f"站点 {site_id}: {len(points)} 个数据点")

            # 验证数据质量
            if points:
                quality = await connector.validate_data(points)
                print(f"数据质量评分: {quality.overall_score:.2f}")

                # 显示摘要
                summary = await connector.get_data_summary(points)
                print(f"数据摘要: {summary}")

if __name__ == "__main__":
    asyncio.run(test_usgs_connector())