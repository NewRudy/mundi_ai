"""
洪水演进模型MCP服务器
基于圣维南方程组的洪水演进模拟
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import math
from ..connectors.usgs_connector import USGSConnector

@dataclass
class FloodBoundaryConditions:
    """洪水边界条件"""
    upstream_flow: List[Tuple[datetime, float]]  # 上游流量 (时间, 流量)
    downstream_level: List[Tuple[datetime, float]]  # 下游水位 (时间, 水位)
    lateral_inflow: Optional[List[Tuple[datetime, float]]] = None  # 侧向入流

@dataclass
class RiverSection:
    """河道断面"""
    station: float  # 断面位置 (km)
    elevation: np.ndarray  # 高程 (m)
    area: np.ndarray  # 断面面积 (m²)
    width: np.ndarray  # 水面宽度 (m)
    hydraulic_radius: np.ndarray  # 水力半径 (m)

@dataclass
class FloodSimulationResult:
    """洪水模拟结果"""
    time_series: List[datetime]
    water_levels: np.ndarray  # 水位 (m) [time, section]
    discharges: np.ndarray  # 流量 (m³/s) [time, section]
    velocities: np.ndarray  # 流速 (m/s) [time, section]
    flood_areas: np.ndarray  # 淹没面积 (m²) [time, section]
    risk_levels: np.ndarray  # 风险等级 [time, section]

class SaintVenantSolver:
    """圣维南方程组求解器"""

    def __init__(self,
                 river_length: float = 100.0,  # 河道长度 (km)
                 dx: float = 1.0,  # 空间步长 (km)
                 dt: float = 60.0,  # 时间步长 (s)
                 manning_n: float = 0.035,  # 曼宁糙率系数
                 gravity: float = 9.81):  # 重力加速度

        self.river_length = river_length
        self.dx = dx
        self.dt = dt
        self.manning_n = manning_n
        self.gravity = gravity

        # 计算网格点数
        self.nx = int(river_length / dx) + 1
        self.x = np.linspace(0, river_length, self.nx)

        # 初始化数组
        self.h = np.zeros(self.nx)  # 水深
        self.q = np.zeros(self.nx)  # 单宽流量
        self.z = np.zeros(self.nx)  # 河底高程

        # 稳定性参数
        self.courant_number = 0.5
        self.max_iterations = 1000

    def initialize_river_bed(self, bed_slope: float = 0.001):
        """初始化河床高程"""
        self.z = -bed_slope * self.x

    def calculate_cross_section_properties(self, water_level: float, section_id: int) -> Dict[str, float]:
        """计算断面水力特性"""
        # 简化的梯形断面假设
        depth = max(0, water_level - self.z[section_id])
        bottom_width = 50.0  # 底宽 (m)
        side_slope = 2.0  # 边坡系数

        # 水面宽度
        surface_width = bottom_width + 2 * side_slope * depth

        # 过水断面面积
        area = (bottom_width + surface_width) * depth / 2

        # 湿周
        wetted_perimeter = bottom_width + 2 * depth * np.sqrt(1 + side_slope**2)

        # 水力半径
        hydraulic_radius = area / wetted_perimeter if wetted_perimeter > 0 else 0

        return {
            'depth': depth,
            'area': area,
            'width': surface_width,
            'wetted_perimeter': wetted_perimeter,
            'hydraulic_radius': hydraulic_radius
        }

    def calculate_manning_velocity(self, discharge: float, water_level: float, section_id: int) -> float:
        """用曼宁公式计算流速"""
        props = self.calculate_cross_section_properties(water_level, section_id)

        if props['area'] <= 0 or props['hydraulic_radius'] <= 0:
            return 0.0

        # 曼宁公式: V = (1/n) * R^(2/3) * S^(1/2)
        slope = abs(self.z[min(section_id + 1, self.nx - 1)] - self.z[max(section_id - 1, 0)]) / (2 * self.dx * 1000)
        velocity = (1 / self.manning_n) * (props['hydraulic_radius'] ** (2/3)) * (slope ** 0.5)

        return velocity

    def saint_venant_equations(self, h: np.ndarray, q: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """圣维南方程组"""
        # 连续性方程: ∂h/∂t + ∂q/∂x = 0
        # 动量方程: ∂q/∂t + ∂(q²/h)/∂x + g*h*∂h/∂x = g*h*(S₀ - Sf)

        dh_dt = np.zeros_like(h)
        dq_dt = np.zeros_like(q)

        # 计算空间导数 (中心差分)
        for i in range(1, self.nx - 1):
            # 连续性方程
            dq_dx = (q[i + 1] - q[i - 1]) / (2 * self.dx * 1000)  # 转换为m
            dh_dt[i] = -dq_dx

            # 动量方程各项
            if h[i] > 0:
                # 对流项
                d_q2h_dx = ((q[i + 1]**2 / h[i + 1]) - (q[i - 1]**2 / h[i - 1])) / (2 * self.dx * 1000)

                # 压力项
                dh_dx = (h[i + 1] - h[i - 1]) / (2 * self.dx * 1000)

                # 底坡项
                dz_dx = (self.z[i + 1] - self.z[i - 1]) / (2 * self.dx * 1000)
                s0 = -dz_dx  # 底坡

                # 摩擦坡降 (曼宁公式)
                velocity = q[i] / h[i]
                hydraulic_radius = h[i] / (1 + 2 * h[i] / 50)  # 简化计算
                sf = (self.manning_n**2 * velocity**2) / (hydraulic_radius**(4/3))

                # 动量方程
                dq_dt[i] = -d_q2h_dx - self.gravity * h[i] * (dh_dx + dz_dx) - self.gravity * h[i] * sf

        return dh_dt, dq_dt

    def apply_boundary_conditions(self, h: np.ndarray, q: np.ndarray,
                                bc: FloodBoundaryConditions, time_idx: int) -> None:
        """应用边界条件"""
        # 上游边界 (流量给定)
        if bc.upstream_flow and time_idx < len(bc.upstream_flow):
            q[0] = bc.upstream_flow[time_idx][1] / 50.0  # 转换为单宽流量

        # 下游边界 (水位给定)
        if bc.downstream_level and time_idx < len(bc.downstream_level):
            h[-1] = bc.downstream_level[time_idx][1] - self.z[-1]

    def check_stability(self, h: np.ndarray, q: np.ndarray) -> bool:
        """检查数值稳定性"""
        # CFL条件检查
        max_velocity = np.max(np.abs(q / (h + 1e-6)))  # 避免除零
        max_depth = np.max(h)

        if max_depth > 0:
            wave_speed = np.sqrt(self.gravity * max_depth)
            cfl = (max_velocity + wave_speed) * self.dt / (self.dx * 1000)

            if cfl > self.courant_number:
                print(f"警告: CFL条件不满足 (CFL = {cfl:.3f} > {self.courant_number})")
                return False

        # 检查水深合理性
        if np.any(h < 0):
            print("警告: 出现负水深")
            return False

        return True

    def calculate_flood_risk_level(self, water_level: float, bank_height: float) -> int:
        """计算洪水风险等级"""
        if water_level < bank_height * 0.8:
            return 1  # 低风险
        elif water_level < bank_height * 0.95:
            return 2  # 中等风险
        elif water_level < bank_height * 1.05:
            return 3  # 高风险
        else:
            return 4  # 极高风险

class FloodEvolutionMCPServer:
    """洪水演进模型MCP服务器"""

    def __init__(self):
        self.solver = SaintVenantSolver()
        self.solver.initialize_river_bed()

    async def simulate_flood_propagation(
        self,
        river_length: float = 100.0,
        simulation_hours: float = 24.0,
        upstream_flow_rate: float = 1000.0,  # m³/s
        downstream_water_level: float = 10.0,  # m
        manning_roughness: float = 0.035,
        bed_slope: float = 0.001,
        initial_water_level: float = 5.0,  # m
        bank_height: float = 8.0  # m
    ) -> Dict[str, Any]:
        """
        洪水演进模拟 - MCP工具接口

        Args:
            river_length: 河道长度 (km)
            simulation_hours: 模拟时长 (小时)
            upstream_flow_rate: 上游流量 (m³/s)
            downstream_water_level: 下游水位 (m)
            manning_roughness: 曼宁糙率系数
            bed_slope: 河床坡度
            initial_water_level: 初始水位 (m)
            bank_height: 堤岸高度 (m)

        Returns:
            模拟结果字典
        """

        try:
            # 更新求解器参数
            self.solver = SaintVenantSolver(
                river_length=river_length,
                manning_n=manning_roughness
            )
            self.solver.initialize_river_bed(bed_slope)

            # 计算时间步数
            total_seconds = int(simulation_hours * 3600)
            nt = int(total_seconds / self.solver.dt)

            # 初始化条件
            h = np.full(self.solver.nx, initial_water_level - self.solver.z)
            q = np.full(self.solver.nx, upstream_flow_rate / 50.0)  # 单宽流量

            # 创建边界条件
            time_series = [datetime.now() + timedelta(seconds=i * self.solver.dt) for i in range(nt)]

            bc = FloodBoundaryConditions(
                upstream_flow=[(t, upstream_flow_rate) for t in time_series],
                downstream_level=[(t, downstream_water_level) for t in time_series]
            )

            # 存储结果
            water_levels = np.zeros((nt, self.solver.nx))
            discharges = np.zeros((nt, self.solver.nx))
            velocities = np.zeros((nt, self.solver.nx))
            flood_areas = np.zeros((nt, self.solver.nx))
            risk_levels = np.zeros((nt, self.solver.nx))

            # 时间推进模拟
            for n in range(nt):
                # 应用边界条件
                self.solver.apply_boundary_conditions(h, q, bc, n)

                # 计算圣维南方程组
                dh_dt, dq_dt = self.solver.saint_venant_equations(h, q)

                # 时间积分 (前向欧拉)
                h_new = h + dh_dt * self.solver.dt
                q_new = q + dq_dt * self.solver.dt

                # 稳定性检查
                if not self.solver.check_stability(h_new, q_new):
                    print(f"模拟在时刻 {n * self.solver.dt} 秒不稳定，调整参数")
                    break

                # 更新变量
                h, q = h_new, q_new

                # 存储结果
                water_levels[n] = h
                discharges[n] = q * 50.0  # 转换回总流量

                # 计算流速
                for i in range(self.solver.nx):
                    if h[i] > 0:
                        velocities[n, i] = self.solver.calculate_manning_velocity(
                            q[i] * 50.0, h[i] + self.solver.z[i], i
                        )

                        # 计算洪水风险
                        current_water_level = h[i] + self.solver.z[i]
                        risk_levels[n, i] = self.solver.calculate_flood_risk_level(
                            current_water_level, bank_height
                        )

                        # 计算淹没面积 (简化)
                        flood_areas[n, i] = self.solver.calculate_cross_section_properties(
                            current_water_level, i
                        )['area']

            # 计算关键指标
            max_water_level = np.max(water_levels + self.solver.z.reshape(1, -1))
            max_discharge = np.max(discharges)
            max_velocity = np.max(velocities)
            max_flood_area = np.max(flood_areas)
            max_risk_level = np.max(risk_levels)

            # 风险区域统计
            high_risk_areas = np.sum(risk_levels >= 3) / risk_levels.size

            return {
                "status": "success",
                "simulation_parameters": {
                    "river_length": river_length,
                    "simulation_hours": simulation_hours,
                    "upstream_flow_rate": upstream_flow_rate,
                    "downstream_water_level": downstream_water_level,
                    "manning_roughness": manning_roughness,
                    "bed_slope": bed_slope,
                    "initial_water_level": initial_water_level,
                    "bank_height": bank_height
                },
                "results": {
                    "max_water_level": float(max_water_level),
                    "max_discharge": float(max_discharge),
                    "max_velocity": float(max_velocity),
                    "max_flood_area": float(max_flood_area),
                    "max_risk_level": int(max_risk_level),
                    "high_risk_area_percentage": float(high_risk_areas * 100),
                    "time_series": [t.isoformat() for t in time_series[:nt]],
                    "distance_series": self.solver.x.tolist(),
                    "water_levels": water_levels.tolist(),
                    "discharges": discharges.tolist(),
                    "velocities": velocities.tolist(),
                    "flood_areas": flood_areas.tolist(),
                    "risk_levels": risk_levels.tolist()
                },
                "warnings": self._get_simulation_warnings(water_levels, risk_levels, bank_height),
                "recommendations": self._get_recommendations(risk_levels, high_risk_areas)
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"洪水演进模拟失败: {str(e)}",
                "recommendations": ["请检查输入参数是否合理", "建议减小时间步长或空间步长", "检查边界条件设置"]
            }

    def _get_simulation_warnings(self, water_levels: np.ndarray, risk_levels: np.ndarray, bank_height: float) -> List[str]:
        """获取模拟警告信息"""
        warnings = []

        max_level = np.max(water_levels)
        if max_level > bank_height:
            warnings.append(f"警告: 最高水位 {max_level:.2f}m 超过堤岸高度 {bank_height:.2f}m")

        if np.any(risk_levels >= 3):
            high_risk_count = np.sum(risk_levels >= 3)
            warnings.append(f"警告: 发现 {high_risk_count} 个高风险区域")

        return warnings

    def _get_recommendations(self, risk_levels: np.ndarray, high_risk_areas: float) -> List[str]:
        """获取专业建议"""
        recommendations = []

        if high_risk_areas > 0.1:  # 超过10%的高风险区域
            recommendations.append("建议: 加强洪水预警和应急响应")
            recommendations.append("建议: 提前转移下游居民")
            recommendations.append("建议: 准备防洪物资和设备")

        if high_risk_areas > 0.3:  # 超过30%的高风险区域
            recommendations.append("紧急: 立即启动一级应急响应")
            recommendations.append("紧急: 通知下游所有居民紧急撤离")
            recommendations.append("紧急: 开启所有泄洪设施")

        if high_risk_areas < 0.05:  # 少于5%的高风险区域
            recommendations.append("建议: 继续监测水情变化")
            recommendations.append("建议: 保持正常调度运行")

        return recommendations

    async def validate_flood_simulation(self,
                                     simulation_results: Dict[str, Any],
                                     max_water_level_threshold: float = 15.0,
                                     max_velocity_threshold: float = 5.0) -> Dict[str, Any]:
        """
        验证洪水模拟结果

        Args:
            simulation_results: 模拟结果
            max_water_level_threshold: 最大水位阈值
            max_velocity_threshold: 最大流速阈值

        Returns:
            验证结果
        """
        try:
            if simulation_results.get("status") != "success":
                return {
                    "valid": False,
                    "errors": ["模拟未成功完成"],
                    "warnings": []
                }

            results = simulation_results.get("results", {})
            errors = []
            warnings = []

            # 检查水位合理性
            max_water_level = results.get("max_water_level", 0)
            if max_water_level > max_water_level_threshold:
                errors.append(f"最高水位 {max_water_level:.2f}m 超过阈值 {max_water_level_threshold}m")

            # 检查流速合理性
            max_velocity = results.get("max_velocity", 0)
            if max_velocity > max_velocity_threshold:
                warnings.append(f"最大流速 {max_velocity:.2f}m/s 超过建议阈值 {max_velocity_threshold}m/s")

            # 检查质量守恒
            discharges = np.array(results.get("discharges", []))
            if discharges.size > 0:
                discharge_variation = np.std(discharges[-1]) / np.mean(discharges[-1]) if np.mean(discharges[-1]) > 0 else 0
                if discharge_variation > 0.5:
                    warnings.append(f"流量变化系数 {discharge_variation:.3f} 较大，建议检查边界条件")

            # 检查风险等级分布
            risk_levels = np.array(results.get("risk_levels", []))
            if risk_levels.size > 0:
                max_risk = np.max(risk_levels)
                if max_risk >= 4:
                    errors.append("发现极高风险区域，需要立即采取应急措施")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "validation_score": max(0, 1.0 - len(errors) * 0.3 - len(warnings) * 0.1)
            }

        except Exception as e:
            return {
                "valid": False,
                "errors": [f"验证过程出错: {str(e)}"],
                "warnings": []
            }