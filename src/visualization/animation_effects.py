"""
动态效果生成器
生成各种动态动画效果，如洪水演进、粒子效果、数据流等
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

@dataclass
class AnimationKeyframe:
    """动画关键帧"""
    timestamp: float
    properties: Dict[str, Any]

@dataclass
class Particle:
    """粒子"""
    position: List[float]
    velocity: List[float]
    size: float
    color: List[int]
    lifetime: float

class AnimationEffects:
    """动态效果生成器"""

    def __init__(self):
        self.animation_templates = {
            'flood_propagation': self._create_flood_propagation_animation,
            'discharge_particles': self._create_discharge_particles,
            'water_flow': self._create_water_flow_animation,
            'data_stream': self._create_data_stream_animation,
            'pulse_warning': self._create_pulse_warning_animation,
            'timeline_progress': self._create_timeline_animation
        }

    def _create_flood_propagation_animation(self, flood_data: List[Dict[str, Any]],
                                          duration: int = 10000) -> Dict[str, Any]:
        """创建洪水演进动画"""

        if not flood_data:
            raise ValueError("洪水数据不能为空")

        keyframes = []
        total_steps = len(flood_data)

        for idx, step in enumerate(flood_data):
            progress = idx / max(total_steps - 1, 1)

            keyframe = {
                'timestamp': progress * duration,
                'properties': {
                    'flood_extent': step.get('geometry', {}).get('coordinates', []),
                    'water_level': step.get('water_level', 0),
                    'water_depth': step.get('depth', 2),
                    'affected_area': step.get('area', 0),
                    'flow_velocity': step.get('velocity', 0),
                    'color': [0, 100 + int(progress * 155), 200, 150 + int(progress * 105)],
                    'opacity': 0.5 + progress * 0.5
                }
            }
            keyframes.append(keyframe)

        return {
            'animation_type': 'flood_propagation',
            'duration': duration,
            'easing': 'easeInOutCubic',
            'keyframes': keyframes,
            'layer_config': {
                'type': 'fill',
                'paint': {
                    'fill-color': ['get', 'color'],
                    'fill-opacity': ['get', 'opacity']
                }
            },
            'effects': {
                'show_timeline': True,
                'show_legend': True,
                'play_controls': True
            }
        }

    def _create_discharge_particles(self, discharge_positions: List[Dict],
                                  duration: int = 5000,
                                  intensity: float = 1.0) -> Dict[str, Any]:
        """创建泄洪粒子效果"""

        particles = []
        num_particles = min(int(100 * intensity), 500)  # 根据强度调整粒子数量

        for pos_data in discharge_positions:
            base_position = pos_data.get('position', [0, 0])

            for i in range(num_particles):
                # 随机偏移
                random_offset = [
                    (np.random.random() - 0.5) * 0.001,
                    (np.random.random() - 0.5) * 0.001
                ]

                particle = {
                    'id': f'particle_{pos_data.get("id", "unk")}_{i}',
                    'initial_position': [
                        base_position[0] + random_offset[0],
                        base_position[1] + random_offset[1]
                    ],
                    'velocity': [
                        (np.random.random() - 0.5) * 0.0005,
                        -abs(np.random.random() * 0.001)  # 向下运动
                    ],
                    'size': np.random.random() * 3 + 1,
                    'color': [0, 150 + np.random.randint(0, 105), 255, 200],
                    'lifetime': np.random.random() * 2000 + 1000,  # 1-3秒
                    'fade_out': True
                }
                particles.append(particle)

        keyframes = [
            {
                'timestamp': 0,
                'properties': {
                    'particle_count': len(particles),
                    'particles': particles
                }
            },
            {
                'timestamp': duration,
                'properties': {
                    'particle_count': 0,
                    'particles': []
                }
            }
        ]

        return {
            'animation_type': 'discharge_particles',
            'duration': duration,
            'easing': 'easeOutQuad',
            'keyframes': keyframes,
            'layer_config': {
                'type': 'circle',
                'paint': {
                    'circle-radius': ['get', 'size'],
                    'circle-color': ['get', 'color'],
                    'circle-opacity': 0.9,
                    'circle-blur': 0.5
                }
            },
            'physics': {
                'gravity': 0.0001,
                'wind': [0.0001, 0],
                'turbulence': 0.0002
            }
        }

    def _create_water_flow_animation(self, flow_paths: List[Dict],
                                   duration: int = 8000) -> Dict[str, Any]:
        """创建水流流动动画"""

        keyframes = []
        path_count = len(flow_paths)

        for idx, path in enumerate(flow_paths):
            # 每条路径有延迟开始，形成连续流动效果
            start_delay = (idx / max(path_count, 1)) * duration * 0.3

            coords = path.get('coordinates', [])
            if len(coords) < 2:
                continue

            # 创建流动的点
            keyframes.append({
                'timestamp': start_delay,
                'properties': {
                    'path_id': path.get('id', f'path_{idx}'),
                    'position': coords[0],
                    'progress': 0,
                    'flow_speed': path.get('velocity', 1.0),
                    'line_width': max(path.get('flow_rate', 1.0) / 10, 1),
                    'color': [0, 100, 200, 200]
                }
            })

            # 中间关键点
            segment_count = max(len(coords) - 1, 1)
            for i in range(1, segment_count):
                progress = i / segment_count
                keyframes.append({
                    'timestamp': start_delay + (progress * duration * 0.7),
                    'properties': {
                        'path_id': path.get('id', f'path_{idx}'),
                        'position': coords[i],
                        'progress': progress,
                        'flow_speed': path.get('velocity', 1.0),
                        'line_width': max(path.get('flow_rate', 1.0) / 10, 1),
                        'color': [0, 100 + int(progress * 100), 200, 200]
                    }
                })

            # 结束点
            keyframes.append({
                'timestamp': start_delay + (duration * 0.7),
                'properties': {
                    'path_id': path.get('id', f'path_{idx}'),
                    'position': coords[-1],
                    'progress': 1.0,
                    'flow_speed': path.get('velocity', 1.0),
                    'line_width': max(path.get('flow_rate', 1.0) / 10, 1),
                    'color': [0, 200, 255, 200]
                }
            })

        return {
            'animation_type': 'water_flow',
            'duration': duration,
            'easing': 'linear',
            'keyframes': sorted(keyframes, key=lambda k: k['timestamp']),
            'layer_config': {
                'type': 'symbol',
                'paint': {
                    'icon-opacity': 0.9,
                    'icon-color': ['get', 'color']
                }
            },
            'effects': {
                'show_trail': True,  # 显示尾迹
                'trail_length': 5,  # 尾迹长度
                'glow_effect': True
            }
        }

    def _create_data_stream_animation(self, data_points: List[Dict],
                                    duration: int = 5000) -> Dict[str, Any]:
        """创建数据流动画（用于实时数据可视化）"""

        keyframes = []
        point_count = len(data_points)

        for idx, point in enumerate(data_points):
            timestamp = (idx / max(point_count - 1, 1)) * duration

            keyframe = {
                'timestamp': timestamp,
                'properties': {
                    'data_id': point.get('id', f'data_{idx}'),
                    'position': point.get('position', [0, 0]),
                    'value': point.get('value', 0),
                    'size': min(max(point.get('value', 0) * 2, 5), 20),  # 根据值调整大小
                    'color': point.get('color', [255, 255, 0]),
                    'pulse': True,
                    'pulse_frequency': 1000  # 每秒闪烁一次
                }
            }
            keyframes.append(keyframe)

        return {
            'animation_type': 'data_stream',
            'duration': duration,
            'easing': 'easeInOutQuad',
            'keyframes': keyframes,
            'layer_config': {
                'type': 'circle',
                'paint': {
                    'circle-radius': ['get', 'size'],
                    'circle-color': ['get', 'color'],
                    'circle-opacity': ['interpolate', ['linear'], ['sin', ['*', ['get', 'timestamp'], 0.001]], -1, 0.3, 1, 1.0],
                    'circle-blur': 0.3
                }
            },
            'effects': {
                'show_value_labels': True,
                'fade_old_points': True,  # 旧数据点淡出
                'max_points_shown': 10
            }
        }

    def _create_pulse_warning_animation(self, warning_zones: List[Dict],
                                      duration: int = 3000) -> Dict[str, Any]:
        """创建脉冲预警动画"""

        keyframes = []

        for idx, zone in enumerate(warning_zones):
            severity = zone.get('severity', 'low')

            # 不同严重程度的脉冲参数
            pulse_config = {
                'low': {'color': [255, 255, 0], 'max_radius': 20, 'frequency': 0.5},
                'medium': {'color': [255, 165, 0], 'max_radius': 30, 'frequency': 1.0},
                'high': {'color': [255, 0, 0], 'max_radius': 40, 'frequency': 2.0},
                'critical': {'color': [255, 0, 255], 'max_radius': 50, 'frequency': 3.0}
            }

            config = pulse_config.get(severity, pulse_config['low'])

            # 脉冲动画：从小到大再到小
            half_duration = duration / 2

            keyframes.append({
                'timestamp': 0,
                'properties': {
                    'zone_id': zone.get('id', f'zone_{idx}'),
                    'center': zone.get('center', [0, 0]),
                    'radius': 0,
                    'color': config['color'],
                    'severity': severity,
                    'opacity': 0.8
                }
            })

            keyframes.append({
                'timestamp': half_duration,
                'properties': {
                    'zone_id': zone.get('id', f'zone_{idx}'),
                    'center': zone.get('center', [0, 0]),
                    'radius': config['max_radius'],
                    'color': config['color'],
                    'severity': severity,
                    'opacity': 0.4
                }
            })

            keyframes.append({
                'timestamp': duration,
                'properties': {
                    'zone_id': zone.get('id', f'zone_{idx}'),
                    'center': zone.get('center', [0, 0]),
                    'radius': 0,
                    'color': config['color'],
                    'severity': severity,
                    'opacity': 0.0
                }
            })

        return {
            'animation_type': 'pulse_warning',
            'duration': duration,
            'easing': 'easeInOutSine',
            'keyframes': keyframes,
            'layer_config': {
                'type': 'circle',
                'paint': {
                    'circle-radius': ['get', 'radius'],
                    'circle-color': ['get', 'color'],
                    'circle-opacity': ['get', 'opacity'],
                    'circle-blur': 0.8
                }
            },
            'effects': {
                'loop': True,
                'play_sound': True
            }
        }

    def _create_timeline_animation(self, events: List[Dict]) -> Dict[str, Any]:
        """创建时间轴进度动画"""

        if not events:
            raise ValueError("事件列表不能为空")

        # 按时间排序事件
        sorted_events = sorted(events, key=lambda e: e.get('timestamp', 0))

        start_time = sorted_events[0].get('timestamp', 0)
        end_time = sorted_events[-1].get('timestamp', 0)
        duration = end_time - start_time

        keyframes = []

        for idx, event in enumerate(sorted_events):
            event_time = event.get('timestamp', 0) - start_time

            keyframe = {
                'timestamp': (event_time / duration) * 10000,  # 标准化到10秒
                'properties': {
                    'event_id': event.get('id', f'event_{idx}'),
                    'position': event.get('position', [0, 0]),
                    'title': event.get('title', 'Event'),
                    'description': event.get('description', ''),
                    'progress': (event_time / duration) * 100,  # 百分比
                    'marker_size': 15,
                    'color': [255, 255, 0]
                }
            }
            keyframes.append(keyframe)

        return {
            'animation_type': 'timeline_progress',
            'duration': 10000,  # 固定10秒
            'easing': 'linear',
            'keyframes': keyframes,
            'layer_config': {
                'type': 'symbol',
                'paint': {
                    'icon-size': 2.0,
                    'icon-color': ['get', 'color'],
                    'text-field': ['get', 'title'],
                    'text-size': 12,
                    'text-anchor': 'top'
                }
            },
            'effects': {
                'show_progress_bar': True,
                'show_event_marks': True,
                'auto_advance': True
            }
        }

    def generate_animation(self, animation_type: str, **kwargs) -> Dict[str, Any]:
        """
        生成动画效果

        Args:
            animation_type: 动画类型
            **kwargs: 动画参数

        Returns:
            动画配置
        """
        if animation_type not in self.animation_templates:
            raise ValueError(f"不支持的动画类型: {animation_type}. 可用类型: {list(self.animation_templates.keys())}")

        return self.animation_templates[animation_type](**kwargs)

    def combine_animations(self, animations: List[Dict[str, Any]],
                         sync_mode: str = 'sequential') -> Dict[str, Any]:
        """
        组合多个动画

        Args:
            animations: 动画列表
            sync_mode: 同步模式 (sequential/parallel/synchronized)

        Returns:
            组合后的动画配置
        """

        combined_duration = 0
        combined_keyframes = []

        if sync_mode == 'sequential':
            # 顺序播放
            offset = 0
            for anim in animations:
                anim_duration = anim.get('duration', 0)

                for keyframe in anim.get('keyframes', []):
                    combined_keyframes.append({
                        'timestamp': keyframe['timestamp'] + offset,
                        'animation_id': id(anim),
                        'properties': keyframe['properties']
                    })

                offset += anim_duration
                combined_duration += anim_duration

        elif sync_mode == 'parallel':
            # 同时播放
            max_duration = max([anim.get('duration', 0) for anim in animations])
            combined_duration = max_duration

            for anim in animations:
                for keyframe in anim.get('keyframes', []):
                    combined_keyframes.append({
                        'timestamp': keyframe['timestamp'],
                        'animation_id': id(anim),
                        'properties': keyframe['properties']
                    })

        elif sync_mode == 'synchronized':
            # 同步到相同节奏
            max_duration = max([anim.get('duration', 0) for anim in animations])
            combined_duration = max_duration

            for anim in animations:
                scale_factor = max_duration / anim.get('duration', 1)

                for keyframe in anim.get('keyframes', []):
                    combined_keyframes.append({
                        'timestamp': keyframe['timestamp'] * scale_factor,
                        'animation_id': id(anim),
                        'properties': keyframe['properties']
                    })
        else:
            raise ValueError(f"不支持的同步模式: {sync_mode}")

        # 按时间排序
        combined_keyframes.sort(key=lambda k: k['timestamp'])

        return {
            'animation_type': 'combined',
            'sync_mode': sync_mode,
            'duration': combined_duration,
            'animations': animations,
            'keyframes': combined_keyframes,
            'effects': {
                'master_control': True,
                'individual_controls': False
            }
        }
