"""
大模型Orchestrator中央调度器
负责协调所有组件，实现搭积木式任务分解和执行
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

from .context_manager import ContextManager
from .mcp_client import MCPClient
from .viz_orchestrator import VizOrchestrator
from .interaction_handler import InteractionHandler


@dataclass
class Task:
    """任务定义"""
    task_id: str
    task_type: str  # data_loading, analysis, visualization, report, scenario
    description: str
    parameters: Dict[str, Any]
    dependencies: List[str] = None
    priority: int = 1  # 1-10
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = None
    completed_at: datetime = None
    result: Any = None
    error: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class UserRequest:
    """用户请求"""
    request_id: str
    user_query: str
    context: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ModelOrchestrator:
    """大模型Orchestrator中央调度器"""

    def __init__(self, mcp_client: MCPClient, context_manager: ContextManager,
                 viz_orchestrator: VizOrchestrator, interaction_handler: InteractionHandler):
        self.mcp_client = mcp_client
        self.context_manager = context_manager
        self.viz_orchestrator = viz_orchestrator
        self.interaction_handler = interaction_handler

        self.logger = logging.getLogger(__name__)

        # 任务队列
        self.task_queue: List[Task] = []
        self.completed_tasks: Dict[str, Task] = {}

        # 回调函数
        self.callbacks: Dict[str, List[Callable]] = {
            'task_created': [],
            'task_completed': [],
            'task_failed': [],
            'workflow_completed': []
        }

    def parse_user_request(self, user_query: str, **context) -> UserRequest:
        """
        解析用户自然语言请求

        Args:
            user_query: 用户查询
            **context: 上下文信息

        Returns:
            标准化用户请求
        """
        import uuid
        request_id = str(uuid.uuid4())

        # 解析请求意图和实体
        parsed_context = self._extract_intent_and_entities(user_query)
        context.update(parsed_context)

        return UserRequest(
            request_id=request_id,
            user_query=user_query,
            context=context
        )

    def _extract_intent_and_entities(self, user_query: str) -> Dict[str, Any]:
        """
        提取用户意图和实体

        Args:
            user_query: 用户查询

        Returns:
            解析结果
        """
        user_query_lower = user_query.lower()

        # 意图识别（基于规则，实际应用中可以使用NLP模型）
        intent = "unknown"

        if any(word in user_query_lower for word in ['洪水', '淹没', '演进', '模拟']):
            intent = "flood_simulation"
        elif any(word in user_query_lower for word in ['水库', '调度', '水位', '库容']):
            intent = "reservoir_operation"
        elif any(word in user_query_lower for word in ['异常', '检测', '故障', '异常']):
            intent = "anomaly_detection"
        elif any(word in user_query_lower for word in ['风险', '评估', '危险', '安全']):
            intent = "risk_assessment"
        elif any(word in user_query_lower for word in ['预测', '预报', '趋势', '未来']):
            intent = "prediction"
        elif any(word in user_query_lower for word in ['数据', '加载', '导入', '连接']):
            intent = "data_loading"
        elif any(word in user_query_lower for word in ['报告', '生成', '输出', '结果']):
            intent = "report_generation"
        elif any(word in user_query_lower for word in ['可视化', '图表', '地图', '3d']):
            intent = "visualization"

        # 实体提取（站点、时间范围等）
        entities = {
            'stations': [],
            'time_range': None,
            'parameters': []
        }

        # 提取站点信息
        if '胡佛水坝' in user_query:
            entities['stations'].append('hoover_dam')
        elif '三峡' in user_query:
            entities['stations'].append('three_gorges')
        elif 'potomac' in user_query_lower or '波托马克' in user_query:
            entities['stations'].append('potomac_river')
        elif 'colorado' in user_query_lower:
            entities['stations'].append('colorado_river')

        return {
            'intent': intent,
            'entities': entities
        }

    def decompose_task(self, user_request: UserRequest) -> List[Task]:
        """
        将复杂任务分解为可执行的子任务（搭积木式）

        Args:
            user_request: 用户请求

        Returns:
            子任务列表
        """
        tasks = []
        intent = user_request.context.get('intent', 'unknown')

        if intent == "flood_simulation":
            tasks = self._decompose_flood_simulation(user_request)
        elif intent == "reservoir_operation":
            tasks = self._decompose_reservoir_operation(user_request)
        elif intent == "anomaly_detection":
            tasks = self._decompose_anomaly_detection(user_request)
        elif intent == "risk_assessment":
            tasks = self._decompose_risk_assessment(user_request)
        elif intent == "prediction":
            tasks = self._decompose_prediction(user_request)
        elif intent == "data_loading":
            tasks = self._decompose_data_loading(user_request)
        elif intent == "report_generation":
            tasks = self._decompose_report_generation(user_request)
        elif intent == "visualization":
            tasks = self._decompose_visualization(user_request)
        else:
            # 通用任务分解
            tasks = self._decompose_generic_task(user_request)

        # 设置任务依赖关系
        self._setup_task_dependencies(tasks)

        return tasks

    def _decompose_flood_simulation(self, user_request: UserRequest) -> List[Task]:
        """分解洪水模拟任务"""
        tasks = []
        import uuid

        # 1. 数据加载
        task1 = Task(
            task_id=f"load_data_{uuid.uuid4().hex[:8]}",
            task_type="data_loading",
            description="加载水文数据",
            parameters={
                'stations': user_request.context.get('entities', {}).get('stations', []),
                'parameters': ['water_level', 'discharge', 'rainfall'],
                'time_range': user_request.context.get('entities', {}).get('time_range')
            },
            priority=1
        )
        tasks.append(task1)

        # 2. 洪水模拟
        task2 = Task(
            task_id=f"flood_sim_{uuid.uuid4().hex[:8]}",
            task_type="analysis",
            description="执行洪水演进模拟",
            parameters={
                'model': 'flood_evolution',
                'boundary_conditions': user_request.context.get('boundary_conditions', {})
            },
            priority=2
        )
        task2.dependencies.append(task1.task_id)
        tasks.append(task2)

        # 3. 风险评估
        task3 = Task(
            task_id=f"risk_assess_{uuid.uuid4().hex[:8]}",
            task_type="analysis",
            description="评估洪水风险",
            parameters={
                'model': 'risk_assessment',
                'risk_types': ['flood', 'structural', 'social']
            },
            priority=3
        )
        task3.dependencies.append(task2.task_id)
        tasks.append(task3)

        # 4. 生成可视化
        task4 = Task(
            task_id=f"viz_{uuid.uuid4().hex[:8]}",
            task_type="visualization",
            description="生成洪水演进可视化",
            parameters={
                'viz_types': ['chart', 'map', '3d_scene'],
                'animation': True
            },
            priority=4
        )
        task4.dependencies.append(task2.task_id)
        task4.dependencies.append(task3.task_id)
        tasks.append(task4)

        # 5. 生成报告
        task5 = Task(
            task_id=f"report_{uuid.uuid4().hex[:8]}",
            task_type="report",
            description="生成洪水分析报告",
            parameters={
                'report_type': 'flood_analysis',
                'include_maps': True,
                'include_charts': True
            },
            priority=5
        )
        task5.dependencies.append(task4.task_id)
        tasks.append(task5)

        return tasks

    def _decompose_reservoir_operation(self, user_request: UserRequest) -> List[Task]:
        """分解水库调度任务"""
        tasks = []
        import uuid

        # 1. 加载水库数据
        task1 = Task(
            task_id=f"load_reservoir_{uuid.uuid4().hex[:8]}",
            task_type="data_loading",
            description="加载水库数据",
            parameters={
                'data_type': 'reservoir',
                'reservoir_id': user_request.context.get('reservoir_id')
            },
            priority=1
        )
        tasks.append(task1)

        # 2. 水库模拟
        task2 = Task(
            task_id=f"reservoir_sim_{uuid.uuid4().hex[:8]}",
            task_type="analysis",
            description="执行水库调度模拟",
            parameters={
                'model': 'reservoir_simulation',
                'operation_mode': user_request.context.get('operation_mode', 'normal'),
                'forecast_days': user_request.context.get('forecast_days', 7)
            },
            priority=2
        )
        task2.dependencies.append(task1.task_id)
        tasks.append(task2)

        # 3. 优化调度方案
        task3 = Task(
            task_id=f"optimize_{uuid.uuid4().hex[:8]}",
            task_type="analysis",
            description="优化调度方案",
            parameters={
                'model': 'optimization',
                'objectives': ['power_generation', 'flood_control', 'water_supply'],
                'constraints': user_request.context.get('constraints', {})
            },
            priority=3
        )
        task3.dependencies.append(task2.task_id)
        tasks.append(task3)

        # 4. 生成可视化
        task4 = Task(
            task_id=f"viz_{uuid.uuid4().hex[:8]}",
            task_type="visualization",
            description="生成调度方案可视化",
            parameters={
                'viz_types': ['chart', '3d_scene'],
                'content': 'reservoir_operation'
            },
            priority=4
        )
        task4.dependencies.append(task3.task_id)
        tasks.append(task4)

        return tasks

    def _decompose_anomaly_detection(self, user_request: UserRequest) -> List[Task]:
        """分解异常检测任务"""
        tasks = []
        import uuid

        # 1. 加载历史数据
        task1 = Task(
            task_id=f"load_history_{uuid.uuid4().hex[:8]}",
            task_type="data_loading",
            description="加载历史监测数据",
            parameters={
                'data_type': 'historical',
                'duration_days': user_request.context.get('duration_days', 30)
            },
            priority=1
        )
        tasks.append(task1)

        # 2. 异常检测
        task2 = Task(
            task_id=f"detect_{uuid.uuid4().hex[:8]}",
            task_type="analysis",
            description="执行异常检测",
            parameters={
                'model': 'anomaly_detection',
                'detection_methods': ['statistical', 'temporal', 'multivariate'],
                'sensitivity': user_request.context.get('sensitivity', 'medium')
            },
            priority=2
        )
        task2.dependencies.append(task1.task_id)
        tasks.append(task2)

        # 3. 生成可视化
        task3 = Task(
            task_id=f"viz_{uuid.uuid4().hex[:8]}",
            task_type="visualization",
            description="生成异常检测结果可视化",
            parameters={
                'viz_types': ['anomaly_chart', 'alerts'],
                'highlight_anomalies': True
            },
            priority=3
        )
        task3.dependencies.append(task2.task_id)
        tasks.append(task3)

        return tasks

    def _setup_task_dependencies(self, tasks: List[Task]):
        """设置任务依赖关系"""
        # 确保依赖关系图中的任务都存在
        task_ids = {task.task_id for task in tasks}

        for task in tasks:
            # 移除不存在的依赖
            task.dependencies = [dep for dep in task.dependencies if dep in task_ids]

    async def execute_tasks(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        执行任务列表

        Args:
            tasks: 任务列表

        Returns:
            执行结果
        """
        # 将任务加入队列
        self.task_queue = tasks

        for task in tasks:
            self.completed_tasks[task.task_id] = task
            self._trigger_callback('task_created', task)

        # 按优先级和执行顺序执行任务
        results = {}

        while any(task.status in ["pending", "running"] for task in tasks):
            # 获取可以执行的任务（所有依赖已完成）
            executable_tasks = [
                task for task in tasks
                if task.status == "pending" and all(
                    self.completed_tasks.get(dep_id, Task("", "", "")).status == "completed"
                    for dep_id in task.dependencies
                )
            ]

            if not executable_tasks:
                # 避免死锁
                break

            # 并行执行可执行任务
            execution_tasks = []
            for task in executable_tasks:
                execution_tasks.append(self._execute_single_task(task))

            # 等待批任务完成
            batch_results = await asyncio.gather(*execution_tasks, return_exceptions=True)

            # 处理结果
            for task, result in zip(executable_tasks, batch_results):
                if isinstance(result, Exception):
                    task.status = "failed"
                    task.error = str(result)
                    self._trigger_callback('task_failed', task)
                    self.logger.error(f"任务 {task.task_id} 执行失败: {result}")
                else:
                    task.status = "completed"
                    task.result = result
                    task.completed_at = datetime.now()
                    results[task.task_id] = result
                    self._trigger_callback('task_completed', task)
                    self.logger.info(f"任务 {task.task_id} 执行成功")

        # 工作流完成
        self._trigger_callback('workflow_completed', {
            'tasks': tasks,
            'results': results
        })

        return {
            'overall_status': 'completed' if not any(task.status == 'failed' for task in tasks) else 'partial_failed',
            'task_count': len(tasks),
            'completed_count': sum(1 for task in tasks if task.status == 'completed'),
            'failed_count': sum(1 for task in tasks if task.status == 'failed'),
            'results': results
        }

    async def _execute_single_task(self, task: Task) -> Any:
        """执行单个任务"""
        task.status = "running"

        try:
            if task.task_type == "data_loading":
                return await self.context_manager.load_data(**task.parameters)
            elif task.task_type == "analysis":
                return await self.mcp_client.call_model(**task.parameters)
            elif task.task_type == "visualization":
                return await self.viz_orchestrator.generate_visualization(**task.parameters)
            elif task.task_type == "report":
                return await self.viz_orchestrator.generate_report(**task.parameters)
            elif task.task_type == "scenario":
                return await self.interaction_handler.execute_scenario(**task.parameters)
            else:
                return {"status": "unknown_task_type", "task_id": task.task_id}
        except Exception as e:
            raise e

    def get_task_status(self, task_id: str) -> Optional[Task]:
        """获取任务状态"""
        return self.completed_tasks.get(task_id)

    def get_workflow_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        tasks = list(self.completed_tasks.values())

        return {
            'total_tasks': len(tasks),
            'pending': sum(1 for task in tasks if task.status == 'pending'),
            'running': sum(1 for task in tasks if task.status == 'running'),
            'completed': sum(1 for task in tasks if task.status == 'completed'),
            'failed': sum(1 for task in tasks if task.status == 'failed')
        }

    def cancel_workflow(self):
        """取消工作流"""
        for task in self.task_queue:
            if task.status in ['pending', 'running']:
                task.status = 'cancelled'

    def register_callback(self, event: str, callback: Callable):
        """注册回调函数"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, data: Any):
        """触发回调"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"回调执行失败: {e}")
