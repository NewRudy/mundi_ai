"""
可视化编排器
负责协调可视化生成流程
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field

from ..visualization import (
    ChartGenerator,
    MapGenerator,
    Scene3DGenerator,
    AnimationEffects,
    ReportGenerator
)


@dataclass
class VizTask:
    """可视化任务"""
    task_id: str
    viz_type: str  # chart, map, scene, animation, report, dashboard
    description: str
    parameters: Dict[str, Any]
    status: str = "pending"  # pending, generating, completed, failed
    priority: int = 1
    result: Any = None
    error: str = None
    created_at: datetime = None
    completed_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class VisualPipeline:
    """可视化管道"""
    pipeline_id: str
    name: str
    viz_tasks: List[VizTask] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = None
    completed_at: datetime = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class VizOrchestrator:
    """可视化编排器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 初始化可视化生成器
        self.chart_gen = ChartGenerator()
        self.map_gen = MapGenerator()
        self.scene_gen = Scene3DGenerator()
        self.anim_effects = AnimationEffects()
        self.report_gen = ReportGenerator()

        # 可视化管道管理
        self.pipelines: Dict[str, VisualPipeline] = {}

        # 缓存管理
        self.viz_cache: Dict[str, Any] = {}

    async def generate_visualization(self, viz_type: str, **parameters) -> Dict[str, Any]:
        """
        生成可视化

        Args:
            viz_type: 可视化类型
            **parameters: 参数

        Returns:
            可视化配置
        """
        self.logger.info(f"生成可视化 - 类型: {viz_type}, 参数: {list(parameters.keys())}")

        try:
            if viz_type == "chart":
                result = await self._generate_chart(**parameters)
            elif viz_type == "map":
                result = await self._generate_map(**parameters)
            elif viz_type == "scene":
                result = await self._generate_scene(**parameters)
            elif viz_type == "animation":
                result = await self._generate_animation(**parameters)
            elif viz_type == "report":
                result = await self.generate_report(**parameters)
            elif viz_type == "dashboard":
                result = await self._generate_dashboard(**parameters)
            else:
                return {"status": "error", "message": f"不支持的可视化类型: {viz_type}"}

            # 缓存结果
            cache_key = f"{viz_type}:{json.dumps(parameters, sort_keys=True)}"
            self.viz_cache[cache_key] = result

            return {
                "status": "success",
                "viz_type": viz_type,
                "config": result
            }

        except Exception as e:
            self.logger.error(f"可视化生成失败: {e}")
            return {"status": "error", "message": str(e)}

    async def _generate_chart(self, data: Dict[str, Any],
                            chart_type: Optional[str] = None,
                            title: Optional[str] = None,
                            **kwargs) -> Dict[str, Any]:
        """生成图表"""
        self.logger.info(f"生成图表 - 数据类型: {type(data)}, 图表类型: {chart_type}")

        # 使用图表生成器
        chart_config = self.chart_gen.generate_automatic_chart(
            data=data,
            chart_type=chart_type,
            title=title
        )

        return chart_config

    async def _generate_map(self, map_type: str = "hydrological_monitoring",
                          stations: List[Dict] = None,
                          risk_zones: List[Dict] = None,
                          warning_zones: List[Dict] = None,
                          **kwargs) -> Dict[str, Any]:
        """生成地图"""
        self.logger.info(f"生成地图 - 类型: {map_type}")

        # 使用地图生成器
        if map_type == "hydrological_monitoring":
            map_config = self.map_gen.generate_hydrological_map(
                stations=stations or [],
                risk_zones=risk_zones,
                warning_zones=warning_zones
            )
        elif map_type == "flood_evolution":
            map_config = self.map_gen.generate_flood_evolution_map(
                flood_extent=kwargs.get("flood_extent", {}),
                evolution_steps=kwargs.get("evolution_steps", [])
            )
        elif map_type == "reservoir_monitoring":
            map_config = self.map_gen.generate_reservoir_map(
                reservoir_boundary=kwargs.get("reservoir_boundary", {}),
                current_water_level=kwargs.get("current_water_level", 0),
                dam_location=kwargs.get("dam_location", {})
            )
        else:
            map_config = self.map_gen.generate_hydrological_map(stations or [])

        return map_config

    async def _generate_scene(self, scene_type: str = "flood_submersion",
                            **kwargs) -> Dict[str, Any]:
        """生成3D场景"""
        self.logger.info(f"生成3D场景 - 类型: {scene_type}")

        # 使用3D场景生成器
        scene_config = self.scene_gen.generate_3d_scene(scene_type, **kwargs)

        return scene_config

    async def _generate_animation(self, animation_type: str, **kwargs) -> Dict[str, Any]:
        """生成动画"""
        self.logger.info(f"生成动画 - 类型: {animation_type}")

        # 使用动画效果生成器
        animation_config = self.anim_effects.generate_animation(animation_type, **kwargs)

        return animation_config

    async def _generate_dashboard(self, datasets: List[Dict[str, Any]],
                                layout: str = "grid",
                                **kwargs) -> Dict[str, Any]:
        """生成仪表板"""
        self.logger.info(f"生成仪表板 - 布局: {layout}, 数据集数: {len(datasets)}")

        # 为每个数据集生成图表
        charts = []
        for dataset in datasets:
            chart_config = await self._generate_chart(
                data=dataset,
                chart_type=dataset.get("chart_type"),
                title=dataset.get("title")
            )
            charts.append(chart_config)

        # 在现有图表生成器上生成仪表板
        dashboard_config = self.chart_gen.generate_dashboard(
            datasets=datasets,
            layout=layout
        )

        return dashboard_config

    async def generate_report(self, report_type: str, **parameters) -> Dict[str, Any]:
        """
        生成报告

        Args:
            report_type: 报告类型
            **parameters: 参数

        Returns:
            报告HTML
        """
        self.logger.info(f"生成报告 - 类型: {report_type}")

        try:
            # 生成报告HTML
            html_content = self.report_gen.generate_report(report_type, **parameters)

            return {
                "status": "success",
                "report_type": report_type,
                "html": html_content,
                "format": "html"
            }

        except Exception as e:
            self.logger.error(f"报告生成失败: {e}")
            return {"status": "error", "message": str(e)}

    def create_pipeline(self, pipeline_name: str, viz_tasks: List[Dict[str, Any]]) -> str:
        """
        创建可视化管道

        Args:
            pipeline_name: 管道名称
            viz_tasks: 可视化任务列表

        Returns:
            管道ID
        """
        import uuid
        pipeline_id = str(uuid.uuid4())

        # 创建可视化任务对象
        tasks = []
        for task_config in viz_tasks:
            task = VizTask(
                task_id=str(uuid.uuid4()),
                viz_type=task_config.get("type"),
                description=task_config.get("description", ""),
                parameters=task_config.get("parameters", {}),
                priority=task_config.get("priority", 1)
            )
            tasks.append(task)

        # 创建管道
        pipeline = VisualPipeline(
            pipeline_id=pipeline_id,
            name=pipeline_name,
            viz_tasks=tasks
        )

        self.pipelines[pipeline_id] = pipeline
        return pipeline_id

    async def execute_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """
        执行可视化管道

        Args:
            pipeline_id: 管道ID

        Returns:
            执行结果
        """
        pipeline = self.pipelines.get(pipeline_id)
        if not pipeline:
            return {"status": "error", "message": f"管道 {pipeline_id} 不存在"}

        pipeline.status = "running"

        results = {}

        # 按优先级排序任务
        sorted_tasks = sorted(pipeline.viz_tasks, key=lambda t: t.priority)

        # 执行每个任务
        for task in sorted_tasks:
            task.status = "generating"

            try:
                result = await self.generate_visualization(
                    viz_type=task.viz_type,
                    **task.parameters
                )

                if result["status"] == "success":
                    task.status = "completed"
                    task.result = result
                    results[task.task_id] = result
                else:
                    task.status = "failed"
                    task.error = result.get("message", "未知错误")

            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                self.logger.error(f"可视化任务 {task.task_id} 失败: {e}")

        pipeline.status = "completed"
        pipeline.completed_at = datetime.now()

        return {
            "status": "completed",
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline.name,
            "task_count": len(pipeline.viz_tasks),
            "completed_count": sum(1 for t in pipeline.viz_tasks if t.status == "completed"),
            "failed_count": sum(1 for t in pipeline.viz_tasks if t.status == "failed"),
            "results": results
        }

    async def generate_comprehensive_analysis(self, analysis_type: str,
                                            data: Dict[str, Any],
                                            **kwargs) -> Dict[str, Any]:
        """
        生成综合分析（包含多种可视化）

        Args:
            analysis_type: 分析类型
            data: 数据
            **kwargs: 其他参数

        Returns:
            综合分析结果
        """
        self.logger.info(f"生成综合分析 - 类型: {analysis_type}")

        results = {}

        # 根据分析类型生成不同的可视化组合
        if analysis_type == "flood_analysis":
            # 洪水分析：图表 + 地图 + 3D场景 + 动画
            chart_task = await self._generate_chart(
                data=data.get("water_level_data", {}),
                chart_type="water_level",
                title="水位变化趋势"
            )
            results["chart"] = chart_task

            map_task = await self._generate_map(
                map_type="flood_evolution",
                flood_extent=data.get("flood_extent", {}),
                evolution_steps=data.get("evolution_steps", [])
            )
            results["map"] = map_task

            scene_task = await self._generate_scene(
                scene_type="flood_submersion",
                terrain=data.get("terrain", {}),
                flood_extent=data.get("flood_extent", {}),
                time_series=data.get("evolution_steps", [])
            )
            results["scene"] = scene_task

            animation_task = await self._generate_animation(
                animation_type="flood_propagation",
                flood_data=data.get("evolution_steps", []),
                duration=15000
            )
            results["animation"] = animation_task

        elif analysis_type == "reservoir_operation":
            # 水库调度：图表 + 地图
            chart_task = await self._generate_chart(
                data=data.get("operation_data", {}),
                chart_type="line",
                title="水库调度方案"
            )
            results["chart"] = chart_task

            map_task = await self._generate_map(
                map_type="reservoir_monitoring",
                reservoir_boundary=data.get("reservoir_boundary", {}),
                current_water_level=data.get("current_level", 0)
            )
            results["map"] = map_task

        elif analysis_type == "anomaly_detection":
            # 异常检测：图表 + 动画
            chart_task = await self._generate_chart(
                data=data.get("detection_data", {}),
                chart_type="anomaly",
                title="异常检测结果"
            )
            results["chart"] = chart_task

            animation_task = await self._generate_animation(
                animation_type="data_stream",
                data_points=data.get("anomaly_points", []),
                duration=8000
            )
            results["animation"] = animation_task

        # 生成综合报告
        report_result = await self.generate_report(
            report_type=f"{analysis_type}_report",
            **data
        )
        results["report"] = report_result

        return {
            "status": "success",
            "analysis_type": analysis_type,
            "components": results,
            "generated_at": datetime.now().isoformat()
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cache_size": len(self.viz_cache),
            "pipeline_count": len(self.pipelines)
        }
