"""
MCP客户端
负责调用专业模型MCP服务器
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

import aiohttp


@dataclass
class ModelEndpoint:
    """模型端点定义"""
    model_id: str
    name: str
    endpoint_url: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    timeout: int = 30
    health_status: str = "healthy"  # healthy, degraded, offline
    last_health_check: datetime = None

    def __post_init__(self):
        if self.last_health_check is None:
            self.last_health_check = datetime.now()


class MCPClient:
    """MCP客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)

        # 模型端点注册表
        self.model_endpoints: Dict[str, ModelEndpoint] = {}

        # 初始化模型端点
        self._init_model_endpoints()

    def _init_model_endpoints(self):
        """初始化模型端点"""
        models = [
            ModelEndpoint(
                model_id="flood_evolution",
                name="洪水演进模型",
                endpoint_url=f"{self.base_url}/api/mcp/flood/simulate",
                description="基于圣维南方程组的洪水演进模拟",
                input_schema={
                    "river_length": {"type": "number"},
                    "dx": {"type": "number"},
                    "dt": {"type": "number"},
                    "manning_n": {"type": "number"},
                    "initial_conditions": {"type": "object"},
                    "upstream_boundary": {"type": "object"},
                    "downstream_boundary": {"type": "object"}
                },
                output_schema={
                    "water_levels": {"type": "array"},
                    "discharges": {"type": "array"},
                    "flood_extent": {"type": "object"},
                    "max_water_level": {"type": "number"},
                    "simulation_time": {"type": "number"}
                }
            ),
            ModelEndpoint(
                model_id="reservoir_simulation",
                name="水库模拟模型",
                endpoint_url=f"{self.base_url}/api/mcp/reservoir/simulate",
                description="水库多目标调度优化",
                input_schema={
                    "reservoir_id": {"type": "string"},
                    "current_level": {"type": "number"},
                    "inflow_forecast": {"type": "array"},
                    "operation_mode": {"type": "string"},
                    "target_level": {"type": "number"}
                },
                output_schema={
                    "optimized_schedule": {"type": "object"},
                    "water_level_series": {"type": "array"},
                    "power_generation": {"type": "number"},
                    "flood_risk_score": {"type": "number"}
                }
            ),
            ModelEndpoint(
                model_id="anomaly_detection",
                name="异常检测模型",
                endpoint_url=f"{self.base_url}/api/mcp/anomaly/detect",
                description="多维度水文异常检测",
                input_schema={
                    "water_level_data": {"type": "array"},
                    "discharge_data": {"type": "array"},
                    "temperature_data": {"type": "array"},
                    "seasonal_period": {"type": "number"},
                    "sensitivity": {"type": "string"}
                },
                output_schema={
                    "anomalies": {"type": "array"},
                    "anomaly_scores": {"type": "array"},
                    "detection_summary": {"type": "object"}
                }
            ),
            ModelEndpoint(
                model_id="risk_assessment",
                name="风险评估模型",
                endpoint_url=f"{self.base_url}/api/mcp/risk/assess",
                description="多维度风险评估",
                input_schema={
                    "risk_types": {"type": "array"},
                    "probability_data": {"type": "object"},
                    "impact_data": {"type": "object"},
                    "vulnerability_data": {"type": "object"}
                },
                output_schema={
                    "risk_scores": {"type": "object"},
                    "overall_risk": {"type": "number"},
                    "risk_ranking": {"type": "array"}
                }
            ),
            ModelEndpoint(
                model_id="prediction",
                name="预测模型",
                endpoint_url=f"{self.base_url}/api/mcp/prediction/forecast",
                description="水文变量时间序列预测",
                input_schema={
                    "historical_water_levels": {"type": "array"},
                    "historical_discharges": {"type": "array"},
                    "prediction_hours": {"type": "integer"},
                    "method": {"type": "string"}
                },
                output_schema={
                    "predictions": {"type": "array"},
                    "confidence_intervals": {"type": "object"},
                    "prediction_metrics": {"type": "object"}
                }
            )
        ]

        for model in models:
            self.model_endpoints[model.model_id] = model

    async def call_model(self, model_id: str, **parameters) -> Dict[str, Any]:
        """
        调用模型

        Args:
            model_id: 模型ID
            **parameters: 模型参数

        Returns:
            模型结果
        """
        if model_id not in self.model_endpoints:
            return {"status": "error", "message": f"模型 {model_id} 未注册"}

        endpoint = self.model_endpoints[model_id]

        # 验证输入
        validation_result = self._validate_input(parameters, endpoint.input_schema)
        if not validation_result["valid"]:
            return {"status": "error", "message": f"参数验证失败: {validation_result['errors']}"}

        try:
            self.logger.info(f"调用模型 {model_id} - 参数: {parameters}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint.endpoint_url,
                    json=parameters,
                    timeout=aiohttp.ClientTimeout(total=endpoint.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "status": "success",
                            "model_id": model_id,
                            "result": result
                        }
                    else:
                        return {
                            "status": "error",
                            "message": f"模型调用失败: HTTP {response.status}"
                        }

        except asyncio.TimeoutError:
            return {"status": "error", "message": f"模型调用超时 ({endpoint.timeout}秒)"}
        except Exception as e:
            self.logger.error(f"模型调用异常: {e}")
            return {"status": "error", "message": str(e)}

    def _validate_input(self, parameters: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """验证输入参数"""
        errors = []

        for param_name, param_config in schema.items():
            if param_name not in parameters:
                if param_config.get("required", True):
                    errors.append(f"缺少必需参数: {param_name}")
            else:
                # 类型检查
                expected_type = param_config["type"]
                actual_value = parameters[param_name]

                if expected_type == "number" and not isinstance(actual_value, (int, float)):
                    errors.append(f"参数 {param_name} 应为数字类型")
                elif expected_type == "string" and not isinstance(actual_value, str):
                    errors.append(f"参数 {param_name} 应为字符串类型")
                elif expected_type == "array" and not isinstance(actual_value, list):
                    errors.append(f"参数 {param_name} 应为数组类型")
                elif expected_type == "object" and not isinstance(actual_value, dict):
                    errors.append(f"参数 {param_name} 应为对象类型")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    async def call_multiple_models(self, model_calls: List[Dict[str, Any]], parallel: bool = True) -> Dict[str, Any]:
        """
        调用多个模型

        Args:
            model_calls: 模型调用列表 [{"model_id": "...", "parameters": {...}}, ...]
            parallel: 是否并行执行

        Returns:
            调用结果
        """
        if parallel:
            # 并行执行
            tasks = []
            for call in model_calls:
                tasks.append(self.call_model(call["model_id"], **call.get("parameters", {})))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            return {
                "status": "completed",
                "results": results
            }
        else:
            # 顺序执行
            results = []
            for call in model_calls:
                result = await self.call_model(call["model_id"], **call.get("parameters", {}))
                results.append(result)

            return {
                "status": "completed",
                "results": results
            }

    async def health_check(self, model_id: str = None) -> Dict[str, Any]:
        """
        健康检查

        Args:
            model_id: 模型ID（可选，如果为None则检查所有）

        Returns:
            健康状态
        """
        if model_id:
            endpoints = [self.model_endpoints.get(model_id)]
        else:
            endpoints = list(self.model_endpoints.values())

        results = {}

        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                if not endpoint:
                    continue

                try:
                    # 调用健康检查端点
                    health_url = f"{endpoint.endpoint_url}/health"

                    async with session.get(health_url, timeout=5) as response:
                        if response.status == 200:
                            endpoint.health_status = "healthy"
                        else:
                            endpoint.health_status = "degraded"

                except Exception as e:
                    self.logger.error(f"健康检查失败 {endpoint.model_id}: {e}")
                    endpoint.health_status = "offline"

                endpoint.last_health_check = datetime.now()
                results[endpoint.model_id] = endpoint.health_status

        return {
            "status": "completed",
            "health_status": results,
            "timestamp": datetime.now().isoformat()
        }

    def get_model_info(self, model_id: str = None) -> Dict[str, Any]:
        """
        获取模型信息

        Args:
            model_id: 模型ID（可选）

        Returns:
            模型信息
        """
        if model_id:
            endpoint = self.model_endpoints.get(model_id)
            if not endpoint:
                return {"status": "error", "message": f"模型 {model_id} 不存在"}

            return {
                "status": "success",
                "model": {
                    "model_id": endpoint.model_id,
                    "name": endpoint.name,
                    "description": endpoint.description,
                    "endpoint_url": endpoint.endpoint_url,
                    "health_status": endpoint.health_status,
                    "input_schema": endpoint.input_schema,
                    "output_schema": endpoint.output_schema
                }
            }
        else:
            models = []
            for endpoint in self.model_endpoints.values():
                models.append({
                    "model_id": endpoint.model_id,
                    "name": endpoint.name,
                    "description": endpoint.description,
                    "health_status": endpoint.health_status
                })

            return {
                "status": "success",
                "models": models
            }
