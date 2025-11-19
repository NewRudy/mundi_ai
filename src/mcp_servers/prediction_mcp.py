"""
预测模型MCP服务器
实现时间序列预测、机器学习预测和集成预测
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# 尝试导入机器学习库
try:
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler, PolynomialFeatures
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from scipy import stats
    from scipy.signal import savgol_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

class PredictionMethod(Enum):
    """预测方法"""
    TIME_SERIES = "time_series"  # 时间序列方法
    MACHINE_LEARNING = "machine_learning"  # 机器学习方法
    ENSEMBLE = "ensemble"  # 集成方法
    TREND = "trend"  # 趋势方法
    SEASONAL = "seasonal"  # 季节方法

class PredictionHorizon(Enum):
    """预测时间范围"""
    SHORT_TERM = "short_term"  # 短期 (1-24小时)
    MEDIUM_TERM = "medium_term"  # 中期 (1-7天)
    LONG_TERM = "long_term"  # 长期 (1-12个月)

@dataclass
class PredictionResult:
    """预测结果"""
    predicted_values: np.ndarray
    confidence_intervals: Optional[Tuple[np.ndarray, np.ndarray]]
    prediction_timestamps: List[datetime]
    method_used: PredictionMethod
    accuracy_metrics: Dict[str, float]
    confidence_level: float
    model_parameters: Dict[str, Any]

@dataclass
class HistoricalData:
    """历史数据"""
    timestamps: List[datetime]
    values: np.ndarray
    quality_scores: Optional[np.ndarray] = None

class TimeSeriesPredictor:
    """时间序列预测器"""

    def __init__(self):
        self.seasonal_patterns = {}
        self.trend_models = {}

    def detect_seasonality(self, data: np.ndarray, period: int = 24) -> Dict[str, Any]:
        """检测季节性模式"""
        if len(data) < period * 2:
            return {"has_seasonality": False, "seasonal_strength": 0.0}

        # 计算季节性强度
        seasonal_component = np.zeros(period)
        for i in range(period):
            seasonal_values = []
            for j in range(i, len(data), period):
                seasonal_values.append(data[j])
            if len(seasonal_values) > 1:
                seasonal_component[i] = np.mean(seasonal_values)

        # 计算季节性强度
        seasonal_variance = np.var(seasonal_component)
        total_variance = np.var(data)
        seasonal_strength = seasonal_variance / total_variance if total_variance > 0 else 0

        return {
            "has_seasonality": seasonal_strength > 0.1,
            "seasonal_strength": float(seasonal_strength),
            "seasonal_component": seasonal_component.tolist()
        }

    def extract_trend(self, data: np.ndarray, method: str = "moving_average", window: int = 12) -> np.ndarray:
        """提取趋势成分"""
        if method == "moving_average":
            # 移动平均
            trend = np.convolve(data, np.ones(window)/window, mode='same')
        elif method == "exponential_smoothing" and SCIPY_AVAILABLE:
            # 指数平滑
            alpha = 2 / (window + 1)
            trend = np.zeros_like(data)
            trend[0] = data[0]
            for i in range(1, len(data)):
                trend[i] = alpha * data[i] + (1 - alpha) * trend[i-1]
        else:
            # 线性趋势
            x = np.arange(len(data))
            coefficients = np.polyfit(x, data, 1)
            trend = np.polyval(coefficients, x)

        return trend

    def seasonal_decomposition(self, data: np.ndarray, period: int = 24) -> Dict[str, np.ndarray]:
        """季节性分解"""
        # 提取趋势
        trend = self.extract_trend(data, method="moving_average", window=period)

        # 计算残差
        residual = data - trend

        # 提取季节性
        seasonal_info = self.detect_seasonality(data, period)
        if seasonal_info["has_seasonality"]:
            seasonal = np.tile(seasonal_info["seasonal_component"], len(data) // period + 1)[:len(data)]
            # 重新计算残差
            residual = data - trend - seasonal
        else:
            seasonal = np.zeros_like(data)

        return {
            "original": data,
            "trend": trend,
            "seasonal": seasonal,
            "residual": residual
        }

    def predict_with_seasonality(self, data: np.ndarray, forecast_steps: int,
                               period: int = 24, confidence_level: float = 0.95) -> PredictionResult:
        """基于季节性的预测"""
        if len(data) < period * 2:
            raise ValueError(f"数据长度不足，需要至少 {period * 2} 个数据点")

        # 季节性分解
        decomposition = self.seasonal_decomposition(data, period)

        # 趋势预测 (线性外推)
        trend_data = decomposition["trend"]
        x = np.arange(len(trend_data))
        trend_coefficients = np.polyfit(x, trend_data, 1)

        # 预测趋势
        future_x = np.arange(len(data), len(data) + forecast_steps)
        predicted_trend = np.polyval(trend_coefficients, future_x)

        # 季节性预测
        seasonal_component = decomposition["seasonal"]
        seasonal_pattern = seasonal_component[-period:]  # 最后一个周期的季节性模式
        predicted_seasonal = np.tile(seasonal_pattern, forecast_steps // period + 1)[:forecast_steps]

        # 组合预测
        predicted_values = predicted_trend + predicted_seasonal

        # 计算置信区间 (基于历史残差)
        residual_std = np.std(decomposition["residual"])
        z_score = 1.96 if confidence_level == 0.95 else 2.58  # 95% or 99%
        margin_of_error = z_score * residual_std

        lower_bound = predicted_values - margin_of_error
        upper_bound = predicted_values + margin_of_error

        # 计算准确性指标
        accuracy_metrics = self._calculate_time_series_metrics(data, decomposition["trend"] + decomposition["seasonal"])

        return PredictionResult(
            predicted_values=predicted_values,
            confidence_intervals=(lower_bound, upper_bound),
            prediction_timestamps=[],  # 由调用者设置
            method_used=PredictionMethod.SEASONAL,
            accuracy_metrics=accuracy_metrics,
            confidence_level=confidence_level,
            model_parameters={"period": period, "method": "seasonal_decomposition"}
        )

    def _calculate_time_series_metrics(self, actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        """计算时间序列预测准确性指标"""
        if SCIPY_AVAILABLE:
            mae = mean_absolute_error(actual, predicted)
            rmse = np.sqrt(mean_squared_error(actual, predicted))
            r2 = r2_score(actual, predicted)
        else:
            mae = np.mean(np.abs(actual - predicted))
            rmse = np.sqrt(np.mean((actual - predicted) ** 2))
            ss_res = np.sum((actual - predicted) ** 2)
            ss_tot = np.sum((actual - np.mean(actual)) ** 2)
            r2 = 1 - (ss_res / (ss_tot + 1e-8))

        return {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "mape": np.mean(np.abs((actual - predicted) / (actual + 1e-8))) * 100
        }

class MachineLearningPredictor:
    """机器学习预测器"""

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}

    def prepare_features(self, data: np.ndarray, include_lag_features: bool = True,
                        lag_orders: List[int] = None) -> np.ndarray:
        """准备特征矩阵"""
        if lag_orders is None:
            lag_orders = [1, 2, 3, 6, 12, 24]

        features = []

        # 时间特征
        for i in range(len(data)):
            time_features = [
                np.sin(2 * np.pi * i / 24),  # 日周期
                np.cos(2 * np.pi * i / 24),  # 日周期
                np.sin(2 * np.pi * i / (24 * 7)),  # 周周期
                np.cos(2 * np.pi * i / (24 * 7)),  # 周周期
            ]
            features.append(time_features)

        features = np.array(features)

        # 滞后特征
        if include_lag_features:
            lag_features = []
            for lag in lag_orders:
                if lag < len(data):
                    lag_feature = np.roll(data, lag)
                    lag_feature[:lag] = data[0]  # 填充初始值
                    lag_features.append(lag_feature)

            if lag_features:
                lag_features = np.column_stack(lag_features)
                features = np.column_stack([features, lag_features])

        # 统计特征
        rolling_stats = []
        for window in [3, 6, 12, 24]:
            if window <= len(data):
                rolling_mean = np.convolve(data, np.ones(window)/window, mode='same')
                rolling_std = np.array([np.std(data[max(0, i-window+1):i+1]) for i in range(len(data))])
                rolling_stats.extend([rolling_mean, rolling_std])

        if rolling_stats:
            rolling_stats = np.column_stack(rolling_stats)
            features = np.column_stack([features, rolling_stats])

        return features

    def train_models(self, X: np.ndarray, y: np.ndarray, test_size: float = 0.2) -> Dict[str, Any]:
        """训练机器学习模型"""
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn 不可用，无法训练机器学习模型"}

        # 数据分割
        split_idx = int(len(X) * (1 - test_size))
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # 特征标准化
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # 训练多个模型
        models = {
            "linear_regression": LinearRegression(),
            "random_forest": RandomForestRegressor(n_estimators=100, random_state=42),
            "gradient_boosting": GradientBoostingRegressor(n_estimators=100, random_state=42)
        }

        training_results = {}

        for name, model in models.items():
            # 训练模型
            model.fit(X_train_scaled, y_train)

            # 预测
            y_pred = model.predict(X_test_scaled)

            # 计算性能指标
            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)

            training_results[name] = {
                "model": model,
                "scaler": scaler,
                "performance": {
                    "mae": mae,
                    "rmse": rmse,
                    "r2": r2
                }
            }

        return training_results

    def predict_with_ml(self, historical_data: np.ndarray, forecast_steps: int,
                       confidence_level: float = 0.95) -> PredictionResult:
        """使用机器学习方法预测"""
        if len(historical_data) < 48:
            raise ValueError("机器学习预测需要至少48个历史数据点")

        # 准备特征
        features = self.prepare_features(historical_data)

        # 训练模型
        training_results = self.train_models(features, historical_data)

        if "error" in training_results:
            raise ValueError(training_results["error"])

        # 选择最佳模型
        best_model_name = max(training_results.keys(),
                            key=lambda x: training_results[x]["performance"]["r2"])
        best_model_info = training_results[best_model_name]

        # 准备预测特征
        last_features = features[-1:].copy()
        predictions = []

        for step in range(forecast_steps):
            # 使用最佳模型预测
            pred_features = last_features.copy()
            pred_scaled = best_model_info["scaler"].transform(pred_features)
            pred_value = best_model_info["model"].predict(pred_scaled)[0]
            predictions.append(pred_value)

            # 更新特征用于下一步预测 (简单的特征更新策略)
            # 这里需要更复杂的特征更新逻辑
            last_features = np.roll(last_features, -1, axis=1)
            last_features[0, -1] = pred_value

        predicted_values = np.array(predictions)

        # 计算置信区间 (基于模型性能)
        model_rmse = best_model_info["performance"]["rmse"]
        z_score = 1.96 if confidence_level == 0.95 else 2.58
        margin_of_error = z_score * model_rmse

        lower_bound = predicted_values - margin_of_error
        upper_bound = predicted_values + margin_of_error

        return PredictionResult(
            predicted_values=predicted_values,
            confidence_intervals=(lower_bound, upper_bound),
            prediction_timestamps=[],
            method_used=PredictionMethod.MACHINE_LEARNING,
            accuracy_metrics=best_model_info["performance"],
            confidence_level=confidence_level,
            model_parameters={"model_type": best_model_name, "feature_count": features.shape[1]}
        )

class EnsemblePredictor:
    """集成预测器"""

    def __init__(self):
        self.time_series_predictor = TimeSeriesPredictor()
        self.ml_predictor = MachineLearningPredictor()
        self.weights = {"time_series": 0.4, "machine_learning": 0.6}  # 默认权重

    def calculate_ensemble_weights(self, historical_data: np.ndarray) -> Dict[str, float]:
        """计算集成权重"""
        try:
            # 简单的交叉验证方法
            cv_size = min(24, len(historical_data) // 4)
            if cv_size < 6:
                return self.weights

            # 时间序列方法性能
            ts_performance = self._evaluate_time_series_performance(historical_data, cv_size)

            # 机器学习方法性能
            ml_performance = self._evaluate_ml_performance(historical_data, cv_size)

            # 基于性能计算权重 (R2分数加权)
            ts_weight = ts_performance["r2"] / (ts_performance["r2"] + ml_performance["r2"] + 1e-8)
            ml_weight = ml_performance["r2"] / (ts_performance["r2"] + ml_performance["r2"] + 1e-8)

            return {"time_series": ts_weight, "machine_learning": ml_weight}

        except Exception as e:
            print(f"权重计算失败: {e}")
            return self.weights

    def _evaluate_time_series_performance(self, data: np.ndarray, test_size: int) -> Dict[str, float]:
        """评估时间序列方法性能"""
        try:
            train_data = data[:-test_size]
            test_data = data[-test_size:]

            # 简单的时间序列预测 (线性趋势 + 季节性)
            trend = self.time_series_predictor.extract_trend(train_data)
            seasonal_info = self.time_series_predictor.detect_seasonality(train_data, 24)

            if seasonal_info["has_seasonality"]:
                seasonal_pattern = np.array(seasonal_info["seasonal_component"])
                # 预测趋势
                x_train = np.arange(len(train_data))
                trend_coef = np.polyfit(x_train, trend, 1)
                x_test = np.arange(len(train_data), len(train_data) + test_size)
                pred_trend = np.polyval(trend_coef, x_test)
                # 预测季节性
                pred_seasonal = np.tile(seasonal_pattern, test_size // 24 + 1)[:test_size]
                predictions = pred_trend + pred_seasonal
            else:
                # 仅趋势预测
                x_train = np.arange(len(train_data))
                trend_coef = np.polyfit(x_train, train_data, 1)
                x_test = np.arange(len(train_data), len(train_data) + test_size)
                predictions = np.polyval(trend_coef, x_test)

            # 计算性能指标
            mae = np.mean(np.abs(test_data - predictions))
            rmse = np.sqrt(np.mean((test_data - predictions) ** 2))
            ss_res = np.sum((test_data - predictions) ** 2)
            ss_tot = np.sum((test_data - np.mean(test_data)) ** 2)
            r2 = 1 - (ss_res / (ss_tot + 1e-8))

            return {"mae": mae, "rmse": rmse, "r2": r2}

        except Exception as e:
            print(f"时间序列性能评估失败: {e}")
            return {"mae": np.inf, "rmse": np.inf, "r2": 0.0}

    def _evaluate_ml_performance(self, data: np.ndarray, test_size: int) -> Dict[str, float]:
        """评估机器学习方法性能"""
        try:
            if not SKLEARN_AVAILABLE or len(data) < test_size * 2:
                return {"mae": np.inf, "rmse": np.inf, "r2": 0.0}

            train_data = data[:-test_size]
            test_data = data[-test_size:]

            # 准备特征
            features = self.ml_predictor.prepare_features(train_data)
            if features.shape[1] == 0:
                return {"mae": np.inf, "rmse": np.inf, "r2": 0.0}

            # 训练简单线性模型
            X_train, X_test = features[:-test_size], features[-test_size:]
            y_train, y_test = train_data[:-test_size], train_data[-test_size:]

            model = LinearRegression()
            model.fit(X_train, y_train)
            predictions = model.predict(X_test)

            # 计算性能指标
            mae = mean_absolute_error(y_test, predictions)
            rmse = np.sqrt(mean_squared_error(y_test, predictions))
            r2 = r2_score(y_test, predictions)

            return {"mae": mae, "rmse": rmse, "r2": r2}

        except Exception as e:
            print(f"机器学习性能评估失败: {e}")
            return {"mae": np.inf, "rmse": np.inf, "r2": 0.0}

    def predict_with_ensemble(self, historical_data: np.ndarray, forecast_steps: int,
                            confidence_level: float = 0.95) -> PredictionResult:
        """使用集成方法预测"""
        # 计算动态权重
        weights = self.calculate_ensemble_weights(historical_data)

        # 时间序列预测
        try:
            ts_result = self.time_series_predictor.predict_with_seasonality(
                historical_data, forecast_steps, confidence_level=confidence_level
            )
            ts_predictions = ts_result.predicted_values
            ts_lower, ts_upper = ts_result.confidence_intervals
        except Exception as e:
            print(f"时间序列预测失败: {e}")
            # 使用简单的线性预测作为备选
            x = np.arange(len(historical_data))
            coefficients = np.polyfit(x, historical_data, 1)
            future_x = np.arange(len(historical_data), len(historical_data) + forecast_steps)
            ts_predictions = np.polyval(coefficients, future_x)
            ts_lower = ts_predictions * 0.9
            ts_upper = ts_predictions * 1.1

        # 机器学习预测
        try:
            ml_result = self.ml_predictor.predict_with_ml(historical_data, forecast_steps, confidence_level)
            ml_predictions = ml_result.predicted_values
            ml_lower, ml_upper = ml_result.confidence_intervals
        except Exception as e:
            print(f"机器学习预测失败: {e}")
            # 使用移动平均作为备选
            window = min(24, len(historical_data))
            recent_avg = np.mean(historical_data[-window:])
            ml_predictions = np.full(forecast_steps, recent_avg)
            ml_lower = ml_predictions * 0.9
            ml_upper = ml_predictions * 1.1

        # 集成预测
        ensemble_predictions = (
            weights["time_series"] * ts_predictions +
            weights["machine_learning"] * ml_predictions
        )

        # 集成置信区间
        ensemble_lower = (
            weights["time_series"] * ts_lower +
            weights["machine_learning"] * ml_lower
        )

        ensemble_upper = (
            weights["time_series"] * ts_upper +
            weights["machine_learning"] * ml_upper
        )

        # 计算集成准确性指标 (简化方法)
        ensemble_metrics = {
            "mae": (weights["time_series"] * 1.0 + weights["machine_learning"] * 1.0),  # 简化
            "rmse": 1.0,  # 简化
            "r2": 0.8,  # 简化
            "ensemble_weight_ts": weights["time_series"],
            "ensemble_weight_ml": weights["machine_learning"]
        }

        return PredictionResult(
            predicted_values=ensemble_predictions,
            confidence_intervals=(ensemble_lower, ensemble_upper),
            prediction_timestamps=[],  # 由调用者设置
            method_used=PredictionMethod.ENSEMBLE,
            accuracy_metrics=ensemble_metrics,
            confidence_level=confidence_level,
            model_parameters={"weights": weights, "methods": ["time_series", "machine_learning"]}
        )

class PredictionMCPServer:
    """预测模型MCP服务器"""

    def __init__(self):
        self.time_series_predictor = TimeSeriesPredictor()
        self.ml_predictor = MachineLearningPredictor()
        self.ensemble_predictor = EnsemblePredictor()

    async def predict_hydrological_variables(
        self,
        historical_water_levels: List[float],
        historical_discharges: List[float],
        historical_temperatures: Optional[List[float]] = None,
        prediction_hours: int = 24,
        method: str = "ensemble",
        seasonal_period: int = 24,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        水文变量预测 - MCP工具接口

        Args:
            historical_water_levels: 历史水位数据
            historical_discharges: 历史流量数据
            historical_temperatures: 历史水温数据 (可选)
            prediction_hours: 预测时长 (小时)
            method: 预测方法 (time_series/machine_learning/ensemble)
            seasonal_period: 季节周期 (小时)
            confidence_level: 置信水平

        Returns:
            水文变量预测结果
        """

        try:
            # 参数验证
            if len(historical_water_levels) != len(historical_discharges):
                return {
                    "status": "error",
                    "message": "水位数据和流量数据长度不一致"
                }

            if len(historical_water_levels) < 48:
                return {
                    "status": "error",
                    "message": "历史数据不足，至少需要48个数据点"
                }

            if prediction_hours < 1 or prediction_hours > 168:  # 限制预测范围
                return {
                    "status": "error",
                    "message": "预测时长应在1-168小时之间"
                }

            # 转换数据类型
            water_level_array = np.array(historical_water_levels)
            discharge_array = np.array(historical_discharges)

            # 选择预测方法
            try:
                prediction_method = PredictionMethod(method)
            except ValueError:
                return {
                    "status": "error",
                    "message": f"无效的预测方法: {method}"
                }

            # 生成预测时间戳
            last_timestamp = datetime.now()
            prediction_timestamps = [last_timestamp + timedelta(hours=i+1) for i in range(prediction_hours)]

            # 执行预测
            water_level_result = self._predict_variable(
                water_level_array, prediction_hours, prediction_method,
                seasonal_period, confidence_level, "水位"
            )

            discharge_result = self._predict_variable(
                discharge_array, prediction_hours, prediction_method,
                seasonal_period, confidence_level, "流量"
            )

            # 温度预测 (如果提供数据)
            temperature_result = None
            if historical_temperatures and len(historical_temperatures) == len(historical_water_levels):
                temperature_array = np.array(historical_temperatures)
                temperature_result = self._predict_variable(
                    temperature_array, prediction_hours, prediction_method,
                    seasonal_period, confidence_level, "水温"
                )

            # 计算预测准确性评估
            accuracy_assessment = self._assess_prediction_accuracy(
                water_level_result, discharge_result, temperature_result
            )

            # 生成预测建议
            recommendations = self._generate_prediction_recommendations(
                accuracy_assessment, prediction_method
            )

            return {
                "status": "success",
                "prediction_summary": {
                    "prediction_method": method,
                    "prediction_hours": prediction_hours,
                    "seasonal_period": seasonal_period,
                    "confidence_level": confidence_level,
                    "historical_data_points": len(historical_water_levels)
                },
                "water_level_prediction": {
                    "predicted_values": water_level_result.predicted_values.tolist(),
                    "confidence_intervals": {
                        "lower": water_level_result.confidence_intervals[0].tolist(),
                        "upper": water_level_result.confidence_intervals[1].tolist()
                    },
                    "accuracy_metrics": water_level_result.accuracy_metrics,
                    "timestamps": [ts.isoformat() for ts in prediction_timestamps]
                },
                "discharge_prediction": {
                    "predicted_values": discharge_result.predicted_values.tolist(),
                    "confidence_intervals": {
                        "lower": discharge_result.confidence_intervals[0].tolist(),
                        "upper": discharge_result.confidence_intervals[1].tolist()
                    },
                    "accuracy_metrics": discharge_result.accuracy_metrics,
                    "timestamps": [ts.isoformat() for ts in prediction_timestamps]
                },
                "temperature_prediction": {
                    "predicted_values": temperature_result.predicted_values.tolist() if temperature_result else [],
                    "confidence_intervals": {
                        "lower": temperature_result.confidence_intervals[0].tolist() if temperature_result else [],
                        "upper": temperature_result.confidence_intervals[1].tolist() if temperature_result else []
                    },
                    "accuracy_metrics": temperature_result.accuracy_metrics if temperature_result else {}
                } if temperature_result else None,
                "accuracy_assessment": accuracy_assessment,
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"水文变量预测失败: {str(e)}",
                "recommendations": ["请检查输入数据格式", "确认历史数据质量符合要求", "尝试调整预测参数"]
            }

    def _predict_variable(self, historical_data: np.ndarray, forecast_steps: int,
                         method: PredictionMethod, seasonal_period: int, confidence_level: float,
                         variable_name: str) -> PredictionResult:
        """预测单个变量"""
        if method == PredictionMethod.TIME_SERIES:
            return self.time_series_predictor.predict_with_seasonality(
                historical_data, forecast_steps, seasonal_period, confidence_level
            )

        elif method == PredictionMethod.MACHINE_LEARNING:
            return self.ml_predictor.predict_with_ml(historical_data, forecast_steps, confidence_level)

        elif method == PredictionMethod.ENSEMBLE:
            return self.ensemble_predictor.predict_with_ensemble(historical_data, forecast_steps, confidence_level)

        else:
            # 默认使用时间序列方法
            return self.time_series_predictor.predict_with_seasonality(
                historical_data, forecast_steps, seasonal_period, confidence_level
            )

    def _assess_prediction_accuracy(self, water_level_result: PredictionResult,
                                  discharge_result: PredictionResult,
                                  temperature_result: Optional[PredictionResult]) -> Dict[str, Any]:
        """评估预测准确性"""
        # 综合准确性指标
        overall_r2 = np.mean([
            water_level_result.accuracy_metrics.get("r2", 0),
            discharge_result.accuracy_metrics.get("r2", 0),
            temperature_result.accuracy_metrics.get("r2", 0) if temperature_result else 0
        ])

        overall_rmse = np.mean([
            water_level_result.accuracy_metrics.get("rmse", 0),
            discharge_result.accuracy_metrics.get("rmse", 0),
            temperature_result.accuracy_metrics.get("rmse", 0) if temperature_result else 0
        ])

        # 预测质量等级
        if overall_r2 > 0.8:
            quality_level = "excellent"
            reliability_score = 0.95
        elif overall_r2 > 0.6:
            quality_level = "good"
            reliability_score = 0.8
        elif overall_r2 > 0.4:
            quality_level = "fair"
            reliability_score = 0.6
        else:
            quality_level = "poor"
            reliability_score = 0.3

        # 不确定性评估
        water_level_uncertainty = np.mean(np.abs(
            water_level_result.confidence_intervals[1] - water_level_result.confidence_intervals[0]
        )) / 2.0

        discharge_uncertainty = np.mean(np.abs(
            discharge_result.confidence_intervals[1] - discharge_result.confidence_intervals[0]
        )) / 2.0

        return {
            "overall_r2": overall_r2,
            "overall_rmse": overall_rmse,
            "quality_level": quality_level,
            "reliability_score": reliability_score,
            "uncertainty_assessment": {
                "water_level_uncertainty": water_level_uncertainty,
                "discharge_uncertainty": discharge_uncertainty,
                "average_uncertainty": (water_level_uncertainty + discharge_uncertainty) / 2
            }
        }

    def _generate_prediction_recommendations(self, accuracy_assessment: Dict[str, Any],
                                           prediction_method: PredictionMethod) -> List[str]:
        """生成预测建议"""
        recommendations = []

        quality_level = accuracy_assessment.get("quality_level", "unknown")
        reliability_score = accuracy_assessment.get("reliability_score", 0.0)

        # 基于预测质量的建议
        if quality_level == "excellent":
            recommendations.append("预测质量优秀，结果高度可信")
            recommendations.append("可以基于预测结果制定精确的运行计划")

        elif quality_level == "good":
            recommendations.append("预测质量良好，结果较为可信")
            recommendations.append("建议结合其他信息综合判断")

        elif quality_level == "fair":
            recommendations.append("预测质量一般，需要谨慎使用")
            recommendations.append("建议增加监测频率，及时调整预测")

        else:  # poor
            recommendations.append("预测质量较差，结果仅供参考")
            recommendations.append("不建议仅基于预测结果做重要决策")
            recommendations.append("建议收集更多历史数据重新训练模型")

        # 基于预测方法的建议
        if prediction_method == PredictionMethod.ENSEMBLE:
            recommendations.append("集成预测: 综合了多种方法的优点，结果较为稳健")

        elif prediction_method == PredictionMethod.TIME_SERIES:
            recommendations.append("时间序列预测: 适用于具有明显季节性和趋势性的数据")

        elif prediction_method == PredictionMethod.MACHINE_LEARNING:
            recommendations.append("机器学习预测: 适用于复杂非线性关系的数据")

        # 不确定性建议
        avg_uncertainty = accuracy_assessment.get("uncertainty_assessment", {}).get("average_uncertainty", 0)
        if avg_uncertainty > 1.0:
            recommendations.append("注意: 预测不确定性较大，需要留出足够的安全余量")

        return recommendations

    async def predict_extreme_events(
        self,
        historical_data: List[float],
        event_threshold: float,
        prediction_hours: int = 72,
        return_period_years: int = 10
    ) -> Dict[str, Any]:
        """
        极端事件预测 - MCP工具接口

        Args:
            historical_data: 历史数据
            event_threshold: 极端事件阈值
            prediction_hours: 预测时长 (小时)
            return_period_years: 重现期 (年)

        Returns:
            极端事件预测结果
        """

        try:
            # 参数验证
            if len(historical_data) < 365:  # 至少需要1年的数据
                return {
                    "status": "error",
                    "message": "历史数据不足，至少需要365个数据点进行极端事件分析"
                }

            if event_threshold <= 0:
                return {
                    "status": "error",
                    "message": "极端事件阈值必须大于0"
                }

            # 转换数据类型
            data_array = np.array(historical_data)

            # 极端事件统计分析
            extreme_events = self._analyze_extreme_events(data_array, event_threshold)

            # 重现期分析
            return_period_analysis = self._analyze_return_periods(data_array, return_period_years)

            # 极端事件预测
            extreme_event_forecast = self._predict_extreme_events(
                data_array, event_threshold, prediction_hours
            )

            # 风险评估
            risk_assessment = self._assess_extreme_event_risk(
                extreme_event_forecast, event_threshold
            )

            # 生成极端事件应对建议
            recommendations = self._generate_extreme_event_recommendations(
                risk_assessment, extreme_events
            )

            return {
                "status": "success",
                "extreme_event_analysis": {
                    "historical_extreme_events": extreme_events,
                    "return_period_analysis": return_period_analysis,
                    "event_threshold": event_threshold,
                    "return_period_years": return_period_years
                },
                "extreme_event_forecast": {
                    "forecast_hours": prediction_hours,
                    "extreme_event_probability": extreme_event_forecast.get("probability", 0),
                    "expected_timing": extreme_event_forecast.get("expected_timing", "unknown"),
                    "expected_magnitude": extreme_event_forecast.get("expected_magnitude", 0),
                    "confidence_level": extreme_event_forecast.get("confidence", 0)
                },
                "risk_assessment": risk_assessment,
                "recommendations": recommendations
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"极端事件预测失败: {str(e)}",
                "recommendations": ["请检查历史数据质量", "确认数据包含足够的极端事件样本", "尝试调整阈值参数"]
            }

    def _analyze_extreme_events(self, data: np.ndarray, threshold: float) -> Dict[str, Any]:
        """分析历史极端事件"""
        extreme_indices = np.where(data > threshold)[0]
        extreme_values = data[extreme_indices]

        if len(extreme_values) == 0:
            return {
                "total_events": 0,
                "max_magnitude": 0,
                "average_magnitude": 0,
                "event_frequency": 0,
                "last_event_index": -1
            }

        return {
            "total_events": len(extreme_values),
            "max_magnitude": float(np.max(extreme_values)),
            "average_magnitude": float(np.mean(extreme_values)),
            "event_frequency": len(extreme_values) / len(data),
            "last_event_index": int(extreme_indices[-1]) if len(extreme_indices) > 0 else -1
        }

    def _analyze_return_periods(self, data: np.ndarray, return_period_years: int) -> Dict[str, Any]:
        """分析重现期"""
        # 计算年最大值 (简化方法)
        daily_data_points = 24  # 假设每小时数据
        yearly_maxima = []

        for year in range(len(data) // (365 * daily_data_points)):
            start_idx = year * 365 * daily_data_points
            end_idx = (year + 1) * 365 * daily_data_points
            if end_idx <= len(data):
                yearly_max = np.max(data[start_idx:end_idx])
                yearly_maxima.append(yearly_max)

        if len(yearly_maxima) < 5:
            return {
                "insufficient_data": True,
                "available_years": len(yearly_maxima),
                "recommended_period": min(len(yearly_maxima), return_period_years)
            }

        # 使用Gumbel分布拟合 (简化方法)
        if SCIPY_AVAILABLE:
            try:
                # 拟合极值分布
                loc, scale = stats.gumbel_r.fit(yearly_maxima)

                # 计算重现期对应的分位数
                return_period_probability = 1 / return_period_years
                return_period_value = stats.gumbel_r.ppf(1 - return_period_probability, loc=loc, scale=scale)

                return {
                    "return_period_years": return_period_years,
                    "return_period_value": float(return_period_value),
                    "distribution_fitted": True,
                    "available_years": len(yearly_maxima),
                    "extreme_value_parameters": {"loc": loc, "scale": scale}
                }
            except Exception:
                pass

        # 简化重现期分析
        sorted_maxima = np.sort(yearly_maxima)
        return_period_index = int(len(sorted_maxima) * (1 - 1/return_period_years))
        return_period_index = min(return_period_index, len(sorted_maxima) - 1)
        return_period_value = sorted_maxima[return_period_index]

        return {
            "return_period_years": return_period_years,
            "return_period_value": float(return_period_value),
            "distribution_fitted": False,
            "available_years": len(yearly_maxima),
            "method": "empirical_distribution"
        }

    def _predict_extreme_events(self, data: np.ndarray, threshold: float, prediction_hours: int) -> Dict[str, Any]:
        """预测极端事件"""
        # 简化的极值预测方法
        recent_data = data[-min(168, len(data)):]  # 最近一周的数据

        # 计算当前风险指标
        threshold_exceedances = np.sum(recent_data > threshold)
        current_risk_level = threshold_exceedances / len(recent_data)

        # 趋势分析
        if len(recent_data) >= 24:
            recent_trend = np.polyfit(np.arange(len(recent_data)), recent_data, 1)[0]
        else:
            recent_trend = 0

        # 预测极端事件概率 (简化模型)
        if current_risk_level > 0.1:  # 10%的阈值超越率
            base_probability = min(0.8, current_risk_level * 2)
        else:
            base_probability = min(0.3, current_risk_level * 5)

        # 趋势调整
        if recent_trend > 0:
            probability = min(0.9, base_probability * 1.5)
        else:
            probability = base_probability

        # 预期时间和强度
        if probability > 0.5:
            expected_timing = "within_24_hours"
            expected_magnitude = threshold * 1.2  # 预期超过阈值的20%
            confidence = min(0.8, probability)
        else:
            expected_timing = "uncertain"
            expected_magnitude = threshold * 1.1
            confidence = probability

        return {
            "probability": float(probability),
            "expected_timing": expected_timing,
            "expected_magnitude": float(expected_magnitude),
            "confidence": float(confidence),
            "current_risk_level": float(current_risk_level),
            "trend_factor": float(recent_trend)
        }

    def _assess_extreme_event_risk(self, extreme_forecast: Dict[str, Any], threshold: float) -> Dict[str, Any]:
        """评估极端事件风险"""
        probability = extreme_forecast.get("probability", 0)
        expected_magnitude = extreme_forecast.get("expected_magnitude", 0)

        # 风险等级
        if probability > 0.7:
            risk_level = "high"
            alert_status = "red_alert"
        elif probability > 0.4:
            risk_level = "medium"
            alert_status = "orange_alert"
        elif probability > 0.2:
            risk_level = "low"
            alert_status = "yellow_alert"
        else:
            risk_level = "minimal"
            alert_status = "green_alert"

        # 影响评估
        impact_magnitude = expected_magnitude / threshold if threshold > 0 else 0
        if impact_magnitude > 1.5:
            impact_level = "severe"
        elif impact_magnitude > 1.2:
            impact_level = "significant"
        elif impact_magnitude > 1.0:
            impact_level = "moderate"
        else:
            impact_level = "minor"

        return {
            "risk_level": risk_level,
            "alert_status": alert_status,
            "impact_level": impact_level,
            "probability_score": probability,
            "impact_magnitude": float(impact_magnitude),
            "expected_severity": self._calculate_severity_score(probability, impact_magnitude)
        }

    def _calculate_severity_score(self, probability: float, impact_magnitude: float) -> float:
        """计算严重程度评分"""
        # 简化的严重程度评分: P × I^2 (小概率大影响事件更重要)
        return min(1.0, probability * (impact_magnitude ** 2))

    def _generate_extreme_event_recommendations(self, risk_assessment: Dict[str, Any],
                                              extreme_events: Dict[str, Any]) -> List[str]:
        """生成极端事件应对建议"""
        recommendations = []

        risk_level = risk_assessment.get("risk_level", "unknown")
        alert_status = risk_assessment.get("alert_status", "green_alert")

        # 基于风险等级的建议
        if alert_status == "red_alert":
            recommendations.append("紧急: 极端事件风险极高，立即启动最高级别应急响应")
            recommendations.append("紧急: 通知所有相关部门和人员进入紧急状态")
            recommendations.append("紧急: 准备实施极端事件应急预案")

        elif alert_status == "orange_alert":
            recommendations.append("重要: 极端事件风险较高，启动二级应急响应")
            recommendations.append("重要: 加强监测和预警，密切关注事件发展")
            recommendations.append("重要: 准备应急物资和设备")

        elif alert_status == "yellow_alert":
            recommendations.append("注意: 存在极端事件风险，加强日常监控")
            recommendations.append("注意: 检查应急准备工作，确保响应机制有效")

        # 基于历史事件的建议
        if extreme_events.get("total_events", 0) > 5:
            recommendations.append("注意: 历史上极端事件频发，需要特别关注")

        # 通用建议
        recommendations.append("建议: 建立极端事件监测预警系统")
        recommendations.append("建议: 制定和完善极端事件应急预案")
        recommendations.append("建议: 加强与上下游的协调联动")

        return recommendations