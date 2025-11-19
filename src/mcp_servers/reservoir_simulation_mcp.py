"""
水库模拟模型MCP服务器
实现水库调度、水位控制和泄洪计算
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class ReservoirOperationMode(Enum):
    """水库运行模式"""
    NORMAL = "normal"  # 正常运行
    FLOOD_CONTROL = "flood_control"  # 防洪调度
    POWER_GENERATION = "power_generation"  # 发电优化
    WATER_SUPPLY = "water_supply"  # 供水调度
    EMERGENCY = "emergency"  # 应急调度

class ReservoirState(Enum):
    """水库状态"""
    NORMAL = "normal"
    ATTENTION = "attention"  # 注意
    WARNING = "warning"  # 警告
    DANGER = "danger"  # 危险
    EMERGENCY = "emergency"  # 紧急

@dataclass
class ReservoirCharacteristics:
    """水库特征参数"""
    name: str
    total_capacity: float  # 总库容 (m³)
    dead_capacity: float  # 死库容 (m³)
    flood_capacity: float  # 防洪库容 (m³)
    normal_water_level: float  # 正常蓄水位 (m)
    dead_water_level: float  # 死水位 (m)
    flood_limit_water_level: float  # 防洪限制水位 (m)
    dam_height: float  # 坝高 (m)
    crest_elevation: float  # 坝顶高程 (m)

@dataclass
class InflowForecast:
    """入库流量预报"""
    time_series: List[datetime]
    inflow_rates: List[float]  # 入库流量 (m³/s)
    confidence_level: float  # 置信水平

@dataclass
class ReservoirConstraints:
    """水库运行约束"""
    min_outflow: float  # 最小下泄流量 (m³/s)
    max_outflow: float  # 最大下泄流量 (m³/s)
    min_water_level: float  # 最低运行水位 (m)
    max_water_level: float  # 最高运行水位 (m)
    max_water_level_change: float  # 最大水位日变幅 (m)
    min_power_generation_flow: float  # 最小发电流量 (m³/s)

class ReservoirSimulationModel:
    """水库模拟模型"""

    def __init__(self, characteristics: ReservoirCharacteristics):
        self.characteristics = characteristics
        self.constraints = self._initialize_constraints()

        # 水位-库容关系曲线 (简化)
        self.level_capacity_curve = self._generate_level_capacity_curve()

        # 泄流能力曲线
        self.outflow_capacity_curve = self._generate_outflow_capacity_curve()

        # 发电效率曲线
        self.power_efficiency_curve = self._generate_power_efficiency_curve()

    def _initialize_constraints(self) -> ReservoirConstraints:
        """初始化运行约束"""
        return ReservoirConstraints(
            min_outflow=10.0,  # m³/s
            max_outflow=5000.0,  # m³/s
            min_water_level=self.characteristics.dead_water_level + 1.0,
            max_water_level=self.characteristics.normal_water_level,
            max_water_level_change=2.0,  # m/day
            min_power_generation_flow=50.0  # m³/s
        )

    def _generate_level_capacity_curve(self) -> Dict[float, float]:
        """生成水位-库容关系曲线"""
        # 简化的水位-库容关系 (实际应用中需要实测数据)
        min_level = self.characteristics.dead_water_level
        max_level = self.characteristics.normal_water_level

        levels = np.linspace(min_level, max_level, 50)
        capacities = []

        for level in levels:
            # 使用幂函数近似库容曲线
            relative_level = (level - min_level) / (max_level - min_level)
            capacity = (self.characteristics.total_capacity - self.characteristics.dead_capacity) * (relative_level ** 1.5) + self.characteristics.dead_capacity
            capacities.append(capacity)

        return dict(zip(levels, capacities))

    def _generate_outflow_capacity_curve(self) -> Dict[float, float]:
        """生成泄流能力曲线"""
        # 简化的泄流能力曲线
        levels = np.linspace(self.characteristics.dead_water_level, self.characteristics.normal_water_level, 20)
        outflows = []

        for level in levels:
            # 基于水头的泄流能力计算 (简化)
            head = level - self.characteristics.dead_water_level
            # 考虑不同泄洪设施
            spillway_flow = 0.5 * 9.81 * (head ** 1.5) if head > 0 else 0
            outlet_flow = 100 * np.sqrt(head) if head > 0 else 0
            total_outflow = min(spillway_flow + outlet_flow, self.constraints.max_outflow)
            outflows.append(total_outflow)

        return dict(zip(levels, outflows))

    def _generate_power_efficiency_curve(self) -> Dict[float, float]:
        """生成发电效率曲线"""
        # 简化的发电效率曲线
        levels = np.linspace(self.characteristics.dead_water_level, self.characteristics.normal_water_level, 15)
        efficiencies = []

        for level in levels:
            head = level - self.characteristics.dead_water_level
            # 效率随水头变化的简化模型
            efficiency = 0.85 * (1 - np.exp(-head / 10.0))
            efficiencies.append(max(0.1, efficiency))

        return dict(zip(levels, efficiencies))

    def level_to_capacity(self, water_level: float) -> float:
        """水位转库容"""
        levels = sorted(self.level_capacity_curve.keys())

        if water_level <= levels[0]:
            return self.level_capacity_curve[levels[0]]
        if water_level >= levels[-1]:
            return self.level_capacity_curve[levels[-1]]

        # 线性插值
        for i in range(len(levels) - 1):
            if levels[i] <= water_level <= levels[i + 1]:
                level1, level2 = levels[i], levels[i + 1]
                cap1, cap2 = self.level_capacity_curve[level1], self.level_capacity_curve[level2]
                return cap1 + (cap2 - cap1) * (water_level - level1) / (level2 - level1)

        return self.level_capacity_curve[levels[0]]

    def capacity_to_level(self, capacity: float) -> float:
        """库容转水位"""
        levels = sorted(self.level_capacity_curve.keys())
        capacities = [self.level_capacity_curve[level] for level in levels]

        if capacity <= capacities[0]:
            return levels[0]
        if capacity >= capacities[-1]:
            return levels[-1]

        # 线性插值
        for i in range(len(capacities) - 1):
            if capacities[i] <= capacity <= capacities[i + 1]:
                cap1, cap2 = capacities[i], capacities[i + 1]
                level1, level2 = levels[i], levels[i + 1]
                return level1 + (level2 - level1) * (capacity - cap1) / (cap2 - cap1)

        return levels[0]

    def calculate_water_balance(self, current_level: float, inflow: float, outflow: float, dt: float) -> float:
        """计算水量平衡"""
        current_capacity = self.level_to_capacity(current_level)

        # 水量变化 (m³)
        volume_change = (inflow - outflow) * dt

        # 新库容
        new_capacity = current_capacity + volume_change

        # 新水位
        new_level = self.capacity_to_level(new_capacity)

        return new_level

    def optimize_reservoir_operation(self,
                                   current_level: float,
                                   forecast: InflowForecast,
                                   target_level: Optional[float] = None,
                                   mode: ReservoirOperationMode = ReservoirOperationMode.NORMAL) -> List[Dict[str, Any]]:
        """优化水库调度"""

        if target_level is None:
            target_level = self.characteristics.normal_water_level

        operation_schedule = []

        for i, (time, inflow) in enumerate(zip(forecast.time_series, forecast.inflow_rates)):
            # 根据运行模式确定调度策略
            if mode == ReservoirOperationMode.FLOOD_CONTROL:
                # 防洪调度：预泄迎洪
                target_level = self.characteristics.flood_limit_water_level
                safe_outflow = max(inflow * 0.8, self.constraints.min_outflow)

            elif mode == ReservoirOperationMode.POWER_GENERATION:
                # 发电优化：保持高水位
                target_level = self.characteristics.normal_water_level * 0.95
                safe_outflow = max(inflow, self.constraints.min_power_generation_flow)

            elif mode == ReservoirOperationMode.WATER_SUPPLY:
                # 供水调度：稳定下泄
                safe_outflow = max(inflow, self.constraints.min_outflow)

            else:  # NORMAL
                # 正常运行：维持水位
                level_error = current_level - target_level
                safe_outflow = inflow - level_error * 100  # 简单的PID控制思想

            # 约束检查
            safe_outflow = max(self.constraints.min_outflow,
                             min(safe_outflow, self.constraints.max_outflow))

            # 计算水位变化
            new_level = self.calculate_water_balance(current_level, inflow, safe_outflow, 3600)  # 1小时

            # 检查水位约束
            if new_level > self.constraints.max_water_level:
                new_level = self.constraints.max_water_level
                # 需要增加泄流
                excess_capacity = self.level_to_capacity(new_level) - self.level_to_capacity(self.constraints.max_water_level)
                additional_outflow = excess_capacity / 3600
                safe_outflow += additional_outflow

            elif new_level < self.constraints.min_water_level:
                new_level = self.constraints.min_water_level
                # 需要减少泄流
                safe_outflow = max(self.constraints.min_outflow, safe_outflow * 0.8)

            # 计算发电量和效率
            power_generation = 0
            efficiency = 0
            if safe_outflow >= self.constraints.min_power_generation_flow:
                head = current_level - self.characteristics.dead_water_level
                efficiency = self._get_power_efficiency(current_level)
                power_generation = 9.81 * safe_outflow * head * efficiency / 1000  # MW

            operation_schedule.append({
                "time": time.isoformat(),
                "current_level": current_level,
                "target_level": target_level,
                "inflow": inflow,
                "outflow": safe_outflow,
                "new_level": new_level,
                "power_generation": power_generation,
                "efficiency": efficiency,
                "mode": mode.value
            })

            current_level = new_level

        return operation_schedule

    def _get_power_efficiency(self, water_level: float) -> float:
        """获取发电效率"""
        levels = sorted(self.power_efficiency_curve.keys())

        if water_level <= levels[0]:
            return self.power_efficiency_curve[levels[0]]
        if water_level >= levels[-1]:
            return self.power_efficiency_curve[levels[-1]]

        for i in range(len(levels) - 1):
            if levels[i] <= water_level <= levels[i + 1]:
                level1, level2 = levels[i], levels[i + 1]
                eff1, eff2 = self.power_efficiency_curve[level1], self.power_efficiency_curve[level2]
                return eff1 + (eff2 - eff1) * (water_level - level1) / (level2 - level1)

        return 0.8

    def assess_reservoir_state(self, current_level: float, inflow_rate: float) -> Dict[str, Any]:
        """评估水库状态"""
        # 计算各种指标
        relative_level = (current_level - self.characteristics.dead_water_level) / \
                        (self.characteristics.normal_water_level - self.characteristics.dead_water_level)

        current_capacity = self.level_to_capacity(current_level)
        capacity_ratio = (current_capacity - self.characteristics.dead_capacity) / \
                        (self.characteristics.total_capacity - self.characteristics.dead_capacity)

        # 确定风险等级
        if current_level >= self.characteristics.flood_limit_water_level:
            state = ReservoirState.EMERGENCY
            risk_level = 4
        elif current_level >= self.characteristics.normal_water_level * 0.95:
            state = ReservoirState.WARNING
            risk_level = 3
        elif current_level >= self.characteristics.normal_water_level * 0.85:
            state = ReservoirState.ATTENTION
            risk_level = 2
        else:
            state = ReservoirState.NORMAL
            risk_level = 1

        # 泄流能力评估
        max_possible_outflow = self._get_outflow_capacity(current_level)

        return {
            "current_level": current_level,
            "relative_level": relative_level,
            "capacity_ratio": capacity_ratio,
            "state": state.value,
            "risk_level": risk_level,
            "max_outflow_capacity": max_possible_outflow,
            "available_flood_capacity": self.characteristics.flood_capacity * (1 - capacity_ratio),
            "power_generation_potential": self._calculate_power_potential(current_level)
        }

    def _get_outflow_capacity(self, water_level: float) -> float:
        """获取泄流能力"""
        levels = sorted(self.outflow_capacity_curve.keys())

        if water_level <= levels[0]:
            return self.outflow_capacity_curve[levels[0]]
        if water_level >= levels[-1]:
            return self.outflow_capacity_curve[levels[-1]]

        for i in range(len(levels) - 1):
            if levels[i] <= water_level <= levels[i + 1]:
                level1, level2 = levels[i], levels[i + 1]
                out1, out2 = self.outflow_capacity_curve[level1], self.outflow_capacity_curve[level2]
                return out1 + (out2 - out1) * (water_level - level1) / (level2 - level1)

        return 0.0

    def _calculate_power_potential(self, water_level: float) -> float:
        """计算发电潜力"""
        head = water_level - self.characteristics.dead_water_level
        if head <= 0:
            return 0.0

        efficiency = self._get_power_efficiency(water_level)
        max_flow = min(self.constraints.max_outflow, self._get_outflow_capacity(water_level))

        # 理论最大发电功率
        power_potential = 9.81 * max_flow * head * efficiency / 1000  # MW
        return power_potential

class ReservoirSimulationMCPServer:
    """水库模拟模型MCP服务器"""

    def __init__(self):
        # 创建示例水库
        self.reservoir = self._create_example_reservoir()

    def _create_example_reservoir(self) -> ReservoirSimulationModel:
        """创建示例水库"""
        characteristics = ReservoirCharacteristics(
            name="三峡水库",
            total_capacity=39.3e9,  # 39.3亿立方米
            dead_capacity=17.1e9,   # 17.1亿立方米
            flood_capacity=22.2e9,  # 22.2亿立方米
            normal_water_level=175.0,  # 175m
            dead_water_level=145.0,    # 145m
            flood_limit_water_level=171.0,  # 171m
            dam_height=181.0,  # 181m
            crest_elevation=185.0  # 185m
        )

        return ReservoirSimulationModel(characteristics)

    async def simulate_reservoir_operation(
        self,
        current_water_level: float,
        forecast_hours: int = 24,
        average_inflow: float = 5000.0,  # m³/s
        operation_mode: str = "normal",
        target_water_level: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        水库调度模拟 - MCP工具接口

        Args:
            current_water_level: 当前水位 (m)
            forecast_hours: 预报时长 (小时)
            average_inflow: 平均入库流量 (m³/s)
            operation_mode: 运行模式 (normal/flood_control/power_generation/water_supply/emergency)
            target_water_level: 目标水位 (m)

        Returns:
            调度结果字典
        """

        try:
            # 参数验证
            if current_water_level < self.reservoir.characteristics.dead_water_level:
                return {
                    "status": "error",
                    "message": f"当前水位 {current_water_level}m 低于死水位 {self.reservoir.characteristics.dead_water_level}m"
                }

            if current_water_level > self.reservoir.characteristics.crest_elevation:
                return {
                    "status": "error",
                    "message": f"当前水位 {current_water_level}m 超过坝顶高程 {self.reservoir.characteristics.crest_elevation}m"
                }

            # 创建入库流量预报
            time_series = [datetime.now() + timedelta(hours=i) for i in range(forecast_hours)]

            # 生成变化的入库流量 (简化模型)
            inflow_variation = 0.2  # 20%变化
            inflow_rates = []
            for i in range(forecast_hours):
                # 添加日变化和随机波动
                daily_variation = np.sin(2 * np.pi * i / 24) * inflow_variation * average_inflow
                random_variation = np.random.normal(0, inflow_variation * average_inflow * 0.3)
                inflow = max(0, average_inflow + daily_variation + random_variation)
                inflow_rates.append(inflow)

            forecast = InflowForecast(
                time_series=time_series,
                inflow_rates=inflow_rates,
                confidence_level=0.85
            )

            # 转换运行模式
            try:
                mode = ReservoirOperationMode(operation_mode)
            except ValueError:
                return {
                    "status": "error",
                    "message": f"无效的运行模式: {operation_mode}"
                }

            # 评估当前状态
            current_state = self.reservoir.assess_reservoir_state(current_water_level, average_inflow)

            # 优化调度
            operation_schedule = self.reservoir.optimize_reservoir_operation(
                current_water_level,
                forecast,
                target_water_level,
                mode
            )

            # 计算调度结果统计
            outflows = [op["outflow"] for op in operation_schedule]
            water_levels = [op["new_level"] for op in operation_schedule]
            power_generations = [op["power_generation"] for op in operation_schedule]

            avg_outflow = np.mean(outflows)
            max_outflow = np.max(outflows)
            min_outflow = np.min(outflows)
            final_water_level = water_levels[-1]
            total_power_generation = np.sum(power_generations)  # MWh

            # 风险分析
            risk_analysis = self._analyze_operation_risks(water_levels, outflows)

            # 生成建议
            recommendations = self._generate_operation_recommendations(
                current_state, final_water_level, max_outflow, mode
            )

            return {
                "status": "success",
                "reservoir_info": {
                    "name": self.reservoir.characteristics.name,
                    "current_state": current_state,
                    "operation_mode": mode.value,
                    "forecast_hours": forecast_hours
                },
                "operation_schedule": operation_schedule,
                "statistics": {
                    "avg_outflow": avg_outflow,
                    "max_outflow": max_outflow,
                    "min_outflow": min_outflow,
                    "final_water_level": final_water_level,
                    "total_power_generation_mwh": total_power_generation,
                    "water_level_change": final_water_level - current_water_level
                },
                "risk_analysis": risk_analysis,
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"水库调度模拟失败: {str(e)}",
                "recommendations": ["请检查输入参数是否合理", "确认水库特征参数设置正确"]
            }

    def _analyze_operation_risks(self, water_levels: List[float], outflows: List[float]) -> Dict[str, Any]:
        """分析运行风险"""
        # 水位风险
        max_level = np.max(water_levels)
        min_level = np.min(water_levels)

        level_risk = "low"
        if max_level >= self.reservoir.characteristics.flood_limit_water_level:
            level_risk = "critical"
        elif max_level >= self.reservoir.characteristics.normal_water_level * 0.95:
            level_risk = "high"
        elif max_level >= self.reservoir.characteristics.normal_water_level * 0.85:
            level_risk = "medium"

        # 泄流风险
        max_outflow = np.max(outflows)
        outflow_risk = "low"
        if max_outflow > self.reservoir.constraints.max_outflow * 0.9:
            outflow_risk = "high"
        elif max_outflow > self.reservoir.constraints.max_outflow * 0.7:
            outflow_risk = "medium"

        # 水位变化率风险
        level_changes = np.diff(water_levels)
        max_level_change = np.max(np.abs(level_changes))
        change_risk = "low"
        if max_level_change > self.reservoir.constraints.max_water_level_change:
            change_risk = "high"
        elif max_level_change > self.reservoir.constraints.max_water_level_change * 0.7:
            change_risk = "medium"

        return {
            "level_risk": level_risk,
            "outflow_risk": outflow_risk,
            "change_risk": change_risk,
            "max_water_level": max_level,
            "min_water_level": min_level,
            "max_outflow": max_outflow,
            "max_level_change": max_level_change
        }

    def _generate_operation_recommendations(self, current_state: Dict[str, Any],
                                         final_water_level: float, max_outflow: float,
                                         mode: ReservoirOperationMode) -> List[str]:
        """生成运行建议"""
        recommendations = []

        # 基于当前状态的建议
        risk_level = current_state.get("risk_level", 1)
        if risk_level >= 3:
            recommendations.append("警告: 当前水库处于高风险状态，需要密切监控")
            recommendations.append("建议: 加强巡查频次，确保大坝安全")

        # 基于调度结果的建议
        if final_water_level > self.reservoir.characteristics.flood_limit_water_level:
            recommendations.append("紧急: 预报水位将超过防洪限制水位，需要加大泄流")

        if max_outflow > self.reservoir.constraints.max_outflow * 0.9:
            recommendations.append("警告: 最大泄流接近上限，需要谨慎控制")

        # 基于运行模式的建议
        if mode == ReservoirOperationMode.FLOOD_CONTROL:
            recommendations.append("防洪调度: 继续密切关注上游来水情况")
            recommendations.append("防洪调度: 保持足够的防洪库容")

        elif mode == ReservoirOperationMode.POWER_GENERATION:
            recommendations.append("发电优化: 在保证安全的前提下维持高水位运行")
            recommendations.append("发电优化: 合理安排机组运行方式")

        return recommendations

    async def calculate_flood_discharge(
        self,
        current_water_level: float,
        target_water_level: float,
        discharge_duration: int = 12  # hours
    ) -> Dict[str, Any]:
        """
        计算泄洪方案 - MCP工具接口

        Args:
            current_water_level: 当前水位 (m)
            target_water_level: 目标水位 (m)
            discharge_duration: 泄洪时长 (小时)

        Returns:
            泄洪方案
        """

        try:
            if current_water_level <= target_water_level:
                return {
                    "status": "warning",
                    "message": "当前水位已低于或等于目标水位，无需泄洪",
                    "required_discharge": 0.0,
                    "discharge_schedule": []
                }

            # 计算需要释放的水量
            current_capacity = self.reservoir.level_to_capacity(current_water_level)
            target_capacity = self.reservoir.level_to_capacity(target_water_level)
            volume_to_release = current_capacity - target_capacity  # m³

            if volume_to_release <= 0:
                return {
                    "status": "warning",
                    "message": "计算得到的水量为负值，请检查输入参数",
                    "required_discharge": 0.0,
                    "discharge_schedule": []
                }

            # 计算平均泄流
            total_seconds = discharge_duration * 3600
            average_discharge = volume_to_release / total_seconds  # m³/s

            # 检查泄流能力
            max_capacity = self.reservoir._get_outflow_capacity(current_water_level)
            if average_discharge > max_capacity:
                return {
                    "status": "error",
                    "message": f"所需平均泄流 {average_discharge:.1f} m³/s 超过当前泄流能力 {max_capacity:.1f} m³/s",
                    "required_discharge": average_discharge,
                    "max_capacity": max_capacity,
                    "recommendations": ["延长泄洪时间", "分阶段泄洪", "提前预泄"]
                }

            # 生成泄洪调度
            discharge_schedule = []
            remaining_volume = volume_to_release

            for hour in range(discharge_duration):
                # 泄流递减策略 (考虑水位下降)
                progress = hour / discharge_duration
                current_discharge = average_discharge * (1 - 0.3 * progress)  # 递减30%

                # 确保在安全范围内
                current_discharge = max(self.reservoir.constraints.min_outflow,
                                      min(current_discharge, max_capacity))

                # 计算时段泄水量
                hourly_volume = current_discharge * 3600
                remaining_volume -= hourly_volume

                # 估算水位变化
                current_capacity = self.reservoir.level_to_capacity(current_water_level)
                new_capacity = current_capacity - hourly_volume
                new_water_level = self.reservoir.capacity_to_level(max(0, new_capacity))

                discharge_schedule.append({
                    "hour": hour + 1,
                    "discharge_rate": current_discharge,
                    "cumulative_volume": volume_to_release - max(0, remaining_volume),
                    "estimated_water_level": new_water_level,
                    "safety_status": "safe" if current_discharge < max_capacity * 0.9 else "caution"
                })

                current_water_level = new_water_level

            return {
                "status": "success",
                "discharge_summary": {
                    "total_volume_to_release": volume_to_release,
                    "average_discharge": average_discharge,
                    "discharge_duration": discharge_duration,
                    "max_required_discharge": max([d["discharge_rate"] for d in discharge_schedule])
                },
                "discharge_schedule": discharge_schedule,
                "safety_assessment": {
                    "overall_risk": "low" if average_discharge < max_capacity * 0.7 else "medium",
                    "max_capacity_utilization": max([d["discharge_rate"] for d in discharge_schedule]) / max_capacity * 100
                },
                "recommendations": [
                    "严格按照调度方案执行泄洪",
                    "密切监测下游水位变化",
                    "保持与下游部门的沟通协调",
                    "根据实时水情调整泄洪策略"
                ]
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"泄洪计算失败: {str(e)}",
                "recommendations": ["请检查输入参数是否合理", "确认水库特征参数设置正确"]
            }