"""
风险评估模型MCP服务器
实现综合风险评估和影响分析
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import math

class RiskType(Enum):
    """风险类型"""
    FLOOD = "flood"  # 洪水风险
    STRUCTURAL = "structural"  # 结构风险
    OPERATIONAL = "operational"  # 运行风险
    ENVIRONMENTAL = "environmental"  # 环境风险
    ECONOMIC = "economic"  # 经济风险
    SOCIAL = "social"  # 社会风险

class RiskLevel(Enum):
    """风险等级"""
    VERY_LOW = 1  # 极低风险
    LOW = 2  # 低风险
    MEDIUM = 3  # 中等风险
    HIGH = 4  # 高风险
    VERY_HIGH = 5  # 极高风险

@dataclass
class RiskFactor:
    """风险因子"""
    name: str
    type: RiskType
    probability: float  # 发生概率 (0-1)
    impact: float  # 影响程度 (0-10)
    detectability: float  # 可检测性 (0-1)
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    weight: float = 1.0  # 权重

@dataclass
class VulnerabilityAssessment:
    """脆弱性评估"""
    physical_vulnerability: float  # 物理脆弱性 (0-1)
    operational_vulnerability: float  # 运行脆弱性 (0-1)
    organizational_vulnerability: float  # 组织脆弱性 (0-1)
    social_vulnerability: float  # 社会脆弱性 (0-1)
    economic_vulnerability: float  # 经济脆弱性 (0-1)

@dataclass
class ExposureAssessment:
    """暴露度评估"""
    population_exposure: float  # 人口暴露度 (0-1)
    asset_exposure: float  # 资产暴露度 (0-1)
    infrastructure_exposure: float  # 基础设施暴露度 (0-1)
    environmental_exposure: float  # 环境暴露度 (0-1)

class RiskAssessmentEngine:
    """风险评估引擎"""

    def __init__(self):
        # 风险权重系数
        self.risk_weights = {
            RiskType.FLOOD: 0.3,
            RiskType.STRUCTURAL: 0.25,
            RiskType.OPERATIONAL: 0.2,
            RiskType.ENVIRONMENTAL: 0.1,
            RiskType.ECONOMIC: 0.1,
            RiskType.SOCIAL: 0.05
        }

        # 风险等级阈值
        self.risk_thresholds = {
            RiskLevel.VERY_LOW: 0.2,
            RiskLevel.LOW: 0.4,
            RiskLevel.MEDIUM: 0.6,
            RiskLevel.HIGH: 0.8,
            RiskLevel.VERY_HIGH: 1.0
        }

    def calculate_risk_score(self, probability: float, impact: float, vulnerability: float, exposure: float) -> float:
        """计算综合风险评分"""
        # 基础风险公式: R = P × I × V × E
        base_risk = probability * (impact / 10.0) * vulnerability * exposure

        # 考虑可检测性的调整
        detectability_factor = 1.0  # 简化处理

        return min(1.0, base_risk * detectability_factor)

    def assess_risk_level(self, risk_score: float) -> RiskLevel:
        """评估风险等级"""
        if risk_score < self.risk_thresholds[RiskLevel.VERY_LOW]:
            return RiskLevel.VERY_LOW
        elif risk_score < self.risk_thresholds[RiskLevel.LOW]:
            return RiskLevel.LOW
        elif risk_score < self.risk_thresholds[RiskLevel.MEDIUM]:
            return RiskLevel.MEDIUM
        elif risk_score < self.risk_thresholds[RiskLevel.HIGH]:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH

    def calculate_flood_risk(self, water_level: float, discharge: float,
                           historical_max_level: float, historical_max_discharge: float,
                           dam_height: float, population_density: float) -> Dict[str, float]:
        """计算洪水风险"""
        # 概率评估
        level_probability = min(1.0, water_level / historical_max_level)
        discharge_probability = min(1.0, discharge / historical_max_discharge)
        flood_probability = max(level_probability, discharge_probability)

        # 影响评估
        level_impact = min(10.0, (water_level / dam_height) * 10)
        discharge_impact = min(10.0, (discharge / historical_max_discharge) * 10)
        flood_impact = max(level_impact, discharge_impact)

        # 人口影响系数
        population_factor = min(1.0, population_density / 1000.0)

        return {
            "probability": flood_probability,
            "impact": flood_impact,
            "population_factor": population_factor,
            "risk_score": flood_probability * (flood_impact / 10.0) * population_factor
        }

    def calculate_structural_risk(self, stress_level: float, age_years: int,
                                design_capacity: float, maintenance_score: float) -> Dict[str, float]:
        """计算结构风险"""
        # 应力风险
        stress_probability = min(1.0, stress_level / design_capacity)

        # 老化风险
        age_factor = min(1.0, age_years / 50.0)  # 50年老化系数

        # 维护风险
        maintenance_factor = max(0.1, 1.0 - maintenance_score / 100.0)

        # 综合结构风险概率
        structural_probability = max(stress_probability, age_factor, maintenance_factor)

        # 结构失效影响 (简化评估)
        structural_impact = 8.0 if structural_probability > 0.7 else 5.0

        return {
            "probability": structural_probability,
            "impact": structural_impact,
            "stress_factor": stress_probability,
            "age_factor": age_factor,
            "maintenance_factor": maintenance_factor
        }

    def calculate_operational_risk(self, operational_data: Dict[str, float]) -> Dict[str, float]:
        """计算运行风险"""
        # 运行参数风险因子
        risk_factors = {
            "efficiency_deviation": abs(operational_data.get("current_efficiency", 100) - 100) / 100.0,
            "temperature_deviation": abs(operational_data.get("current_temperature", 20) - 20) / 40.0,
            "vibration_level": operational_data.get("vibration_level", 0) / 10.0,
            "pressure_deviation": abs(operational_data.get("current_pressure", 1.0) - 1.0) / 2.0,
            "power_factor": max(0, 1.0 - operational_data.get("power_factor", 1.0))
        }

        # 综合运行风险概率
        operational_probability = np.mean(list(risk_factors.values()))

        # 运行风险影响
        operational_impact = 6.0  # 中等影响

        return {
            "probability": operational_probability,
            "impact": operational_impact,
            "risk_factors": risk_factors
        }

class VulnerabilityAssessmentEngine:
    """脆弱性评估引擎"""

    def __init__(self):
        # 脆弱性评估权重
        self.vulnerability_weights = {
            "physical": 0.3,
            "operational": 0.25,
            "organizational": 0.2,
            "social": 0.15,
            "economic": 0.1
        }

    def assess_physical_vulnerability(self, structure_age: int, design_standard: float,
                                    maintenance_status: float, inspection_score: float) -> float:
        """评估物理脆弱性"""
        # 结构老化脆弱性
        aging_vulnerability = min(1.0, structure_age / 50.0)

        # 设计标准脆弱性
        design_vulnerability = max(0.0, 1.0 - design_standard / 100.0)

        # 维护状况脆弱性
        maintenance_vulnerability = max(0.0, 1.0 - maintenance_status / 100.0)

        # 检查评分脆弱性
        inspection_vulnerability = max(0.0, 1.0 - inspection_score / 100.0)

        # 综合物理脆弱性
        physical_vulnerability = np.mean([
            aging_vulnerability,
            design_vulnerability,
            maintenance_vulnerability,
            inspection_vulnerability
        ])

        return physical_vulnerability

    def assess_operational_vulnerability(self, redundancy_level: float,
                                       automation_level: float, training_level: float) -> float:
        """评估运行脆弱性"""
        # 冗余度脆弱性 (反向指标)
        redundancy_vulnerability = max(0.0, 1.0 - redundancy_level)

        # 自动化水平脆弱性 (反向指标)
        automation_vulnerability = max(0.0, 1.0 - automation_level)

        # 培训水平脆弱性 (反向指标)
        training_vulnerability = max(0.0, 1.0 - training_level)

        # 综合运行脆弱性
        operational_vulnerability = np.mean([
            redundancy_vulnerability,
            automation_vulnerability,
            training_vulnerability
        ])

        return operational_vulnerability

    def assess_organizational_vulnerability(self, preparedness_score: float,
                                          response_time: float, communication_score: float) -> float:
        """评估组织脆弱性"""
        # 准备充分性脆弱性 (反向指标)
        preparedness_vulnerability = max(0.0, 1.0 - preparedness_score / 100.0)

        # 响应时间脆弱性
        response_vulnerability = min(1.0, response_time / 60.0)  # 60分钟为基准

        # 沟通协调脆弱性 (反向指标)
        communication_vulnerability = max(0.0, 1.0 - communication_score / 100.0)

        # 综合组织脆弱性
        organizational_vulnerability = np.mean([
            preparedness_vulnerability,
            response_vulnerability,
            communication_vulnerability
        ])

        return organizational_vulnerability

class ExposureAssessmentEngine:
    """暴露度评估引擎"""

    def __init__(self):
        # 暴露度评估基准值
        self.exposure_baseline = {
            "population": 1000,  # 人口基准
            "asset_value": 1e8,  # 资产价值基准 (元)
            "infrastructure_density": 10,  # 基础设施密度基准
            "environmental_sensitivity": 5.0  # 环境敏感度基准
        }

    def assess_population_exposure(self, population_density: float, proximity_distance: float) -> float:
        """评估人口暴露度"""
        # 人口密度暴露度
        density_exposure = min(1.0, population_density / self.exposure_baseline["population"])

        # 距离暴露度 (距离越近，暴露度越高)
        proximity_exposure = max(0.0, 1.0 - proximity_distance / 1000.0)  # 1km为基准

        # 综合人口暴露度
        population_exposure = np.mean([density_exposure, proximity_exposure])

        return population_exposure

    def assess_asset_exposure(self, asset_value: float, criticality_score: float) -> float:
        """评估资产暴露度"""
        # 资产价值暴露度
        value_exposure = min(1.0, asset_value / self.exposure_baseline["asset_value"])

        # 关键性暴露度
        criticality_exposure = criticality_score / 10.0

        # 综合资产暴露度
        asset_exposure = np.mean([value_exposure, criticality_exposure])

        return asset_exposure

    def assess_infrastructure_exposure(self, infrastructure_density: float,
                                     interdependency_score: float) -> float:
        """评估基础设施暴露度"""
        # 基础设施密度暴露度
        density_exposure = min(1.0, infrastructure_density / self.exposure_baseline["infrastructure_density"])

        # 相互依赖度暴露度
        interdependency_exposure = interdependency_score / 10.0

        # 综合基础设施暴露度
        infrastructure_exposure = np.mean([density_exposure, interdependency_exposure])

        return infrastructure_exposure

class RiskPropagationAnalyzer:
    """风险传播分析器"""

    def __init__(self):
        # 风险传播系数矩阵
        self.propagation_matrix = {
            RiskType.FLOOD: {
                RiskType.STRUCTURAL: 0.8,
                RiskType.OPERATIONAL: 0.6,
                RiskType.ENVIRONMENTAL: 0.7,
                RiskType.ECONOMIC: 0.5,
                RiskType.SOCIAL: 0.4
            },
            RiskType.STRUCTURAL: {
                RiskType.FLOOD: 0.3,
                RiskType.OPERATIONAL: 0.9,
                RiskType.ENVIRONMENTAL: 0.4,
                RiskType.ECONOMIC: 0.7,
                RiskType.SOCIAL: 0.6
            },
            RiskType.OPERATIONAL: {
                RiskType.FLOOD: 0.2,
                RiskType.STRUCTURAL: 0.5,
                RiskType.ENVIRONMENTAL: 0.3,
                RiskType.ECONOMIC: 0.8,
                RiskType.SOCIAL: 0.3
            }
        }

    def analyze_risk_propagation(self, primary_risks: Dict[RiskType, float]) -> Dict[RiskType, float]:
        """分析风险传播"""
        propagated_risks = {}

        for risk_type in RiskType:
            if risk_type in [RiskType.ENVIRONMENTAL, RiskType.ECONOMIC, RiskType.SOCIAL]:
                # 这些是次要风险，需要计算传播
                propagated_risk = 0.0

                for primary_type, primary_risk in primary_risks.items():
                    if primary_type in self.propagation_matrix and risk_type in self.propagation_matrix[primary_type]:
                        propagation_coefficient = self.propagation_matrix[primary_type][risk_type]
                        propagated_risk += primary_risk * propagation_coefficient

                propagated_risks[risk_type] = min(1.0, propagated_risk)
            else:
                # 这些是主要风险，直接使用原始值
                propagated_risks[risk_type] = primary_risks.get(risk_type, 0.0)

        return propagated_risks

    def calculate_cascading_risk(self, risk_scores: Dict[RiskType, float]) -> float:
        """计算级联风险"""
        # 级联风险 = 1 - 产品(1 - 风险_i)
        cascading_risk = 1.0 - np.prod([1.0 - score for score in risk_scores.values()])
        return cascading_risk

class RiskAssessmentMCPServer:
    """风险评估模型MCP服务器"""

    def __init__(self):
        self.risk_engine = RiskAssessmentEngine()
        self.vulnerability_engine = VulnerabilityAssessmentEngine()
        self.exposure_engine = ExposureAssessmentEngine()
        self.propagation_analyzer = RiskPropagationAnalyzer()

    async def assess_comprehensive_risk(
        self,
        current_water_level: float,
        current_discharge: float,
        historical_max_level: float,
        historical_max_discharge: float,
        dam_height: float,
        population_density: float = 100.0,
        structure_age: int = 20,
        design_standard: float = 85.0,
        maintenance_score: float = 80.0,
        inspection_score: float = 90.0,
        operational_data: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        综合风险评估 - MCP工具接口

        Args:
            current_water_level: 当前水位 (m)
            current_discharge: 当前流量 (m³/s)
            historical_max_level: 历史最高水位 (m)
            historical_max_discharge: 历史最大流量 (m³/s)
            dam_height: 坝高 (m)
            population_density: 人口密度 (人/km²)
            structure_age: 结构年龄 (年)
            design_standard: 设计标准 (分)
            maintenance_score: 维护评分 (分)
            inspection_score: 检查评分 (分)
            operational_data: 运行数据

        Returns:
            综合风险评估结果
        """

        try:
            # 参数验证
            if current_water_level < 0 or current_discharge < 0:
                return {
                    "status": "error",
                    "message": "水位和流量不能为负值"
                }

            if historical_max_level <= 0 or historical_max_discharge <= 0:
                return {
                    "status": "error",
                    "message": "历史最大值必须大于0"
                }

            # 默认运行数据
            if operational_data is None:
                operational_data = {
                    "current_efficiency": 95.0,
                    "current_temperature": 18.0,
                    "vibration_level": 2.0,
                    "current_pressure": 1.2,
                    "power_factor": 0.95
                }

            # 1. 主要风险评估
            primary_risks = {}

            # 洪水风险
            flood_risk = self.risk_engine.calculate_flood_risk(
                current_water_level, current_discharge,
                historical_max_level, historical_max_discharge,
                dam_height, population_density
            )
            primary_risks[RiskType.FLOOD] = flood_risk["risk_score"]

            # 结构风险
            structural_risk = self.risk_engine.calculate_structural_risk(
                current_water_level, structure_age, design_capacity=dam_height, maintenance_score=maintenance_score
            )
            primary_risks[RiskType.STRUCTURAL] = structural_risk["probability"] * (structural_risk["impact"] / 10.0)

            # 运行风险
            operational_risk = self.risk_engine.calculate_operational_risk(operational_data)
            primary_risks[RiskType.OPERATIONAL] = operational_risk["probability"] * (operational_risk["impact"] / 10.0)

            # 2. 脆弱性评估
            physical_vulnerability = self.vulnerability_engine.assess_physical_vulnerability(
                structure_age, design_standard, maintenance_score, inspection_score
            )

            operational_vulnerability = self.vulnerability_engine.assess_operational_vulnerability(
                redundancy_level=0.8, automation_level=0.7, training_level=0.85
            )

            organizational_vulnerability = self.vulnerability_engine.assess_organizational_vulnerability(
                preparedness_score=75.0, response_time=30.0, communication_score=80.0
            )

            social_vulnerability = 0.3  # 简化评估
            economic_vulnerability = 0.2  # 简化评估

            vulnerability_assessment = VulnerabilityAssessment(
                physical_vulnerability=physical_vulnerability,
                operational_vulnerability=operational_vulnerability,
                organizational_vulnerability=organizational_vulnerability,
                social_vulnerability=social_vulnerability,
                economic_vulnerability=economic_vulnerability
            )

            overall_vulnerability = np.mean([
                physical_vulnerability,
                operational_vulnerability,
                organizational_vulnerability,
                social_vulnerability,
                economic_vulnerability
            ])

            # 3. 暴露度评估
            population_exposure = self.exposure_engine.assess_population_exposure(
                population_density, proximity_distance=5.0
            )

            asset_exposure = self.exposure_engine.assess_asset_exposure(
                asset_value=1e9, criticality_score=8.0
            )

            infrastructure_exposure = self.exposure_engine.assess_infrastructure_exposure(
                infrastructure_density=15.0, interdependency_score=7.0
            )

            environmental_exposure = 0.6  # 简化评估

            exposure_assessment = ExposureAssessment(
                population_exposure=population_exposure,
                asset_exposure=asset_exposure,
                infrastructure_exposure=infrastructure_exposure,
                environmental_exposure=environmental_exposure
            )

            overall_exposure = np.mean([
                population_exposure,
                asset_exposure,
                infrastructure_exposure,
                environmental_exposure
            ])

            # 4. 综合风险评分
            comprehensive_risk_scores = {}

            for risk_type, primary_score in primary_risks.items():
                comprehensive_risk_scores[risk_type] = self.risk_engine.calculate_risk_score(
                    probability=primary_score,
                    impact=8.0,  # 中等影响
                    vulnerability=overall_vulnerability,
                    exposure=overall_exposure
                )

            # 5. 风险传播分析
            propagated_risks = self.propagation_analyzer.analyze_risk_propagation(primary_risks)

            # 6. 级联风险
            cascading_risk = self.propagation_analyzer.calculate_cascading_risk(propagated_risks)

            # 7. 总体风险等级
            total_risk_score = np.mean(list(comprehensive_risk_scores.values()))
            overall_risk_level = self.risk_engine.assess_risk_level(total_risk_score)

            # 8. 生成建议
            recommendations = self._generate_risk_recommendations(
                overall_risk_level, primary_risks, vulnerability_assessment
            )

            return {
                "status": "success",
                "risk_assessment": {
                    "current_conditions": {
                        "water_level": current_water_level,
                        "discharge": current_discharge,
                        "structure_age": structure_age,
                        "maintenance_score": maintenance_score
                    },
                    "primary_risks": {
                        risk_type.value: {
                            "score": float(score),
                            "level": self.risk_engine.assess_risk_level(score).value
                        }
                        for risk_type, score in primary_risks.items()
                    },
                    "comprehensive_risk_scores": {
                        risk_type.value: float(score)
                        for risk_type, score in comprehensive_risk_scores.items()
                    },
                    "propagated_risks": {
                        risk_type.value: float(score)
                        for risk_type, score in propagated_risks.items()
                    },
                    "vulnerability_assessment": {
                        "physical": float(vulnerability_assessment.physical_vulnerability),
                        "operational": float(vulnerability_assessment.operational_vulnerability),
                        "organizational": float(vulnerability_assessment.organizational_vulnerability),
                        "overall": float(overall_vulnerability)
                    },
                    "exposure_assessment": {
                        "population": float(exposure_assessment.population_exposure),
                        "asset": float(exposure_assessment.asset_exposure),
                        "infrastructure": float(exposure_assessment.infrastructure_exposure),
                        "overall": float(overall_exposure)
                    },
                    "overall_risk": {
                        "total_score": float(total_risk_score),
                        "risk_level": overall_risk_level.value,
                        "cascading_risk": float(cascading_risk)
                    }
                },
                "detailed_analysis": {
                    "flood_risk": flood_risk,
                    "structural_risk": structural_risk,
                    "operational_risk": operational_risk
                },
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"风险评估失败: {str(e)}",
                "recommendations": ["请检查输入参数是否合理", "确认历史数据准确性", "检查计算过程是否存在错误"]
            }

    def _generate_risk_recommendations(self, overall_risk_level: RiskLevel,
                                     primary_risks: Dict[RiskType, float],
                                     vulnerability_assessment: VulnerabilityAssessment) -> List[str]:
        """生成风险管控建议"""
        recommendations = []

        # 基于总体风险等级的建议
        if overall_risk_level == RiskLevel.VERY_HIGH:
            recommendations.append("紧急: 风险等级极高，立即启动一级应急响应")
            recommendations.append("紧急: 停止所有非必要作业，确保人员安全")
            recommendations.append("紧急: 通知上级主管部门和相关单位")

        elif overall_risk_level == RiskLevel.HIGH:
            recommendations.append("重要: 风险等级较高，启动二级应急响应")
            recommendations.append("重要: 加强监测和巡查，密切关注风险变化")
            recommendations.append("重要: 准备应急物资和设备")

        elif overall_risk_level == RiskLevel.MEDIUM:
            recommendations.append("注意: 风险等级中等，加强日常监控")
            recommendations.append("注意: 分析风险成因，制定管控措施")
            recommendations.append("注意: 定期检查关键设备和设施")

        # 基于具体风险类型的建议
        if primary_risks.get(RiskType.FLOOD, 0) > 0.6:
            recommendations.append("防洪建议: 加强洪水预警和监测")
            recommendations.append("防洪建议: 检查防洪设施和设备")

        if primary_risks.get(RiskType.STRUCTURAL, 0) > 0.6:
            recommendations.append("结构建议: 加强结构安全检查和评估")
            recommendations.append("结构建议: 必要时进行结构加固或维修")

        if primary_risks.get(RiskType.OPERATIONAL, 0) > 0.6:
            recommendations.append("运行建议: 优化运行参数和调度方案")
            recommendations.append("运行建议: 加强设备维护和保养")

        # 基于脆弱性的建议
        if vulnerability_assessment.physical_vulnerability > 0.6:
            recommendations.append("脆弱性建议: 加强结构维护和加固")

        if vulnerability_assessment.operational_vulnerability > 0.6:
            recommendations.append("脆弱性建议: 提高运行管理水平和应急响应能力")

        if vulnerability_assessment.organizational_vulnerability > 0.6:
            recommendations.append("脆弱性建议: 完善应急预案和组织管理")

        return recommendations

    async def analyze_risk_propagation(
        self,
        primary_risk_events: Dict[str, float],
        propagation_time_horizon: int = 24,  # hours
        cascade_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """
        风险传播分析 - MCP工具接口

        Args:
            primary_risk_events: 主要风险事件 {风险类型: 风险评分}
            propagation_time_horizon: 传播时间范围 (小时)
            cascade_threshold: 级联阈值

        Returns:
            风险传播分析结果
        """

        try:
            # 转换风险事件类型
            risk_events = {}
            for risk_type_str, score in primary_risk_events.items():
                try:
                    risk_type = RiskType(risk_type_str)
                    risk_events[risk_type] = score
                except ValueError:
                    continue

            if not risk_events:
                return {
                    "status": "error",
                    "message": "没有有效的风险事件类型"
                }

            # 风险传播分析
            propagated_risks = self.propagation_analyzer.analyze_risk_propagation(risk_events)

            # 级联风险分析
            cascading_risk = self.propagation_analyzer.calculate_cascading_risk(propagated_risks)

            # 传播路径分析
            propagation_paths = self._analyze_propagation_paths(risk_events, propagated_risks)

            # 时间演化分析
            temporal_evolution = self._simulate_temporal_evolution(
                risk_events, propagated_risks, propagation_time_horizon
            )

            # 关键节点识别
            critical_nodes = self._identify_critical_nodes(propagated_risks, cascade_threshold)

            # 生成传播管控建议
            propagation_recommendations = self._generate_propagation_recommendations(
                cascading_risk, critical_nodes
            )

            return {
                "status": "success",
                "propagation_analysis": {
                    "primary_risks": {
                        risk_type.value: float(score) for risk_type, score in risk_events.items()
                    },
                    "propagated_risks": {
                        risk_type.value: float(score) for risk_type, score in propagated_risks.items()
                    },
                    "cascading_risk": float(cascading_risk),
                    "propagation_paths": propagation_paths,
                    "temporal_evolution": temporal_evolution,
                    "critical_nodes": critical_nodes
                },
                "risk_evolution": {
                    "initial_risk_level": max(risk_events.values()),
                    "final_risk_level": max(propagated_risks.values()),
                    "risk_amplification": max(propagated_risks.values()) - max(risk_events.values()),
                    "cascade_potential": cascading_risk > cascade_threshold
                },
                "recommendations": propagation_recommendations
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"风险传播分析失败: {str(e)}",
                "recommendations": ["请检查输入参数格式", "确认风险评分在合理范围内", "检查计算过程是否存在错误"]
            }

    def _analyze_propagation_paths(self, primary_risks: Dict[RiskType, float],
                                 propagated_risks: Dict[RiskType, float]) -> List[Dict[str, Any]]:
        """分析风险传播路径"""
        paths = []

        for from_risk, from_score in primary_risks.items():
            for to_risk, to_score in propagated_risks.items():
                if from_risk != to_risk and to_risk not in primary_risks:
                    propagation_strength = to_score
                    if propagation_strength > 0.1:  # 传播强度阈值
                        paths.append({
                            "from": from_risk.value,
                            "to": to_risk.value,
                            "propagation_strength": float(propagation_strength),
                            "impact_level": "high" if propagation_strength > 0.5 else "medium"
                        })

        return paths

    def _simulate_temporal_evolution(self, primary_risks: Dict[RiskType, float],
                                   propagated_risks: Dict[RiskType, float],
                                   time_horizon: int) -> List[Dict[str, Any]]:
        """模拟风险时间演化"""
        evolution = []

        for hour in range(time_horizon + 1):
            # 简化的风险演化模型
            time_factor = math.exp(-hour / 24.0)  # 24小时衰减

            current_risks = {}
            for risk_type, initial_score in propagated_risks.items():
                current_score = initial_score * time_factor
                current_risks[risk_type.value] = current_score

            evolution.append({
                "hour": hour,
                "risks": current_risks,
                "total_risk": sum(current_risks.values()),
                "decay_factor": time_factor
            })

        return evolution

    def _identify_critical_nodes(self, propagated_risks: Dict[RiskType, float],
                               threshold: float) -> List[Dict[str, Any]]:
        """识别关键节点"""
        critical_nodes = []

        for risk_type, score in propagated_risks.items():
            if score > threshold:
                critical_nodes.append({
                    "risk_type": risk_type.value,
                    "risk_score": float(score),
                    "criticality_level": "high" if score > threshold * 1.5 else "medium",
                    "intervention_priority": "immediate" if score > threshold * 1.5 else "urgent"
                })

        return sorted(critical_nodes, key=lambda x: x["risk_score"], reverse=True)

    def _generate_propagation_recommendations(self, cascading_risk: float,
                                            critical_nodes: List[Dict[str, Any]]) -> List[str]:
        """生成风险传播管控建议"""
        recommendations = []

        if cascading_risk > 0.5:
            recommendations.append("紧急: 级联风险较高，需要立即采取阻断措施")
            recommendations.append("紧急: 加强关键节点的监控和保护")

        elif cascading_risk > 0.3:
            recommendations.append("重要: 存在级联风险，需要重点关注")
            recommendations.append("重要: 制定风险传播阻断预案")

        # 针对关键节点的建议
        high_priority_nodes = [node for node in critical_nodes if node["criticality_level"] == "high"]
        if high_priority_nodes:
            recommendations.append(f"关键节点: {len(high_priority_nodes)} 个高风险节点需要立即干预")

        # 传播阻断建议
        recommendations.append("传播管控: 建立风险传播监测机制")
        recommendations.append("传播管控: 制定分级响应策略")
        recommendations.append("传播管控: 加强部门间协调配合")

        return recommendations