"""
2D地图自动生成器
根据空间数据自动生成2D地图
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np

@dataclass
class MapFeature:
    """地图要素"""
    type: str  # point, line, polygon
    coordinates: List[Any]
    properties: Dict[str, Any]
    style: Dict[str, Any]

class MapGenerator:
    """2D地图自动生成器"""

    def __init__(self):
        self.layer_templates = {
            'water_level_stations': self._create_water_level_station_layer,
            'discharge_stations': self._create_discharge_station_layer,
            'flood_risk_zones': self._create_flood_risk_layer,
            'reservoir_boundary': self._create_reservoir_boundary_layer,
            'warning_zones': self._create_warning_zone_layer,
            'hydrological_network': self._create_hydrological_network_layer
        }

    def _create_water_level_station_layer(self, stations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建水位站点图层"""
        features = []

        for station in stations:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [station['longitude'], station['latitude']]
                },
                'properties': {
                    'station_id': station.get('id', 'unknown'),
                    'station_name': station.get('name', 'Unknown Station'),
                    'water_level': station.get('water_level', 0),
                    'timestamp': station.get('timestamp', datetime.now().isoformat()),
                    'status': station.get('status', 'normal')
                }
            }
            features.append(feature)

        return {
            'id': 'water_level_stations',
            'type': 'circle',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'FeatureCollection',
                    'features': features
                }
            },
            'paint': {
                'circle-radius': [
                    'case',
                    ['==', ['get', 'status'], 'warning'], 8,
                    ['==', ['get', 'status'], 'danger'], 12,
                    6  # normal
                ],
                'circle-color': [
                    'case',
                    ['==', ['get', 'status'], 'warning'], '#FFA500',
                    ['==', ['get', 'status'], 'danger'], '#FF0000',
                    '#0000FF'  # normal
                ],
                'circle-stroke-width': 2,
                'circle-stroke-color': '#FFFFFF'
            },
            'layout': {
                'visibility': 'visible'
            }
        }

    def _create_flood_risk_layer(self, risk_zones: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建洪水风险区域图层"""
        features = []

        for zone in risk_zones:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': zone['coordinates']  # [[lon, lat], [lon, lat], ...]
                },
                'properties': {
                    'zone_id': zone.get('id', 'unknown'),
                    'zone_name': zone.get('name', 'Unknown Zone'),
                    'risk_level': zone.get('risk_level', 1),
                    'risk_score': zone.get('risk_score', 0.0),
                    'population_exposed': zone.get('population_exposed', 0),
                    'area_km2': zone.get('area_km2', 0.0)
                }
            }
            features.append(feature)

        # 风险等级颜色映射
        return {
            'id': 'flood_risk_zones',
            'type': 'fill',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'FeatureCollection',
                    'features': features
                }
            },
            'paint': {
                'fill-color': [
                    'case',
                    ['==', ['get', 'risk_level'], 1], 'rgba(0, 255, 0, 0.3)',
                    ['==', ['get', 'risk_level'], 2], 'rgba(255, 255, 0, 0.4)',
                    ['==', ['get', 'risk_level'], 3], 'rgba(255, 165, 0, 0.5)',
                    ['==', ['get', 'risk_level'], 4], 'rgba(255, 0, 0, 0.6)',
                    'rgba(128, 128, 128, 0.3)'
                ],
                'fill-outline-color': [
                    'case',
                    ['==', ['get', 'risk_level'], 1], 'rgba(0, 255, 0, 0.8)',
                    ['==', ['get', 'risk_level'], 2], 'rgba(255, 255, 0, 0.8)',
                    ['==', ['get', 'risk_level'], 3], 'rgba(255, 165, 0, 0.8)',
                    ['==', ['get', 'risk_level'], 4], 'rgba(255, 0, 0, 0.8)',
                    'rgba(128, 128, 128, 0.8)'
                ]
            },
            'layout': {
                'visibility': 'visible'
            }
        }

    def _create_warning_zone_layer(self, warning_zones: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建预警区域图层"""
        features = []

        for zone in warning_zones:
            center = zone['center']
            radius = zone['radius']  # in meters

            # 创建圆形缓冲区
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': center
                },
                'properties': {
                    'zone_id': zone.get('id', 'unknown'),
                    'zone_name': zone.get('name', 'Unknown Zone'),
                    'radius': radius,
                    'warning_type': zone.get('warning_type', 'general'),
                    'severity': zone.get('severity', 'low')
                }
            }
            features.append(feature)

        return {
            'id': 'warning_zones',
            'type': 'circle',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'FeatureCollection',
                    'features': features
                }
            },
            'paint': {
                'circle-radius': ['get', 'radius'],
                'circle-radius-transition': {
                    'duration': 0
                },
                'circle-color': [
                    'case',
                    ['==', ['get', 'severity'], 'low'], 'rgba(0, 255, 0, 0.2)',
                    ['==', ['get', 'severity'], 'medium'], 'rgba(255, 255, 0, 0.3)',
                    ['==', ['get', 'severity'], 'high'], 'rgba(255, 165, 0, 0.4)',
                    ['==', ['get', 'severity'], 'critical'], 'rgba(255, 0, 0, 0.5)',
                    'rgba(128, 128, 128, 0.2)'
                ],
                'circle-stroke-width': 2,
                'circle-stroke-color': [
                    'case',
                    ['==', ['get', 'severity'], 'low'], 'rgba(0, 255, 0, 0.8)',
                    ['==', ['get', 'severity'], 'medium'], 'rgba(255, 255, 0, 0.8)',
                    ['==', ['get', 'severity'], 'high'], 'rgba(255, 165, 0, 0.8)',
                    ['==', ['get', 'severity'], 'critical'], 'rgba(255, 0, 0, 0.8)',
                    'rgba(128, 128, 128, 0.8)'
                ]
            }
        }

    def generate_hydrological_map(self, stations: List[Dict[str, Any]],
                                risk_zones: List[Dict[str, Any]] = None,
                                warning_zones: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成水文监测地图

        Args:
            stations: 水文站点列表
            risk_zones: 风险区域列表
            warning_zones: 预警区域列表

        Returns:
            地图配置
        """

        layers = []

        # 添加风险区域图层（最底层）
        if risk_zones:
            risk_layer = self._create_flood_risk_layer(risk_zones)
            layers.append(risk_layer)

        # 添加预警区域图层
        if warning_zones:
            warning_layer = self._create_warning_zone_layer(warning_zones)
            layers.append(warning_layer)

        # 添加站点图层（最上层）
        if stations:
            station_layer = self._create_water_level_station_layer(stations)
            layers.append(station_layer)

        return {
            'map_type': 'hydrological_monitoring',
            'center': [116.4074, 39.9042],  # 北京
            'zoom': 10,
            'layers': layers,
            'controls': {
                'navigation': True,
                'scale': True,
                'fullscreen': True
            },
            'interactions': {
                'popup_on_click': True,
                'tooltip_on_hover': True,
                'cluster_markers': True
            }
        }

    def generate_flood_evolution_map(self, flood_extent: Dict[str, Any],
                                   evolution_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成洪水演进地图

        Args:
            flood_extent: 洪水范围
            evolution_steps: 演进步骤

        Returns:
            洪水演进地图配置
        """

        layers = []

        # 基础洪水范围
        if flood_extent:
            flood_layer = {
                'id': 'flood_extent',
                'type': 'fill',
                'source': {
                    'type': 'geojson',
                    'data': {
                        'type': 'Feature',
                        'geometry': flood_extent['geometry'],
                        'properties': {
                            'stage': 0,
                            'water_depth': flood_extent.get('depth', 0)
                        }
                    }
                },
                'paint': {
                    'fill-color': 'rgba(0, 0, 255, 0.3)',
                    'fill-outline-color': 'blue'
                }
            }
            layers.append(flood_layer)

        # 演进动画帧
        animation_frames = []
        for idx, step in enumerate(evolution_steps):
            frame = {
                'frame_id': idx,
                'timestamp': step.get('timestamp'),
                'water_level': step.get('water_level'),
                'layers': [{
                    'id': f'flood_step_{idx}',
                    'type': 'fill',
                    'source': {
                        'type': 'geojson',
                        'data': {
                            'type': 'Feature',
                            'geometry': step['geometry'],
                            'properties': {
                                'stage': idx + 1,
                                'water_depth': step.get('depth', 0)
                            }
                        }
                    },
                    'paint': {
                        'fill-color': f'rgba(0, {50 + idx * 20}, 255, {0.2 + idx * 0.1})',
                        'fill-outline-color': 'blue'
                    },
                    'layout': {
                        'visibility': 'none'  # 默认隐藏，通过动画控制显示
                    }
                }]
            }
            animation_frames.append(frame)

        return {
            'map_type': 'flood_evolution',
            'center': flood_extent.get('center', [116.4074, 39.9042]),
            'zoom': 12,
            'base_layers': layers,
            'animation_frames': animation_frames,
            'animation_config': {
                'duration': 5000,  # 5秒动画
                'autoplay': True,
                'loop': True,
                'frame_delay': 500  # 每帧500ms
            }
        }

    def generate_reservoir_map(self, reservoir_boundary: Dict[str, Any],
                             current_water_level: float,
                             dam_location: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成水库地图

        Args:
            reservoir_boundary: 水库边界
            current_water_level: 当前水位
            dam_location: 大坝位置

        Returns:
            水库地图配置
        """

        layers = []

        # 水库边界
        boundary_layer = {
            'id': 'reservoir_boundary',
            'type': 'line',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'Feature',
                    'geometry': reservoir_boundary['geometry'],
                    'properties': {
                        'name': reservoir_boundary.get('name', 'Reservoir')
                    }
                }
            },
            'paint': {
                'line-color': 'brown',
                'line-width': 2
            }
        }
        layers.append(boundary_layer)

        # 水位填充
        water_body_layer = {
            'id': 'water_body',
            'type': 'fill',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'Feature',
                    'geometry': reservoir_boundary['geometry'],
                    'properties': {
                        'water_level': current_water_level
                    }
                }
            },
            'paint': {
                'fill-color': 'rgba(0, 100, 200, 0.7)',
                'fill-outline-color': 'blue'
            }
        }
        layers.append(water_body_layer)

        # 大坝位置
        dam_layer = {
            'id': 'dam_location',
            'type': 'symbol',
            'source': {
                'type': 'geojson',
                'data': {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': dam_location['coordinates']
                    },
                    'properties': {
                        'dam_name': dam_location.get('name', 'Dam'),
                        'dam_height': dam_location.get('height', 0)
                    }
                }
            },
            'layout': {
                'icon-image': 'dam-15',
                'text-field': ['get', 'dam_name'],
                'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
                'text-size': 12,
                'text-anchor': 'top'
            },
            'paint': {
                'text-color': '#000000'
            }
        }
        layers.append(dam_layer)

        return {
            'map_type': 'reservoir_monitoring',
            'center': dam_location['coordinates'],
            'zoom': 13,
            'layers': layers,
            'realtime_updates': {
                'water_level': current_water_level,
                'update_interval': 300  # 5分钟
            }
        }

    def get_map_statistics(self, map_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取地图统计信息"""
        layers = map_config.get('layers', [])

        stats = {
            'total_layers': len(layers),
            'layer_types': {},
            'visible_layers': 0
        }

        for layer in layers:
            layer_type = layer.get('type', 'unknown')
            stats['layer_types'][layer_type] = stats['layer_types'].get(layer_type, 0) + 1

            if layer.get('layout', {}).get('visibility', 'visible') == 'visible':
                stats['visible_layers'] += 1

        return stats