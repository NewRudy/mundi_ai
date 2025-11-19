"""
异常检测模型MCP服务器
实现多维度异常检测和预警
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.covariance import EllipticEnvelope
import warnings
warnings.filterwarnings('ignore')

class AnomalyType(Enum):
    """异常类型"""
    STATISTICAL = "statistical"  # 统计异常
    TEMPORAL = "temporal"  # 时间序列异常
    MULTIVARIATE = "multivariate"  # 多变量异常
    SPATIAL = "spatial"  # 空间异常
    CONTEXTUAL = "contextual"  # 上下文异常

class AnomalySeverity(Enum):
    """异常严重程度"""
    LOW = 1  # 轻微异常
    MEDIUM = 2  # 中等异常
    HIGH = 3  # 严重异常
    CRITICAL = 4  # 极严重异常

@dataclass
class TimeSeriesData:
    """时间序列数据"""
    timestamps: List[datetime]
    values: np.ndarray
    labels: Optional[List[str]] = None

@dataclass
class AnomalyDetectionResult:
    """异常检测结果"""
    is_anomaly: bool
    anomaly_score: float
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    confidence: float
    affected_indices: List[int]
    description: str
    recommendations: List[str]

class StatisticalAnomalyDetector:
    """统计异常检测器"""

    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        self.contamination = contamination
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100
        )
        self.elliptic_envelope = EllipticEnvelope(
            contamination=contamination,
            random_state=random_state
        )
        self.scaler = StandardScaler()
        self.fitted = False

    def fit(self, data: np.ndarray) -> None:
        """训练统计模型"""
        if data.ndim == 1:
            data = data.reshape(-1, 1)

        # 标准化数据
        scaled_data = self.scaler.fit_transform(data)

        # 训练隔离森林
        self.isolation_forest.fit(scaled_data)

        # 训练椭圆包络 (适用于高斯分布数据)
        try:
            self.elliptic_envelope.fit(scaled_data)
        except:
            pass  # 椭圆包络可能不适用于某些数据分布

        self.fitted = True

    def detect_anomalies(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """检测统计异常"""
        if not self.fitted:
            raise ValueError("模型需要先训练")

        if data.ndim == 1:
            data = data.reshape(-1, 1)

        # 标准化数据
        scaled_data = self.scaler.transform(data)

        # 隔离森林预测
        iso_predictions = self.isolation_forest.predict(scaled_data)
        iso_scores = self.isolation_forest.decision_function(scaled_data)

        # 椭圆包络预测
        try:
            ell_predictions = self.elliptic_envelope.predict(scaled_data)
            ell_scores = self.elliptic_envelope.decision_function(scaled_data)
        except:
            ell_predictions = np.ones(len(data))
            ell_scores = np.zeros(len(data))

        # 综合两种方法的结果
        combined_predictions = np.where(
            (iso_predictions == -1) | (ell_predictions == -1),
            -1, 1
        )

        # 异常分数 (取两种方法的最大值)
        combined_scores = np.maximum(
            (iso_scores - iso_scores.mean()) / (iso_scores.std() + 1e-8),
            (ell_scores - ell_scores.mean()) / (ell_scores.std() + 1e-8)
        )

        return combined_predictions, combined_scores, iso_scores

class TimeSeriesAnomalyDetector:
    """时间序列异常检测器"""

    def __init__(self, window_size: int = 24, threshold_factor: float = 2.0):
        self.window_size = window_size
        self.threshold_factor = threshold_factor

    def detect_trend_anomalies(self, data: np.ndarray) -> np.ndarray:
        """检测趋势异常"""
        anomalies = np.zeros(len(data), dtype=bool)

        for i in range(self.window_size, len(data)):
            window = data[i-self.window_size:i]
            current_value = data[i]

            # 计算窗口统计量
            mean = np.mean(window)
            std = np.std(window)

            if std > 0:
                z_score = abs(current_value - mean) / std
                anomalies[i] = z_score > self.threshold_factor

        return anomalies

    def detect_seasonal_anomalies(self, data: np.ndarray, seasonal_period: int = 24) -> np.ndarray:
        """检测季节性异常"""
        anomalies = np.zeros(len(data), dtype=bool)

        if len(data) < seasonal_period * 2:
            return anomalies

        # 计算季节性基线
        seasonal_baseline = np.zeros(seasonal_period)
        seasonal_std = np.zeros(seasonal_period)

        for t in range(seasonal_period):
            seasonal_values = []
            for i in range(t, len(data), seasonal_period):
                seasonal_values.append(data[i])
            if len(seasonal_values) > 1:
                seasonal_baseline[t] = np.mean(seasonal_values)
                seasonal_std[t] = np.std(seasonal_values)

        # 检测异常
        for i in range(len(data)):
            t = i % seasonal_period
            if seasonal_std[t] > 0:
                z_score = abs(data[i] - seasonal_baseline[t]) / seasonal_std[t]
                anomalies[i] = z_score > self.threshold_factor

        return anomalies

    def detect_change_point_anomalies(self, data: np.ndarray) -> np.ndarray:
        """检测变点异常"""
        anomalies = np.zeros(len(data), dtype=bool)

        for i in range(self.window_size, len(data) - self.window_size):
            before_window = data[i-self.window_size:i]
            after_window = data[i:i+self.window_size]

            # 使用统计检验检测变点
            before_mean = np.mean(before_window)
            after_mean = np.mean(after_window)

            # 简单的均值变化检测
            change_magnitude = abs(after_mean - before_mean)
            baseline_std = np.std(np.concatenate([before_window, after_window]))

            if baseline_std > 0:
                change_score = change_magnitude / baseline_std
                anomalies[i] = change_score > self.threshold_factor

        return anomalies

class MultivariateAnomalyDetector:
    """多变量异常检测器"""

    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.isolation_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self.fitted = False

    def fit(self, data: np.ndarray) -> None:
        """训练多变量模型"""
        if data.ndim != 2:
            raise ValueError("多变量检测需要2维数据")

        # 标准化数据
        scaled_data = self.scaler.fit_transform(data)

        # 训练隔离森林
        self.isolation_forest.fit(scaled_data)
        self.fitted = True

    def detect_anomalies(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """检测多变量异常"""
        if not self.fitted:
            raise ValueError("模型需要先训练")

        if data.ndim != 2:
            raise ValueError("多变量检测需要2维数据")

        # 标准化数据
        scaled_data = self.scaler.transform(data)

        # 预测异常
        predictions = self.isolation_forest.predict(scaled_data)
        scores = self.isolation_forest.decision_function(scaled_data)

        return predictions, scores

    def identify_anomalous_features(self, data: np.ndarray, predictions: np.ndarray) -> List[List[int]]:
        """识别导致异常的特征"""
        anomalous_features = []

        for i, (row, pred) in enumerate(zip(data, predictions)):
            if pred == -1:  # 异常点
                # 计算每个特征对异常性的贡献 (简化方法)
                feature_scores = []
                for j in range(row.shape[0]):
                    # 计算该特征相对于均值的偏离程度
                    feature_mean = np.mean(data[:, j])
                    feature_std = np.std(data[:, j])
                    if feature_std > 0:
                        deviation = abs(row[j] - feature_mean) / feature_std
                        feature_scores.append(deviation)
                    else:
                        feature_scores.append(0)

                # 选择偏离最大的特征
                top_features = np.argsort(feature_scores)[-3:][::-1]
                anomalous_features.append(top_features.tolist())
            else:
                anomalous_features.append([])

        return anomalous_features

class ContextualAnomalyDetector:
    """上下文异常检测器"""

    def __init__(self, context_window: int = 24):
        self.context_window = context_window

    def detect_contextual_anomalies(self, data: np.ndarray, contexts: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """检测上下文相关异常"""
        results = {}

        for context_name, context_data in contexts.items():
            if len(context_data) != len(data):
                continue

            anomalies = np.zeros(len(data), dtype=bool)

            for i in range(self.context_window, len(data)):
                # 获取当前上下文
                current_context = context_data[i]

                # 获取相似上下文的历史数据
                context_window = context_data[max(0, i-self.context_window):i]
                data_window = data[max(0, i-self.context_window):i]

                # 找到相似上下文的数据点
                similar_indices = np.where(np.abs(context_window - current_context) < 0.1)[0]

                if len(similar_indices) > 5:  # 需要足够的相似样本
                    similar_data = data_window[similar_indices]
                    current_value = data[i]

                    # 计算相似上下文下的统计量
                    context_mean = np.mean(similar_data)
                    context_std = np.std(similar_data)

                    if context_std > 0:
                        context_z_score = abs(current_value - context_mean) / context_std
                        anomalies[i] = context_z_score > 2.0  # 阈值

            results[context_name] = anomalies

        return results

class AnomalyDetectionMCPServer:
    """异常检测模型MCP服务器"""

    def __init__(self):
        self.statistical_detector = StatisticalAnomalyDetector()
        self.time_series_detector = TimeSeriesAnomalyDetector()
        self.multivariate_detector = MultivariateAnomalyDetector()
        self.contextual_detector = ContextualAnomalyDetector()

    async def detect_hydrological_anomalies(
        self,
        water_level_data: List[float],
        discharge_data: List[float],
        temperature_data: Optional[List[float]] = None,
        timestamps: Optional[List[str]] = None,
        seasonal_period: int = 24,
        sensitivity: str = "medium"
    ) -> Dict[str, Any]:
        """
        检测水文异常 - MCP工具接口

        Args:
            water_level_data: 水位数据
            discharge_data: 流量数据
            temperature_data: 水温数据 (可选)
            timestamps: 时间戳 (可选)
            seasonal_period: 季节周期 (小时)
            sensitivity: 检测敏感度 (low/medium/high)

        Returns:
            异常检测结果
        """

        try:
            # 参数验证
            if len(water_level_data) != len(discharge_data):
                return {
                    "status": "error",
                    "message": "水位数据和流量数据长度不一致"
                }

            if len(water_level_data) < 24:
                return {
                    "status": "error",
                    "message": "数据长度不足，至少需要24个数据点"
                }

            # 转换敏感度为阈值
            sensitivity_thresholds = {
                "low": 3.0,
                "medium": 2.0,
                "high": 1.5
            }
            threshold = sensitivity_thresholds.get(sensitivity, 2.0)

            # 准备数据
            water_level_array = np.array(water_level_data)
            discharge_array = np.array(discharge_data)

            # 1. 统计异常检测
            water_level_anomalies, wl_scores, _ = self._detect_statistical_anomalies(
                water_level_array, threshold
            )
            discharge_anomalies, d_scores, _ = self._detect_statistical_anomalies(
                discharge_array, threshold
            )

            # 2. 时间序列异常检测
            ts_water_level_anomalies = self._detect_time_series_anomalies(
                water_level_array, seasonal_period, threshold
            )
            ts_discharge_anomalies = self._detect_time_series_anomalies(
                discharge_array, seasonal_period, threshold
            )

            # 3. 多变量异常检测
            multivariate_anomalies, multivariate_scores = self._detect_multivariate_anomalies(
                np.column_stack([water_level_array, discharge_array]), threshold
            )

            # 4. 综合异常评分
            combined_anomalies = self._combine_anomaly_results(
                water_level_anomalies, discharge_anomalies,
                ts_water_level_anomalies, ts_discharge_anomalies,
                multivariate_anomalies
            )

            # 5. 异常严重程度评估
            severity_assessment = self._assess_anomaly_severity(
                combined_anomalies, wl_scores, d_scores, multivariate_scores
            )

            # 6. 生成建议
            recommendations = self._generate_anomaly_recommendations(
                severity_assessment, water_level_array, discharge_array
            )

            return {
                "status": "success",
                "detection_summary": {
                    "total_data_points": len(water_level_data),
                    "anomaly_detection_rate": np.mean(combined_anomalies),
                    "water_level_anomalies": int(np.sum(water_level_anomalies)),
                    "discharge_anomalies": int(np.sum(discharge_anomalies)),
                    "multivariate_anomalies": int(np.sum(multivariate_anomalies))
                },
                "anomaly_details": {
                    "combined_anomalies": combined_anomalies.tolist(),
                    "water_level_anomalies": water_level_anomalies.tolist(),
                    "discharge_anomalies": discharge_anomalies.tolist(),
                    "time_series_anomalies": {
                        "water_level": ts_water_level_anomalies.tolist(),
                        "discharge": ts_discharge_anomalies.tolist()
                    },
                    "multivariate_anomalies": multivariate_anomalies.tolist()
                },
                "anomaly_scores": {
                    "water_level_scores": wl_scores.tolist(),
                    "discharge_scores": d_scores.tolist(),
                    "multivariate_scores": multivariate_scores.tolist()
                },
                "severity_assessment": severity_assessment,
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"异常检测失败: {str(e)}",
                "recommendations": ["请检查输入数据格式", "确认数据质量符合要求", "尝试调整检测参数"]
            }

    def _detect_statistical_anomalies(self, data: np.ndarray, threshold: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """检测统计异常"""
        self.statistical_detector.fit(data)
        predictions, scores, raw_scores = self.statistical_detector.detect_anomalies(data)

        # 应用阈值调整
        adjusted_predictions = np.where(scores > threshold, -1, 1)

        return adjusted_predictions == -1, scores, raw_scores

    def _detect_time_series_anomalies(self, data: np.ndarray, seasonal_period: int, threshold: float) -> np.ndarray:
        """检测时间序列异常"""
        # 趋势异常
        trend_anomalies = self.time_series_detector.detect_trend_anomalies(data)

        # 季节性异常
        seasonal_anomalies = self.time_series_detector.detect_seasonal_anomalies(data, seasonal_period)

        # 变点异常
        change_point_anomalies = self.time_series_detector.detect_change_point_anomalies(data)

        # 综合时间序列异常
        combined_ts_anomalies = trend_anomalies | seasonal_anomalies | change_point_anomalies

        return combined_ts_anomalies

    def _detect_multivariate_anomalies(self, data: np.ndarray, threshold: float) -> Tuple[np.ndarray, np.ndarray]:
        """检测多变量异常"""
        self.multivariate_detector.fit(data)
        predictions, scores = self.multivariate_detector.detect_anomalies(data)

        # 应用阈值调整
        adjusted_predictions = np.where(scores > threshold, -1, 1)

        return adjusted_predictions == -1, scores

    def _combine_anomaly_results(self, *anomaly_arrays) -> np.ndarray:
        """综合多种异常检测结果"""
        # 使用投票机制综合结果
        votes = np.zeros(len(anomaly_arrays[0]))

        for anomalies in anomaly_arrays:
            votes += anomalies.astype(int)

        # 多数投票决定最终异常
        threshold = len(anomaly_arrays) / 2
        combined_anomalies = votes >= threshold

        return combined_anomalies

    def _assess_anomaly_severity(self, combined_anomalies: np.ndarray,
                                wl_scores: np.ndarray, d_scores: np.ndarray,
                                multivariate_scores: np.ndarray) -> Dict[str, Any]:
        """评估异常严重程度"""
        anomaly_indices = np.where(combined_anomalies)[0]

        if len(anomaly_indices) == 0:
            return {
                "overall_severity": "normal",
                "severity_level": 0,
                "anomaly_percentage": 0.0,
                "max_score": 0.0,
                "critical_periods": []
            }

        # 计算异常严重程度指标
        anomaly_percentage = len(anomaly_indices) / len(combined_anomalies)
        max_score = max(np.max(wl_scores) if len(wl_scores) > 0 else 0,
                       np.max(d_scores) if len(d_scores) > 0 else 0,
                       np.max(multivariate_scores) if len(multivariate_scores) > 0 else 0)

        # 确定严重程度等级
        if anomaly_percentage > 0.3 or max_score > 3.0:
            overall_severity = "critical"
            severity_level = 4
        elif anomaly_percentage > 0.15 or max_score > 2.0:
            overall_severity = "high"
            severity_level = 3
        elif anomaly_percentage > 0.05 or max_score > 1.5:
            overall_severity = "medium"
            severity_level = 2
        else:
            overall_severity = "low"
            severity_level = 1

        # 识别关键异常时段
        critical_periods = self._identify_critical_periods(combined_anomalies, max_score)

        return {
            "overall_severity": overall_severity,
            "severity_level": severity_level,
            "anomaly_percentage": anomaly_percentage,
            "max_score": float(max_score),
            "critical_periods": critical_periods
        }

    def _identify_critical_periods(self, anomalies: np.ndarray, max_score: float) -> List[Dict[str, Any]]:
        """识别关键异常时段"""
        critical_periods = []

        # 找到连续的异常段
        anomaly_changes = np.diff(np.concatenate([[0], anomalies.astype(int), [0]]))
        start_indices = np.where(anomaly_changes == 1)[0]
        end_indices = np.where(anomaly_changes == -1)[0] - 1

        for start, end in zip(start_indices, end_indices):
            duration = end - start + 1
            severity = "high" if duration > 6 or max_score > 2.5 else "medium"

            critical_periods.append({
                "start_index": int(start),
                "end_index": int(end),
                "duration": int(duration),
                "severity": severity
            })

        return critical_periods

    def _generate_anomaly_recommendations(self, severity_assessment: Dict[str, Any],
                                        water_level_data: np.ndarray, discharge_data: np.ndarray) -> List[str]:
        """生成异常处理建议"""
        recommendations = []
        severity_level = severity_assessment.get("severity_level", 0)

        if severity_level >= 4:  # Critical
            recommendations.append("紧急: 发现严重异常，立即启动应急响应")
            recommendations.append("紧急: 通知相关技术人员和管理部门")
            recommendations.append("紧急: 暂停相关设备运行，确保安全")

        elif severity_level == 3:  # High
            recommendations.append("重要: 发现显著异常，需要密切监控")
            recommendations.append("重要: 加强巡检频次，检查设备状态")
            recommendations.append("重要: 准备应急预案，随时响应")

        elif severity_level == 2:  # Medium
            recommendations.append("注意: 发现中等异常，需要关注变化趋势")
            recommendations.append("注意: 增加监测频率，记录异常情况")
            recommendations.append("注意: 分析异常原因，制定处理方案")

        elif severity_level == 1:  # Low
            recommendations.append("观察: 发现轻微异常，继续监测")
            recommendations.append("观察: 分析可能原因，预防恶化")

        # 基于数据特征的建议
        if np.std(water_level_data) > 2.0:
            recommendations.append("建议: 水位波动较大，检查上游来水情况")

        if np.std(discharge_data) > 1000:
            recommendations.append("建议: 流量变化剧烈，检查泄洪设施状态")

        return recommendations

    async def detect_real_time_anomalies(
        self,
        sensor_readings: Dict[str, List[float]],
        time_window_minutes: int = 60,
        update_frequency: int = 5
    ) -> Dict[str, Any]:
        """
        实时异常检测 - MCP工具接口

        Args:
            sensor_readings: 传感器读数字典 {传感器名称: 读数列表}
            time_window_minutes: 时间窗口 (分钟)
            update_frequency: 更新频率 (分钟)

        Returns:
            实时异常检测结果
        """

        try:
            # 验证输入数据
            if not sensor_readings:
                return {
                    "status": "error",
                    "message": "没有提供传感器数据"
                }

            # 检查数据一致性
            data_lengths = [len(readings) for readings in sensor_readings.values()]
            if len(set(data_lengths)) > 1:
                return {
                    "status": "error",
                    "message": "传感器数据长度不一致"
                }

            if data_lengths[0] < 12:  # 至少需要12个数据点 (1小时，5分钟间隔)
                return {
                    "status": "error",
                    "message": "数据点数量不足，无法有效检测异常"
                }

            # 准备多变量数据
            sensor_names = list(sensor_readings.keys())
            data_matrix = np.column_stack([sensor_readings[name] for name in sensor_names])

            # 实时异常检测
            real_time_anomalies, anomaly_scores = self.multivariate_detector.detect_anomalies(data_matrix)

            # 计算趋势异常
            trend_anomalies = {}
            for name, readings in sensor_readings.items():
                readings_array = np.array(readings)
                trend_anomaly = self.time_series_detector.detect_trend_anomalies(readings_array)
                trend_anomalies[name] = trend_anomaly.tolist()

            # 综合评估
            overall_anomaly_rate = np.mean(real_time_anomalies)
            max_score = np.max(anomaly_scores) if len(anomaly_scores) > 0 else 0

            # 确定严重程度
            if overall_anomaly_rate > 0.3 or max_score > 3.0:
                severity = "critical"
                alert_level = 4
            elif overall_anomaly_rate > 0.15 or max_score > 2.0:
                severity = "high"
                alert_level = 3
            elif overall_anomaly_rate > 0.05 or max_score > 1.5:
                severity = "medium"
                alert_level = 2
            else:
                severity = "low"
                alert_level = 1

            # 识别异常传感器
            anomalous_sensors = []
            for i, name in enumerate(sensor_names):
                sensor_anomalies = real_time_anomalies[:, i] if data_matrix.ndim > 1 else real_time_anomalies
                anomaly_rate = np.mean(sensor_anomalies)
                if anomaly_rate > 0.1:  # 10%以上异常
                    anomalous_sensors.append({
                        "sensor_name": name,
                        "anomaly_rate": float(anomaly_rate),
                        "severity": "high" if anomaly_rate > 0.3 else "medium"
                    })

            return {
                "status": "success",
                "detection_summary": {
                    "total_sensors": len(sensor_names),
                    "monitoring_duration_minutes": time_window_minutes,
                    "update_frequency_minutes": update_frequency,
                    "overall_anomaly_rate": float(overall_anomaly_rate),
                    "max_anomaly_score": float(max_score),
                    "severity_level": severity,
                    "alert_level": alert_level
                },
                "anomaly_details": {
                    "real_time_anomalies": real_time_anomalies.tolist(),
                    "anomaly_scores": anomaly_scores.tolist(),
                    "trend_anomalies": trend_anomalies,
                    "anomalous_sensors": anomalous_sensors
                },
                "timestamp": datetime.now().isoformat(),
                "recommendations": self._generate_real_time_recommendations(alert_level, anomalous_sensors)
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"实时异常检测失败: {str(e)}",
                "recommendations": ["请检查传感器数据质量", "确认数据格式正确", "检查网络连接状态"]
            }

    def _generate_real_time_recommendations(self, alert_level: int, anomalous_sensors: List[Dict[str, Any]]) -> List[str]:
        """生成实时异常处理建议"""
        recommendations = []

        if alert_level >= 4:  # Critical
            recommendations.append("紧急: 检测到严重异常，立即检查现场设备")
            recommendations.append("紧急: 通知运维人员和管理人员")
            recommendations.append("紧急: 考虑暂停相关操作，确保安全")

        elif alert_level == 3:  # High
            recommendations.append("重要: 检测到显著异常，需要立即关注")
            recommendations.append("重要: 加强监控，准备应急措施")

        elif alert_level == 2:  # Medium
            recommendations.append("注意: 检测到异常，需要关注")
            recommendations.append("注意: 检查相关设备和参数")

        # 针对异常传感器的建议
        for sensor in anomalous_sensors:
            if sensor["severity"] == "high":
                recommendations.append(f"紧急: {sensor['sensor_name']} 异常率 {sensor['anomaly_rate']:.1%}，需要立即检修")
            else:
                recommendations.append(f"注意: {sensor['sensor_name']} 异常率 {sensor['anomaly_rate']:.1%}，建议检查校准")

        return recommendations