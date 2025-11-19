"""
外部知识库连接器
连接外部知识库和文档系统
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod


class KnowledgeSource(ABC):
    """知识源抽象基类"""

    @abstractmethod
    async def query(self, query: str, **kwargs) -> Dict[str, Any]:
        """查询知识"""
        pass


class DocumentKnowledgeSource(KnowledgeSource):
    """文档知识源"""

    def __init__(self, document_path: str):
        self.document_path = document_path
        self.documents = {}

    async def load_documents(self):
        """加载文档"""
        import os
        for filename in os.listdir(self.document_path):
            if filename.endswith(('.txt', '.md', '.pdf')):
                filepath = os.path.join(self.document_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.documents[filename] = {
                            'content': f.read(),
                            'modified': os.path.getmtime(filepath)
                        }
                except:
                    pass

    async def query(self, query: str, **kwargs) -> Dict[str, Any]:
        """查询文档"""
        results = []
        query_lower = query.lower()

        for filename, doc in self.documents.items():
            if query_lower in doc['content'].lower():
                results.append({
                    'source': filename,
                    'relevance': 0.8,
                    'snippet': doc['content'][:500]
                })

        return {
            'status': 'success',
            'query': query,
            'results': results,
            'count': len(results)
        }


class ExternalKnowledgeConnector:
    """外部知识库连接器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.knowledge_sources: Dict[str, KnowledgeSource] = {}

    def add_knowledge_source(self, source_id: str, source: KnowledgeSource):
        """添加知识源"""
        self.knowledge_sources[source_id] = source
        self.logger.info(f"添加知识源: {source_id}")

    async def query_knowledge(self, query: str,
                            source_ids: List[str] = None,
                            **kwargs) -> Dict[str, Any]:
        """
        查询外部知识库

        Args:
            query: 查询内容
            source_ids: 知识源ID列表
            **kwargs: 其他参数

        Returns:
            查询结果
        """
        if not source_ids:
            source_ids = list(self.knowledge_sources.keys())

        all_results = []

        for source_id in source_ids:
            source = self.knowledge_sources.get(source_id)
            if not source:
                continue

            try:
                result = await source.query(query, **kwargs)
                if result.get('status') == 'success':
                    all_results.extend(result.get('results', []))
            except Exception as e:
                self.logger.error(f"知识源 {source_id} 查询失败: {e}")

        # 按相关性排序
        all_results.sort(key=lambda x: x.get('relevance', 0), reverse=True)

        return {
            'status': 'success',
            'query': query,
            'results': all_results,
            'total_count': len(all_results),
            'sources_queried': len(source_ids)
        }

    async def get_flood_control_knowledge(self, query: str) -> Dict[str, Any]:
        """获取防洪知识"""
        flood_knowledge = {
            "prevention": [
                "加固堤防工程",
                "疏通河道障碍",
                "预泄腾库迎洪",
                "落实防汛责任制",
                "准备防汛物资"
            ],
            "emergency": [
                "启动应急预案",
                "人员安全转移",
                "重点部位巡查",
                "险情及时上报",
                "抢险队伍动员"
            ],
            "historical_cases": [
                {
                    "name": "1998年长江洪水",
                    "year": 1998,
                    "peak_flow": "69200 m³/s",
                    "lessons": "加强堤防建设"
                },
                {
                    "name": "2020年长江流域洪水",
                    "year": 2020,
                    "peak_flow": "83600 m³/s",
                    "lessons": "加强预报预警"
                }
            ]
        }

        query_lower = query.lower()

        if '预防' in query_lower or '防治' in query_lower:
            return {
                'status': 'success',
                'type': 'prevention',
                'content': flood_knowledge['prevention']
            }
        elif '应急' in query_lower or '抢' in query_lower:
            return {
                'status': 'success',
                'type': 'emergency',
                'content': flood_knowledge['emergency']
            }
        elif '案例' in query_lower or '历史' in query_lower:
            return {
                'status': 'success',
                'type': 'historical',
                'content': flood_knowledge['historical_cases']
            }

        return {
            'status': 'success',
            'type': 'general',
            'content': flood_knowledge
        }

    async def get_dam_safety_guidelines(self) -> Dict[str, Any]:
        """获取大坝安全指南"""
        guidelines = {
            "daily_inspection": [
                "坝体表面检查：裂缝、渗漏、变形",
                "泄洪设施检查：闸门、启闭机、电气系统",
                "监测设施检查：仪器运行状态、数据采集",
                "库区巡查：滑坡、浸没、库盆渗漏"
            ],
            "regular_tests": [
                "变形监测：水平位移、垂直位移",
                "渗流监测：渗流量、渗透压力、水质",
                "应力应变监测：混凝土应力、钢筋应力",
                "环境监测：温度、湿度、地震"
            ],
            "safety_indicators": {
                "critical_deformation": "超过设计值的80%",
                "critical_seepage": "渗流量突然增大",
                "critical_stress": "应力达到材料强度",
                "warning_signs": ["异常声响", "剧烈振动", "异常渗漏"]
            }
        }

        return {
            'status': 'success',
            'guidelines': guidelines,
            'reference_standards': ['SL258-2017', 'DL/T5256-2010']
        }
