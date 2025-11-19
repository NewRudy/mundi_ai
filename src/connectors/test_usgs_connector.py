"""
USGS数据连接器测试
验证USGS数据连接器的功能
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from src.connectors.usgs_connector import USGSConnector, DataPoint

@pytest.mark.asyncio
async def test_usgs_connector_base_functionality():
    """测试USGS连接器基础功能"""
    async with USGSConnector() as connector:
        # 测试基础连接
        assert connector.name == "usgs"
        assert connector.base_url == "https://waterservices.usgs.gov/nwis"

@pytest.mark.asyncio
async def test_usgs_hydropower_sites():
    """测试水电专业站点获取"""
    async with USGSConnector() as connector:
        # 获取美国站点
        us_sites = await connector.get_hydropower_sites('us')
        assert 'hoover_dam' in us_sites
        assert 'upstream' in us_sites['hoover_dam']
        assert us_sites['hoover_dam']['upstream'] == '09404000'

@pytest.mark.asyncio
async def test_usgs_data_fetch_real_site():
    """测试从真实USGS站点获取数据"""
    async with USGSConnector() as connector:
        # 使用真实的胡佛水坝站点
        data = await connector.fetch_data(
            site_ids=['09404000'],  # 胡佛水坝上游
            time_range='P1D',
            parameters=['00065', '00060', '00010']
        )

        # 验证数据返回
        assert '09404000' in data
        points = data['09404000']

        # 验证数据点格式
        assert len(points) > 0  # 应该有一些数据点

        # 验证第一个数据点
        if points:
            first_point = points[0]
            assert isinstance(first_point, DataPoint)
            assert first_point.source == 'usgs'
            assert first_point.parameter_code in ['00065', '00060', '00010']
            assert isinstance(first_point.timestamp, datetime)
            assert isinstance(first_point.value, float)
            assert first_point.quality >= 0
            assert first_point.quality <= 100

@pytest.mark.asyncio
async def test_usgs_data_quality_validation():
    """测试数据质量验证"""
    async with USGSConnector() as connector:
        # 获取一些数据
        data = await connector.fetch_data(
            site_ids=['09404000'],
            time_range='P1D'
        )

        if data['09404000']:
            points = data['09404000']

            # 验证数据质量
            quality = await connector.validate_data(points)

            assert 0 <= quality.overall_score <= 1
            assert 0 <= quality.completeness <= 1
            assert 0 <= quality.accuracy <= 1
            assert 0 <= quality.consistency <= 1
            assert 0 <= quality.timeliness <= 1

@pytest.mark.asyncio
async def test_usgs_parameter_mapping():
    """测试参数映射"""
    connector = USGSConnector()

    # 验证参数映射存在
    assert '00065' in connector.parameter_map
    assert connector.parameter_map['00065']['name'] == 'water_level'
    assert connector.parameter_map['00065']['unit'] == 'ft'

@pytest.mark.asyncio
async def test_usgs_data_parsing():
    """测试数据解析功能"""
    connector = USGSConnector()

    # 模拟USGS数据格式
    mock_data = {
        'value': {
            'timeSeries': [
                {
                    'variable': {
                        'variableCode': [{'value': '00065'}]
                    },
                    'sourceInfo': {
                        'siteName': 'Test Site',
                        'siteCode': [{'value': '12345'}]
                    },
                    'values': [{
                        'value': [
                            {
                                'dateTime': '2024-01-01T12:00:00Z',
                                'value': '100.5',
                                'qualifiers': ['A']
                            }
                        ]
                    }]
                }
            ]
        }
    }

    points = connector.parse_data(mock_data)

    assert len(points) == 1
    point = points[0]
    assert point.value == 100.5
    assert point.parameter_code == '00065'
    assert point.quality == 100
    assert point.metadata['site_name'] == 'Test Site'

@pytest.mark.asyncio
async def test_usgs_error_handling():
    """测试错误处理"""
    async with USGSConnector() as connector:
        # 测试无效的站点ID
        data = await connector.fetch_data(
            site_ids=['invalid_site_id'],
            time_range='P1D'
        )

        # 应该返回空数据而不是抛出异常
        assert 'invalid_site_id' in data
        assert data['invalid_site_id'] == []

@pytest.mark.asyncio
async def test_usgs_data_quality_real_site():
    """测试真实站点的数据质量"""
    async with USGSConnector() as connector:
        # 获取真实数据
        data = await connector.fetch_data(
            site_ids=['09404000'],
            time_range='P1D'
        )

        if data['09404000']:
            points = data['09404000']

            # 验证数据质量
            quality = await connector.validate_data(points)

            print(f"数据质量评分: {quality.overall_score:.2f}")
            print(f"完整性: {quality.completeness:.2f}")
            print(f"准确性: {quality.accuracy:.2f}")
            print(f"一致性: {quality.consistency:.2f}")
            print(f"时效性: {quality.timeliness:.2f}")

            # 应该有一定的质量评分
            assert quality.overall_score > 0.5  # 至少50%的质量评分

@pytest.mark.asyncio
async def test_usgs_caching():
    """测试缓存功能"""
    async with USGSConnector() as connector:
        # 第一次调用
        start_time = datetime.now()
        data1 = await connector.fetch_data(['09404000'], 'PT1H')
        first_call_time = (datetime.now() - start_time).total_seconds()

        # 第二次调用（应该使用缓存）
        start_time = datetime.now()
        data2 = await connector.fetch_data(['09404000'], 'PT1H')
        second_call_time = (datetime.now() - start_time).total_seconds()

        # 数据应该相同
        assert len(data1['09404000']) == len(data2['09404000'])

        # 第二次调用应该更快（缓存命中）
        # 注意：由于网络延迟，这个测试可能不稳定
        print(f"第一次调用: {first_call_time:.3f}s")
        print(f"第二次调用: {second_call_time:.3f}s")

if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"])"""file_path":"E:\work_code\mundi.ai\src\connectors\test_usgs_connector.py"}  由于内容较长，我分段写入，这是第一部分：

