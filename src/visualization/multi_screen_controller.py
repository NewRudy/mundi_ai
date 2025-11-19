"""
多屏联动控制器
管理多屏监控系统，支持实时监控墙和协同控制
"""

from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import uuid

@dataclass
class ScreenConfig:
    """屏幕配置"""
    screen_id: str
    name: str
    width: int
    height: int
    position_x: int = 0
    position_y: int = 0
    resolution: str = "1920x1080"
    display_mode: str = "primary"  # primary/secondary/collaborative
    status: str = "online"
    last_heartbeat: datetime = field(default_factory=datetime.now)

@dataclass
class DisplayLayout:
    """显示布局"""
    layout_id: str
    name: str
    screen_count: int
    layout_type: str  # grid/horizontal/vertical/custom
    screen_positions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

class MultiScreenController:
    """多屏联动控制器"""

    def __init__(self):
        self.screens: Dict[str, ScreenConfig] = {}
        self.layouts: Dict[str, DisplayLayout] = {}
        self.active_layout: Optional[str] = None
        self.callbacks: Dict[str, List[Callable]] = {}
        self.display_sync_data: Dict[str, Any] = {}
        self.background_tasks: List[asyncio.Task] = []

        # 注册事件回调
        self.callbacks = {
            'screen_online': [],
            'screen_offline': [],
            'layout_changed': [],
            'sync_mode_changed': []
        }

    def register_screen(self, screen_config: ScreenConfig):
        """注册屏幕"""
        self.screens[screen_config.screen_id] = screen_config
        self._trigger_callback('screen_online', screen_config)

    def unregister_screen(self, screen_id: str):
        """注销屏幕"""
        if screen_id in self.screens:
            screen = self.screens.pop(screen_id)
            self._trigger_callback('screen_offline', screen)

    def update_screen_status(self, screen_id: str, status: str):
        """更新屏幕状态"""
        if screen_id in self.screens:
            self.screens[screen_id].status = status
            self.screens[screen_id].last_heartbeat = datetime.now()

    def get_online_screens(self) -> List[ScreenConfig]:
        """获取在线屏幕"""
        return [screen for screen in self.screens.values() if screen.status == "online"]

    def create_layout(self, layout_config: Dict[str, Any]) -> str:
        """
        创建显示布局

        Args:
            layout_config: 布局配置

                  Returns:
            布局ID
        """
        layout_id = str(uuid.uuid4())

        layout = DisplayLayout(
            layout_id=layout_id,
            name=layout_config.get('name', f'Layout {len(self.layouts) + 1}'),
            screen_count=layout_config.get('screen_count', 1),
            layout_type=layout_config.get('layout_type', 'grid'),
            screen_positions=layout_config.get('screen_positions', [])
        )

        self.layouts[layout_id] = layout
        return layout_id

    def activate_layout(self, layout_id: str):
        """激活布局"""
        if layout_id in self.layouts:
            self.active_layout = layout_id
            self._trigger_callback('layout_changed', self.layouts[layout_id])

    def get_active_layout(self) -> Optional[DisplayLayout]:
        """获取当前激活的布局"""
        if self.active_layout and self.active_layout in self.layouts:
            return self.layouts[self.active_layout]
        return None

    def create_monitoring_wall(self, screen_ids: List[str],
                             scene_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        创建监控墙布局

        Args:
            screen_ids: 屏幕ID列表
            scene_configs: 每个屏幕的场景配置

        Returns:
            监控墙配置
        """

        if len(screen_ids) != len(scene_configs):
            raise ValueError("屏幕数量和场景配置数量不匹配")

        wall_config = {
            'wall_id': str(uuid.uuid4()),
            'screen_count': len(screen_ids),
            'screens': {}
        }

        for idx, (screen_id, scene_config) in enumerate(zip(screen_ids, scene_configs)):
            wall_config['screens'][screen_id] = {
                'position': idx,
                'scene_config': scene_config,
                'screen_info': self.screens.get(screen_id).__dict__ if screen_id in self.screens else None
            }

        return wall_config

    def start_realtime_sync(self, sync_interval: float = 1.0):
        """
          启动实时同步

        Args:
            sync_interval: 同步间隔（秒）
        """

        async def _sync_worker():
            while True:
                await self._synchronize_screens()
                await asyncio.sleep(sync_interval)

        task = asyncio.create_task(_sync_worker())
        self.background_tasks.append(task)

    async def _synchronize_screens(self):
        """同步屏幕数据"""
        online_screens = self.get_online_screens()

        if not online_screens:
            return

            # 同步时间基准
        sync_timestamp = datetime.now().isoformat()
        self.display_sync_data['last_sync'] = sync_timestamp

        # 分发同步数据到各屏幕
        for screen in online_screens:
            await self._send_sync_data(screen.screen_id, self.display_sync_data)

    async def _send_sync_data(self, screen_id: str, data: Dict[str, Any]):
        """发送同步数据到屏幕"""
        # 在实际实现中，这里会通过WebSocket或HTTP发送数据
        # 这里仅保存到内部状态
        pass

    def broadcast_update(self, update_data: Dict[str, Any]):
        """
        广播更新到所有屏幕

        Args:
            update_data: 更新数据
        """
        self.display_sync_data.update(update_data)

        for screen in self.get_online_screens():
            asyncio.create_task(self._send_sync_data(screen.screen_id, update_data))

    def set_sync_mode(self, mode: str, master_screen: Optional[str] = None):
        """
          设置同步模式

        Args:
            mode: 同步模式 (independent/synced/master-slave)
            master_screen: 主屏幕ID（master-slave模式）
        """

        sync_config = {
            'mode': mode,
            'master_screen': master_screen,
            'updated_at': datetime.now().isoformat()
        }

        self.display_sync_data['sync_mode'] = sync_config
        self._trigger_callback('sync_mode_changed', sync_config)

    def get_sync_mode(self) -> Dict[str, Any]:
        """获取同步模式"""
        return self.display_sync_data.get('sync_mode', {'mode': 'independent'})

    def share_view_state(self, screen_id: str, view_state: Dict[str, Any]):
        """
        分享视图状态

        Args:
            screen_id: 源屏幕ID
            view_state: 视图状态
        """
        sync_mode = self.get_sync_mode()

        if sync_mode['mode'] == 'synced':
            # 同步模式下，所有屏幕共享相同视图
            for screen in self.get_online_screens():
                if screen.screen_id != screen_id:
                    asyncio.create_task(self._send_view_state(screen.screen_id, view_state))

        elif sync_mode['mode'] == 'master-slave':
            # 主从模式下，主屏幕控制从屏幕
            if sync_mode.get('master_screen') == screen_id:
                for screen in self.get_online_screens():
                    if screen.screen_id != screen_id:
                        asyncio.create_task(self._send_view_state(screen.screen_id, view_state))

    async def _send_view_state(self, screen_id: str, view_state: Dict[str, Any]):
        """发送视图状态"""
        # 实际实现中通过WebSocket发送
        pass

    def create_scene_sequence(self, sequence_config: List[Dict[str, Any]]) -> str:
        """
        创建场景序列（自动轮播）

        Args:
            sequence_config: 序列配置

        Returns:
            序列ID
        """
        sequence_id = str(uuid.uuid4())

        sequence = {
            'sequence_id': sequence_id,
            'scenes': sequence_config,
            'duration': sum([scene.get('duration', 10) for scene in sequence_config]),
            'loop': True
        }

        self.display_sync_data[f'sequence_{sequence_id}'] = sequence
        return sequence_id

    def start_sequence(self, sequence_id: str):
        """启动场景序列"""

        async def _sequence_player():
            sequence = self.display_sync_data.get(f'sequence_{sequence_id}')
            if not sequence:
                return

            scenes = sequence.get('scenes', [])

            while True:
                for scene in scenes:
                    # 切换到场景
                    await self._switch_to_scene(scene)

                    # 等待场景持续时间
                    duration = scene.get('duration', 10)
                    await asyncio.sleep(duration)

                if not sequence.get('loop', True):
                    break

        task = asyncio.create_task(_sequence_player())
        self.background_tasks.append(task)

    async def _switch_to_scene(self, scene_config: Dict[str, Any]):
        """切换到指定场景"""
        scene_data = {
            'action': 'switch_scene',
            'scene_config': scene_config,
            'timestamp': datetime.now().isoformat()
        }

        self.broadcast_update(scene_data)

    def pause_all_screens(self):
        """暂停所有屏幕"""
        pause_data = {
            'action': 'pause',
            'paused_at': datetime.now().isoformat()
        }

        self.broadcast_update(pause_data)

    def resume_all_screens(self):
        """恢复所有屏幕"""
        resume_data = {
            'action': 'resume',
            'resumed_at': datetime.now().isoformat()
        }

        self.broadcast_update(resume_data)

    def stop_all_screens(self):
        """停止所有屏幕"""
        stop_data = {
            'action': 'stop',
            'stopped_at': datetime.now().isoformat()
        }

        self.broadcast_update(stop_data)

        # 取消后台任务
        for task in self.background_tasks:
            task.cancel()

        self.background_tasks.clear()

    def register_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, data: Any):
        """触发回调"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"回调执行失败: {e}")

    def create_control_panel(self) -> Dict[str, Any]:
        """创建控制面板配置"""

        control_panel = {
            'panel_id': str(uuid.uuid4()),
            'screens': {},
            'sync_mode': self.get_sync_mode(),
            'active_layout': self.active_layout,
            'controls': {
                'play_pause': True,
                'stop': True,
                'sync_mode': True,
                'layout_switch': True,
                'scene_sequence': True
            },
            'status_indicators': {
                'screen_status': True,
                'connection_status': True,
                'sync_status': True
            }
        }

        for screen in self.get_online_screens():
            control_panel['screens'][screen.screen_id] = {
                'name': screen.name,
                'status': screen.status,
                'display_mode': screen.display_mode,
                'resolution': screen.resolution,
                'position': [screen.position_x, screen.position_y]
            }

        return control_panel

    def get_health_status(self) -> Dict[str, Any]:
        """获取系统健康状态"""

        online_screens = self.get_online_screens()
        total_screens = len(self.screens)

        health_status = {
            'overall_status': 'healthy' if len(online_screens) == total_screens else 'degraded',
            'total_screens': total_screens,
            'online_screens': len(online_screens),
            'offline_screens': total_screens - len(online_screens),
            'active_layout': self.active_layout,
            'sync_mode': self.get_sync_mode().get('mode', 'unknown'),
            'last_sync': self.display_sync_data.get('last_sync', 'never'),
            'background_tasks': len(self.background_tasks),
            'uptime': 'Active'
        }

        return health_status
