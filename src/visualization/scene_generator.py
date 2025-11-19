"""
3D场景自动生成器
基于Deck.gl的3D可视化，用于洪水淹没、水库结构等专业场景
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Point3D:
    """3D坐标点"""
    x: float
    y: float
    z: float

@dataclass
class TerrainData:
    """地形数据"""
    elevation: np.ndarray
    resolution: float
    bounds: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y

class Scene3DGenerator:
    """3D场景自动生成器"""

    def __init__(self):
        self.scene_templates = {
            'flood_submersion': self._create_flood_submersion_scene,
            'reservoir_structure': self._create_reservoir_structure_scene,
            'terrain_visualization': self._create_terrain_scene,
            'dam_model': self._create_dam_model_scene,
            'watershed_analysis': self._create_watershed_scene
        }

    def _create_flood_submersion_scene(self, terrain: TerrainData,
                                     flood_extent: Dict[str, Any],
                                     water_level: float,
                                     time_series: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """创建洪水淹没3D场景"""

        # 地形图层
        terrain_layer = {
            'id': 'terrain',
            'type': 'TerrainLayer',
            'props': {
                'elevationData': terrain.elevation.tolist(),
                'bounds': terrain.bounds,
                'meshMaxError': 4.0,
                'elevationScale': 1.0,
                'texture': None,
                'color': [139, 69, 19]  # 棕色表示陆地
            }
        }

        # 洪水淹没区域
        flood_geometry = flood_extent.get('geometry', {}).get('coordinates', [])

        flood_layer = {
            'id': 'flood_submersion',
            'type': 'PolygonLayer',
            'props': {
                'data': [{
                    'polygon': flood_geometry,
                    'elevation': water_level,
                    'fillColor': [0, 100, 200, 180],
                    'lineColor': [0, 50, 150],
                    'lineWidth': 2
                }],
                'getPolygon': 'polygon',
                'getElevation': 'elevation',
                'getFillColor': 'fillColor',
                'getLineColor': 'lineColor',
                'getLineWidth': 'lineWidth',
                'extruded': True,
                'pickable': True,
                'opacity': 0.8
            }
        }

        # 洪水演进动画帧
        animation_layers = []
        if time_series:
            for idx, step in enumerate(time_series):
                animation_layer = {
                    'id': f'flood_step_{idx}',
                    'type': 'PolygonLayer',
                    'visible': False,  # 默认隐藏
                    'props': {
                        'data': [{
                            'polygon': step.get('geometry', {}).get('coordinates', []),
                            'elevation': step.get('water_level', water_level),
                            'fillColor': [0, 100 + idx * 20, 200, 180 - idx * 10],
                            'timestamp': step.get('timestamp')
                        }],
                        'extruded': True,
                        'pickable': True
                    }
                }
                animation_layers.append(animation_layer)

        return {
            'scene_type': 'flood_submersion',
            'initialViewState': {
                'longitude': np.mean(terrain.bounds[0::2]),
                'latitude': np.mean(terrain.bounds[1::2]),
                'zoom': 13,
                'pitch': 60,  # 倾斜角度，便于观察3D效果
                'bearing': 0
            },
            'layers': [terrain_layer, flood_layer] + animation_layers,
            'animation_config': {
                'duration': 10000,  # 10秒动画
                'autoplay': True,
                'loop': True,
                'frame_delay': 1000  # 每帧1秒
            } if time_series else None,
            'effects': ['lighting', 'shadows'],
            'lighting': {
                'type': 'ambient',
                'color': [255, 255, 255],
                'intensity': 0.4
            }
        }

    def _create_reservoir_structure_scene(self, reservoir_boundary: Dict[str, Any],
                                        dam_structure: Dict[str, Any],
                                        current_water_level: float,
                                        max_capacity: float) -> Dict[str, Any]:
        """创建水库结构3D场景"""

        # 水库边界（水体）
        reservoir_geometry = reservoir_boundary.get('geometry', {}).get('coordinates', [])

        reservoir_layer = {
            'id': 'reservoir_water',
            'type': 'PolygonLayer',
            'props': {
                'data': [{
                    'polygon': reservoir_geometry,
                    'elevation': current_water_level,
                    'fillColor': [0, 100, 200, 200],
                    'lineColor': [0, 50, 150],
                    'capacity_ratio': current_water_level / max_capacity
                }],
                'getPolygon': 'polygon',
                'getElevation': 'elevation',
                'getFillColor': 'fillColor',
                'getLineColor': 'lineColor',
                'extruded': True,
                'pickable': True,
                'opacity': 0.7
            }
        }

        # 大坝结构
        dam_geometry = dam_structure.get('geometry', {}).get('coordinates', [])
        dam_height = dam_structure.get('height', 50)

        dam_layer = {
            'id': 'dam_structure',
            'type': 'PolygonLayer',
            'props': {
                'data': [{
                    'polygon': dam_geometry,
                    'elevation': dam_height,
                    'fillColor': [128, 128, 128, 255],  # 灰色混凝土
                    'lineColor': [64, 64, 64],
                    'dam_name': dam_structure.get('name', 'Dam'),
                    'dam_type': dam_structure.get('type', 'gravity')
                }],
                'getPolygon': 'polygon',
                'getElevation': 'elevation',
                'getFillColor': 'fillColor',
                'getLineColor': 'lineColor',
                'extruded': True,
                'pickable': True
            }
        }

        # 溢洪道
        spillway_positions = dam_structure.get('spillway_positions', [])
        spillway_layer = {
            'id': 'spillway',
            'type': 'PointCloudLayer',
            'props': {
                'data': [{'position': pos, 'color': [255, 255, 255]} for pos in spillway_positions],
                'getPosition': 'position',
                'getColor': 'color',
                'pointSize': 5,
                'pickable': True
            }
        }

        center_coords = dam_structure.get('center', [116.4074, 39.9042])

        return {
            'scene_type': 'reservoir_structure',
            'initialViewState': {
                'longitude': center_coords[0],
                'latitude': center_coords[1],
                'zoom': 15,
                'pitch': 45,
                'bearing': 30
            },
            'layers': [reservoir_layer, dam_layer, spillway_layer],
            'widget_config': {
                'show_water_level_indicator': True,
                'show_capacity_gauge': True,
                'realtime_update': True
            }
        }

    def _create_terrain_scene(self, terrain: TerrainData,
                            exaggeration: float = 2.0) -> Dict[str, Any]:
        """创建地形3D场景"""

        terrain_layer = {
            'id': 'terrain_surface',
            'type': 'TerrainLayer',
            'props': {
                'elevationData': terrain.elevation.tolist(),
                'bounds': terrain.bounds,
                'meshMaxError': 2.0,
                'elevationScale': exaggeration,
                'color': [139, 69, 19]
            }
        }

        # 等高线
        contours = self._generate_contours(terrain.elevation, terrain.bounds, interval=10)

        contour_layer = {
            'id': 'contours',
            'type': 'PathLayer',
            'props': {
                'data': contours,
                'getPath': 'path',
                'getColor': [0, 0, 0],
                'getWidth': 1,
                'pickable': True
            }
        }

        return {
            'scene_type': 'terrain_visualization',
            'initialViewState': {
                'longitude': np.mean(terrain.bounds[0::2]),
                'latitude': np.mean(terrain.bounds[1::2]),
                'zoom': 12,
                'pitch': 50,
                'bearing': 0
            },
            'layers': [terrain_layer, contour_layer],
            'analysis_tools': {
                'elevation_profile': True,
                'slope_analysis': True,
                'aspect_analysis': True
            }
        }

    def _create_dam_model_scene(self, dam_profile: Dict[str, Any],
                              materials: Optional[Dict] = None) -> Dict[str, Any]:
        """创建大坝3D模型场景"""

        # 大坝主结构
        dam_layers = []

        # 重力坝或拱坝
        dam_geometry = dam_profile.get('geometry', [])
        dam_type = dam_profile.get('dam_type', 'gravity')

        if dam_type == 'arch':
            # 拱坝3D模型
            arch_layer = {
                'id': 'arch_dam',
                'type': 'SolidPolygonLayer',
                'props': {
                    'data': [{
                        'polygons': dam_geometry,
                        'elevation': dam_profile.get('height', 100),
                        'fillColor': [150, 150, 150, 255]
                    }],
                    'extruded': True,
                    'pickable': True
                }
            }
            dam_layers.append(arch_layer)
        else:
            # 重力坝
            gravity_layer = {
                'id': 'gravity_dam',
                'type': 'PolygonLayer',
                'props': {
                    'data': dam_geometry,
                    'extruded': True,
                    'pickable': True
                }
            }
            dam_layers.append(gravity_layer)

        # 坝体内部结构（分区分层）
        if materials:
            internal_layer = {
                'id': 'dam_materials',
                'type': 'SolidPolygonLayer',
                'props': {
                    'data': self._create_internal_structure(dam_geometry, materials),
                    'extruded': True,
                    'pickable': True
                }
            }
            dam_layers.append(internal_layer)

        center_coords = dam_profile.get('center', [116.4074, 39.9042])

        return {
            'scene_type': 'dam_model',
            'initialViewState': {
                'longitude': center_coords[0],
                'latitude': center_coords[1],
                'zoom': 17,
                'pitch': 60,
                'bearing': 45
            },
            'layers': dam_layers,
            'model_info': {
                'dam_type': dam_type,
                'height': dam_profile.get('height'),
                'width': dam_profile.get('width'),
                'materials': materials
            }
        }

    def _create_watershed_scene(self, watershed_boundary: Dict[str, Any],
                              river_network: List[Dict],
                              elevation_data: TerrainData) -> Dict[str, Any]:
        """创建流域分析3D场景"""

        layers = []

        # 流域边界
        boundary_layer = {
            'id': 'watershed_boundary',
            'type': 'PolygonLayer',
            'props': {
                'data': [{
                    'polygon': watershed_boundary.get('coordinates', []),
                    'elevation': 0,
                    'fillColor': [100, 150, 100, 100],
                    'lineColor': [50, 100, 50]
                }],
                'extruded': False,
                'pickable': True
            }
        }
        layers.append(boundary_layer)

        # 河网
        river_layer = {
            'id': 'river_network',
            'type': 'PathLayer',
            'props': {
                'data': river_network,
                'getPath': 'path',
                'getColor': [0, 100, 200],
                'getWidth': 3
            }
        }
        layers.append(river_layer)

        # 地形
        terrain_layer = {
            'id': 'watershed_terrain',
            'type': 'TerrainLayer',
            'props': {
                'elevationData': elevation_data.elevation.tolist(),
                'bounds': elevation_data.bounds,
                'elevationScale': 1.5
            }
        }
        layers.append(terrain_layer)

        center_coords = watershed_boundary.get('center', [116.4074, 39.9042])

        return {
            'scene_type': 'watershed_analysis',
            'initialViewState': {
                'longitude': center_coords[0],
                'latitude': center_coords[1],
                'zoom': 11,
                'pitch': 40,
                'bearing': 0
            },
            'layers': layers,
            'analysis_results': {
                'area': watershed_boundary.get('area'),
                'river_density': len(river_network) / watershed_boundary.get('area', 1),
                'elevation_range': self._calculate_elevation_range(elevation_data)
            }
        }

    def _generate_contours(self, elevation: np.ndarray, bounds: Tuple[float, float, float, float],
                          interval: float = 10) -> List[Dict]:
        """生成等高线"""
        # 简化的等高线生成
        min_elev = np.min(elevation)
        max_elev = np.max(elevation)

        contours = []
        current_elev = np.ceil(min_elev / interval) * interval

        while current_elev <= max_elev:
            # 实际应用中应使用更复杂的等高线追踪算法
            contours.append({
                'elevation': current_elev,
                'path': [],  # 等高线路径坐标
                'color': [0, 0, 0]
            })
            current_elev += interval

        return contours

    def _create_internal_structure(self, dam_geometry: List, materials: Dict) -> List[Dict]:
        """创建大坝内部结构"""
        # 简化的内部结构表示
        internal_structure = []

        for zone, material in materials.items():
            internal_structure.append({
                'zone': zone,
                'material': material['type'],
                'strength': material['strength'],
                'color': material.get('color', [150, 150, 150])
            })

        return internal_structure

    def _calculate_elevation_range(self, terrain: TerrainData) -> Dict[str, float]:
        """计算高程范围"""
        return {
            'min': float(np.min(terrain.elevation)),
            'max': float(np.max(terrain.elevation)),
            'mean': float(np.mean(terrain.elevation)),
            'std': float(np.std(terrain.elevation))
        }

    def generate_3d_scene(self, scene_type: str, **kwargs) -> Dict[str, Any]:
        """
        生成3D场景

        Args:
            scene_type: 场景类型
            **kwargs: 场景参数

        Returns:
            3D场景配置
        """
        if scene_type not in self.scene_templates:
            raise ValueError(f"不支持的3D场景类型: {scene_type}. 可用类型: {list(self.scene_templates.keys())}")

        return self.scene_templates[scene_type](**kwargs)

    def get_scene_statistics(self, scene_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取场景统计信息"""
        layers = scene_config.get('layers', [])

        stats = {
            'total_layers': len(layers),
            'scene_type': scene_config.get('scene_type'),
            '3d_layers': 0,
            'interactive_layers': 0
        }

        for layer in layers:
            if layer.get('props', {}).get('extruded'):
                stats['3d_layers'] += 1
            if layer.get('props', {}).get('pickable'):
                stats['interactive_layers'] += 1

        return stats
