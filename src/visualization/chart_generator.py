"""
2D图表自动生成器
根据水电数据特征自动生成2D图表
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

@dataclass
class ChartData:
    """图表数据"""
    x_values: List[float]
    y_values: List[float]
    labels: List[str]
    timestamps: List[datetime]
    series_names: List[str]
    chart_type: str
    title: str
    x_label: str
    y_label: str

class ChartGenerator:
    """2D图表自动生成器"""

    def __init__(self):
        self.chart_templates = {
            'water_level': self._generate_water_level_chart,
            'discharge': self._generate_discharge_chart,
            'temperature': self._generate_temperature_chart,
            'flood_risk': self._generate_flood_risk_chart,
            'prediction': self._generate_prediction_chart,
            'anomaly': self._generate_anomaly_chart,
            'risk_assessment': self._generate_risk_chart,
            'correlation': self._generate_correlation_chart
        }

    def _determine_chart_type(self, data: Dict[str, Any]) -> str:
        """根据数据特征确定图表类型"""
        if 'water_level' in data or '水位' in data:
            return 'water_level'
        elif 'discharge' in data or '流量' in data:
            return 'discharge'
        elif 'temperature' in data or '温度' in data:
            return 'temperature'
        elif 'risk' in data or '风险' in data:
            return 'flood_risk'
        elif 'prediction' in data or '预测' in data:
            return 'prediction'
        elif 'anomaly' in data or '异常' in data:
            return 'anomaly'
        else:
            return 'line'  # 默认折线图

    def _generate_water_level_chart(self, timestamps: List[datetime], water_levels: List[float],
                                  historical_max: Optional[float] = None,
                                  warning_level: Optional[float] = None,
                                  danger_level: Optional[float] = None) -> Dict[str, Any]:
        """生成水位图表"""

        # 添加警戒线
        annotations = []

        if warning_level:
            annotations.append({
                'type': 'line',
                'y': warning_level,
                'borderColor': 'orange',
                'borderWidth': 2,
                'borderDash': [5, 5],
                'label': {
                    'content': '警戒水位',
                    'enabled': True,
                    'position': 'right'
                }
            })

        if danger_level:
            annotations.append({
                'type': 'line',
                'y': danger_level,
                'borderColor': 'red',
                'borderWidth': 2,
                'borderDash': [5, 5],
                'label': {
                    'content': '危险水位',
                    'enabled': True,
                    'position': 'right'
                }
            })

        return {
            'chart_type': 'line',
            'title': '水位变化趋势',
            'x_label': '时间',
            'y_label': '水位 (m)',
            'data': {
                'labels': [ts.isoformat() for ts in timestamps],
                'datasets': [{
                    'label': '水位',
                    'data': water_levels,
                    'borderColor': 'blue',
                    'backgroundColor': 'rgba(0, 0, 255, 0.1)',
                    'fill': True,
                    'tension': 0.4
                }]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {
                        'display': True,
                        'position': 'top'
                    },
                    'tooltip': {
                        'mode': 'index',
                        'intersect': False
                    }
                },
                'scales': {
                    'x': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '时间'
                        }
                    },
                    'y': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '水位 (m)'
                        }
                    }
                },
                'annotation': {
                    'annotations': annotations
                }
            }
        }

    def _generate_discharge_chart(self, timestamps: List[datetime], discharges: List[float],
                                capacity: Optional[float] = None) -> Dict[str, Any]:
        """生成流量图表"""

        annotations = []
        if capacity:
            annotations.append({
                'type': 'line',
                'y': capacity,
                'borderColor': 'red',
                'borderWidth': 2,
                'borderDash': [5, 5],
                'label': {
                    'content': '最大泄流能力',
                    'enabled': True,
                    'position': 'right'
                }
            })

        return {
            'chart_type': 'line',
            'title': '流量变化趋势',
            'x_label': '时间',
            'y_label': '流量 (m³/s)',
            'data': {
                'labels': [ts.isoformat() for ts in timestamps],
                'datasets': [{
                    'label': '流量',
                    'data': discharges,
                    'borderColor': 'green',
                    'backgroundColor': 'rgba(0, 255, 0, 0.1)',
                    'fill': True,
                    'tension': 0.4
                }]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {
                        'display': True,
                        'position': 'top'
                    }
                },
                'scales': {
                    'x': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '时间'
                        }
                    },
                    'y': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '流量 (m³/s)'
                        }
                    }
                },
                'annotation': {
                    'annotations': annotations
                }
            }
        }

    def _generate_flood_risk_chart(self, timestamps: List[datetime], risk_levels: List[int],
                                risk_scores: List[float]) -> Dict[str, Any]:
        """生成洪水风险图表"""

        # 风险等级颜色映射
        risk_colors = {
            1: 'green',      # 低风险
            2: 'yellow',     # 中等风险
            3: 'orange',     # 高风险
            4: 'red'         # 极高风险
        }

        return {
            'chart_type': 'line',
            'title': '洪水风险等级',
            'x_label': '时间',
            'y_label': '风险等级',
            'data': {
                'labels': [ts.isoformat() for ts in timestamps],
                'datasets': [{
                    'label': '风险等级',
                    'data': risk_levels,
                    'borderColor': [risk_colors.get(level, 'blue') for level in risk_levels],
                    'backgroundColor': [risk_colors.get(level, 'blue') for level in risk_levels],
                    'fill': False,
                    'pointRadius': 5,
                    'pointHoverRadius': 8
                }]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {
                        'display': True,
                        'position': 'top'
                    }
                },
                'scales': {
                    'x': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '时间'
                        }
                    },
                    'y': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '风险等级'
                        },
                        'min': 1,
                        'max': 4,
                        'ticks': {
                            'stepSize': 1
                        }
                    }
                }
            }
        }

    def _generate_prediction_chart(self, timestamps: List[datetime],
                                 historical_values: List[float],
                                 predicted_values: List[float],
                                 confidence_lower: List[float],
                                 confidence_upper: List[float]) -> Dict[str, Any]:
        """生成预测图表"""

        # 分割历史数据和预测数据
        historical_timestamps = timestamps[:len(historical_values)]
        predicted_timestamps = timestamps[len(historical_values):]

        return {
            'chart_type': 'line',
            'title': '水文变量预测',
            'x_label': '时间',
            'y_label': '数值',
            'data': {
                'labels': [ts.isoformat() for ts in timestamps],
                'datasets': [
                    {
                        'label': '历史数据',
                        'data': [[ts.isoformat(), val] for ts, val in zip(historical_timestamps, historical_values)],
                        'borderColor': 'blue',
                        'backgroundColor': 'transparent',
                        'fill': False
                    },
                    {
                        'label': '预测数据',
                        'data': [[ts.isoformat(), val] for ts, val in zip(predicted_timestamps, predicted_values)],
                        'borderColor': 'red',
                        'backgroundColor': 'transparent',
                        'fill': False,
                        'borderDash': [5, 5]
                    },
                    {
                        'label': '置信区间上限',
                        'data': [[ts.isoformat(), val] for ts, val in zip(predicted_timestamps, confidence_upper)],
                        'borderColor': 'rgba(255, 0, 0, 0.3)',
                        'backgroundColor': 'transparent',
                        'fill': False
                    },
                    {
                        'label': '置信区间下限',
                        'data': [[ts.isoformat(), val] for ts, val in zip(predicted_timestamps, confidence_lower)],
                        'borderColor': 'rgba(255, 0, 0, 0.3)',
                        'backgroundColor': 'transparent',
                        'fill': False
                    }
                ]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {
                        'display': True,
                        'position': 'top'
                    }
                },
                'scales': {
                    'x': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '时间'
                        }
                    },
                    'y': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '数值'
                        }
                    }
                }
            }
        }

    def _generate_anomaly_chart(self, timestamps: List[datetime], values: List[float],
                               anomaly_scores: List[float], threshold: float = 2.0) -> Dict[str, Any]:
        """生成异常检测图表"""

        # 标记异常点
        colors = ['red' if score > threshold else 'blue' for score in anomaly_scores]
        point_sizes = [8 if score > threshold else 3 for score in anomaly_scores]

        return {
            'chart_type': 'scatter',
            'title': '异常检测结果',
            'x_label': '时间',
            'y_label': '数值',
            'data': {
                'labels': [ts.isoformat() for ts in timestamps],
                'datasets': [{
                    'label': '数据点',
                    'data': values,
                    'borderColor': colors,
                    'backgroundColor': colors,
                    'pointRadius': point_sizes,
                    'showLine': True,
                    'tension': 0.4
                }]
            },
            'options': {
                'responsive': True,
                'maintainAspectRatio': False,
                'plugins': {
                    'legend': {
                        'display': True,
                        'position': 'top'
                    }
                },
                'scales': {
                    'x': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '时间'
                        }
                    },
                    'y': {
                        'display': True,
                        'title': {
                            'display': True,
                            'text': '数值'
                        }
                    }
                }
            }
        }

    def generate_automatic_chart(self, data: Dict[str, Any], chart_type: Optional[str] = None,
                                title: Optional[str] = None) -> Dict[str, Any]:
        """
        根据数据特征自动生成图表

        Args:
            data: 数据字典
            chart_type: 图表类型（可选）
            title: 图表标题（可选）

        Returns:
            图表配置
        """

        # 自动确定图表类型
        if chart_type is None:
            chart_type = self._determine_chart_type(data)

        # 提取通用数据
        timestamps = data.get('timestamps', [])
        if not timestamps and 'time' in data:
            timestamps = [datetime.fromisoformat(t) for t in data['time']]

        # 根据图表类型生成相应的图表
        if chart_type == 'water_level':
            water_levels = data.get('water_levels', data.get('values', []))
            warning_level = data.get('warning_level')
            danger_level = data.get('danger_level')
            return self._generate_water_level_chart(
                timestamps, water_levels, warning_level, danger_level
            )

        elif chart_type == 'discharge':
            discharges = data.get('discharges', data.get('values', []))
            capacity = data.get('capacity')
            return self._generate_discharge_chart(timestamps, discharges, capacity)

        elif chart_type == 'flood_risk':
            risk_levels = data.get('risk_levels', [])
            risk_scores = data.get('risk_scores', [])
            return self._generate_flood_risk_chart(timestamps, risk_levels, risk_scores)

        elif chart_type == 'prediction':
            historical_values = data.get('historical_values', [])
            predicted_values = data.get('predicted_values', [])
            confidence_lower = data.get('confidence_lower', [])
            confidence_upper = data.get('confidence_upper', [])
            return self._generate_prediction_chart(
                timestamps, historical_values, predicted_values,
                confidence_lower, confidence_upper
            )

        elif chart_type == 'anomaly':
            values = data.get('values', [])
            anomaly_scores = data.get('anomaly_scores', [])
            threshold = data.get('threshold', 2.0)
            return self._generate_anomaly_chart(timestamps, values, anomaly_scores, threshold)

        else:
            # 默认折线图
            values = data.get('values', [])
            return {
                'chart_type': 'line',
                'title': title or '数据趋势',
                'x_label': '时间',
                'y_label': '数值',
                'data': {
                    'labels': [ts.isoformat() for ts in timestamps],
                    'datasets': [{
                        'label': '数据',
                        'data': values,
                        'borderColor': 'blue',
                        'backgroundColor': 'transparent',
                        'fill': False,
                        'tension': 0.4
                    }]
                }
            }

    def generate_dashboard(self, datasets: List[Dict[str, Any]],
                         layout: str = 'grid') -> Dict[str, Any]:
        """
        生成数据仪表板

        Args:
            datasets: 数据集列表
            layout: 布局方式 (grid/vertical/horizontal)

        Returns:
            仪表板配置
        """

        charts = []
        for dataset in datasets:
            chart = self.generate_automatic_chart(dataset)
            charts.append(chart)

        return {
            'dashboard_type': 'hydropower_monitoring',
            'layout': layout,
            'charts': charts,
            'timestamp': datetime.now().isoformat(),
            'refresh_interval': 300,  # 5分钟刷新
            'options': {
                'auto_refresh': True,
                'show_legend': True,
                'show_tooltips': True
            }
        }