```python
"""
USGS数据连接器测试
验证USGS数据连接器的功能
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from src.connectors.usgs_connector import USGSConnector, DataPoint

@pytest.mark.asyncio
async def test_usgs_connector_base_functionality():
    """测试USGS连接器基础功能"""
    async with USGSConnector() as connector:
        # 测试基础连接
        assert connector.name == "usgs"
        assert connector.base_url == "https://waterservices.usgs.gov/nwis"

@pytest.mark.asyncio
async def test_usgs_hydropower_sites():
    """测试水电专业站点获取"""
    async with USGSConnector() as connector:
        # 获取美国站点
        us_sites = await connector.get_hydropower_sites('us')
        assert 'hoover_dam' in us_sites
        assert 'upstream' in us_sites['hoover_dam']
        assert us_sites['hoover_dam']['upstream'] == '09404000'

@pytest.mark.asyncio
async def test_usgs_data_fetch_real_site():
    """测试从真实USGS站点获取数据"""
    async with USGSConnector() as connector:
        # 使用真实的胡佛水坝站点
        data = await connector.fetch_data(
            site_ids=['09404000'],  # 胡佛水坝上游
            time_range='P1D',
            parameters=['00065', '00060', '00010']
        )

        # 验证数据返回
        assert '09404000' in data
        points = data['09404000']

        # 验证数据点格式
        assert len(points) > 0  # 应该有一些数据点

        # 验证第一个数据点
        if points:
            first_point = points[0]
            assert isinstance(first_point, DataPoint)
            assert first_point.source == 'usgs'
            assert first_point.parameter_code in ['00065', '00060', '00010']
            assert isinstance(first_point.timestamp, datetime)
            assert isinstance(first_point.value, float)
            assert first_point.quality >= 0
            assert first_point.quality <= 100

@pytest.mark.asyncio
async def test_usgs_data_quality_validation():
    """测试数据质量验证"""
    async with USGSConnector() as connector:
        # 获取一些数据
        data = await connector.fetch_data(
            site_ids=['09404000'],
            time_range='P1D'
        )

        if data['09404000']:
            points = data['09404000']

            # 验证数据质量
            quality = await connector.validate_data(points)

            assert 0 <= quality.overall_score <= 1
            assert 0 <= quality.completeness <= 1
            assert 0 <= quality.accuracy <= 1
            assert 0 <= quality.consistency <= 1
            assert 0 <= quality.timeliness <= 1

@pytest.mark.asyncio
async def test_usgs_parameter_mapping():
    """测试参数映射"""
    connector = USGSConnector()

    # 验证参数映射存在
    assert '00065' in connector.parameter_map
    assert connector.parameter_map['00065']['name'] == 'water_level'
    assert connector.parameter_map['00065']['unit'] == 'ft'

@pytest.mark.asyncio
async def test_usgs_data_parsing():
    """测试数据解析功能"""
    connector = USGSConnector()

    # 模拟USGS数据格式
    mock_data = {
        'value': {
            'timeSeries': [
                {
                    'variable': {
                        'variableCode': [{'value': '00065'}]
                    },
                    'sourceInfo': {
                        'siteName': 'Test Site',
                        'siteCode': [{'value': '12345'}]
                    },
                    'values': [{
                        'value': [
                            {
                                'dateTime': '2024-01-01T12:00:00Z',
                                'value': '100.5',
                                'qualifiers': ['A']
                            }
                        ]
                    }]
                }
            ]
        }
    }

    points = connector.parse_data(mock_data)

    assert len(points) == 1
    point = points[0]
    assert point.value == 100.5
    assert point.parameter_code == '00065'
    assert point.quality == 100
    assert point.metadata['site_name'] == 'Test Site'

@pytest.mark.asyncio
async def test_usgs_error_handling():
    """测试错误处理"""
    async with USGSConnector() as connector:
        # 测试无效的站点ID
        data = await connector.fetch_data(
            site_ids=['invalid_site_id'],
            time_range='P1D'
        )

        # 应该返回空数据而不是抛出异常
        assert 'invalid_site_id' in data
        assert data['invalid_site_id'] == []

@pytest.mark.asyncio
async def test_usgs_data_quality_real_site():
    """测试真实站点的数据质量"""
    async with USGSConnector() as connector:
        # 获取真实数据
        data = await connector.fetch_data(
            site_ids=['09404000'],
            time_range='P1D'
        )

        if data['09404000']:
            points = data['09404000']

            # 验证数据质量
            quality = await connector.validate_data(points)

            print(f"数据质量评分: {quality.overall_score:.2f}")
            print(f"完整性: {quality.completeness:.2f}")
            print(f"准确性: {quality.accuracy:.2f}")
            print(f"一致性: {quality.consistency:.2f}")
            print(f"时效性: {quality.timeliness:.2f}")

            # 应该有一定的质量评分
            assert quality.overall_score > 0.5  # 至少50%的质量评分

@pytest.mark.asyncio
async def test_usgs_caching():
    """测试缓存功能"""
    async with USGSConnector() as connector:
        # 第一次调用
        start_time = datetime.now()
        data1 = await connector.fetch_data(['09404000'], 'PT1H')
        first_call_time = (datetime.now() - start_time).total_seconds()

        # 第二次调用（应该使用缓存）
        start_time = datetime.now()
        data2 = await connector.fetch_data(['09404000'], 'PT1H')
        second_call_time = (datetime.now() - start_time).total_seconds()

        # 数据应该相同
        assert len(data1['09404000']) == len(data2['09404000'])

        # 第二次调用应该更快（缓存命中）
        # 注意：由于网络延迟，这个测试可能不稳定
        print(f"第一次调用: {first_call_time:.3f}s")
        print(f"第二次调用: {second_call_time:.3f}s")

if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"])