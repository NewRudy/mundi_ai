/**
 * 事件总线实现
 * 基于Redis的发布-订阅模式，实现松耦合通信
 */

import json
import logging
import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import redis.asyncio as redis
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型定义"""
    # Hydro场景事件
    HYDRO_SCENE_CHANGED = "hydro:scene_changed"
    HYDRO_DATA_UPDATED = "hydro:data_updated"
    HYDRO_ALERT_TRIGGERED = "hydro:alert_triggered"

    # KG查询事件
    KG_SEARCH_REQUEST = "kg:search_request"
    KG_SEARCH_COMPLETED = "kg:search_completed"
    KG_ANALYSIS_REQUEST = "kg:analysis_request"
    KG_ANALYSIS_COMPLETED = "kg:analysis_completed"

    # 空间分析事件
    SPATIAL_ANALYSIS_REQUEST = "spatial:analysis_request"
    SPATIAL_ANALYSIS_COMPLETED = "spatial:analysis_completed"

    # 系统事件
    SERVICE_HEALTH_CHECK = "system:health_check"
    SERVICE_ERROR = "system:error"


@dataclass
class Event:
    """事件数据结构"""
    id: str
    type: EventType
    source: str
    timestamp: datetime
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None


class EventBus:
    """事件总线实现"""

    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 0):
        self.redis_url = redis_url
        self.db = db
        self.redis_client: Optional[redis.Redis] = None
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.running = False
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """连接到Redis"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                db=self.db,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                retry_on_timeout=True,
                max_connections=20
            )

            # 测试连接
            await self.redis_client.ping()
            logger.info(f"✅ 事件总线连接到Redis: {self.redis_url}")

            # 启动事件监听器
            asyncio.create_task(self._event_listener())
            self.running = True

        except Exception as e:
            logger.error(f"❌ 事件总线连接失败: {e}")
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        self.running = False
        if self.redis_client:
            await self.redis_client.close()
            logger.info("🛑 事件总线连接已关闭")

    async def publish(self, event_type: EventType, payload: Dict[str, Any],
                     source: str = "unknown", correlation_id: Optional[str] = None,
                     reply_to: Optional[str] = None) -> str:
        """发布事件"""
        if not self.redis_client:
            raise RuntimeError("事件总线未连接")

        event = Event(
            id=self._generate_event_id(),
            type=event_type,
            source=source,
            timestamp=datetime.now(),
            payload=payload,
            correlation_id=correlation_id,
            reply_to=reply_to
        )

        try:
            # 序列化事件
            event_data = self._serialize_event(event)

            # 发布到Redis频道
            channel = f"event:{event_type.value}"
            await self.redis_client.publish(channel, event_data)

            logger.info(f"📤 发布事件: {event_type.value} (ID: {event.id})")
            return event.id

        except Exception as e:
            logger.error(f"❌ 发布事件失败: {e}")
            raise

    async def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """订阅事件"""
        async with self._lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(handler)
            logger.info(f"👂 订阅事件: {event_type.value}")

    async def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        """取消订阅"""
        async with self._lock:
            if event_type in self.subscribers:
                self.subscribers[event_type].remove(handler)
                logger.info(f"👋 取消订阅: {event_type.value}")

    async def request_reply(self, request_type: EventType, request_payload: Dict[str, Any],
                           reply_type: EventType, timeout: float = 30.0) -> Optional[Event]:
        """请求-回复模式"""
        correlation_id = self._generate_event_id()
        reply_queue = f"reply:{correlation_id}"

        # 设置回复监听器
        reply_future = asyncio.Future()

        async def reply_handler(event: Event):
            if event.correlation_id == correlation_id:
                reply_future.set_result(event)

        await self.subscribe(reply_type, reply_handler)

        try:
            # 发送请求
            await self.publish(
                request_type,
                request_payload,
                correlation_id=correlation_id,
                reply_to=reply_queue
            )

            # 等待回复
            reply_event = await asyncio.wait_for(reply_future, timeout=timeout)
            return reply_event

        except asyncio.TimeoutError:
            logger.warning(f"⏰ 请求超时: {request_type.value}")
            return None
        finally:
            await self.unsubscribe(reply_type, reply_handler)

    async def broadcast(self, event_type: EventType, payload: Dict[str, Any],
                       source: str = "unknown") -> None:
        """广播事件到所有订阅者"""
        await self.publish(event_type, payload, source)

    # 私有方法
    async def _event_listener(self) -> None:
        """事件监听器"""
        logger.info("🎧 启动事件监听器...")

        while self.running:
            try:
                # 订阅所有事件频道
                channels = [f"event:{et.value}" for et in EventType]

                async with self.redis_client.pubsub() as pubsub:
                    await pubsub.subscribe(*channels)

                    async for message in pubsub.listen():
                        if message["type"] == "message":
                            await self._handle_message(message)

            except redis.ConnectionError as e:
                logger.error(f"🔌 事件监听器连接错误: {e}")
                await asyncio.sleep(5)  # 重连延迟
            except Exception as e:
                logger.error(f"❌ 事件监听器错误: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """处理消息"""
        try:
            # 反序列化事件
            event_data = message["data"]
            event = self._deserialize_event(event_data)

            logger.debug(f"📨 收到事件: {event.type.value} (ID: {event.id})")

            # 查找并调用处理器
            if event.type in self.subscribers:
                for handler in self.subscribers[event.type]:
                    try:
                        # 异步调用处理器
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event)
                        else:
                            # 同步处理器在executor中运行
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(None, handler, event)
                    except Exception as e:
                        logger.error(f"❌ 事件处理器错误: {e}")

        except Exception as e:
            logger.error(f"❌ 消息处理错误: {e}")

    def _serialize_event(self, event: Event) -> str:
        """序列化事件"""
        return json.dumps({
            "id": event.id,
            "type": event.type.value,
            "source": event.source,
            "timestamp": event.timestamp.isoformat(),
            "payload": event.payload,
            "correlation_id": event.correlation_id,
            "reply_to": event.reply_to
        })

    def _deserialize_event(self, data: str) -> Event:
        """反序列化事件"""
        event_data = json.loads(data)
        return Event(
            id=event_data["id"],
            type=EventType(event_data["type"]),
            source=event_data["source"],
            timestamp=datetime.fromisoformat(event_data["timestamp"]),
            payload=event_data["payload"],
            correlation_id=event_data.get("correlation_id"),
            reply_to=event_data.get("reply_to")
        )

    def _generate_event_id(self) -> str:
        """生成事件ID"""
        import uuid
        return str(uuid.uuid4())


# 全局事件总线实例
_event_bus: Optional[EventBus] = None


async def init_event_bus(redis_url: str = "redis://localhost:6379", db: int = 0) -> EventBus:
    """初始化全局事件总线"""
    global _event_bus
    _event_bus = EventBus(redis_url, db)
    await _event_bus.connect()
    return _event_bus


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    if _event_bus is None:
        raise RuntimeError("事件总线未初始化")
    return _event_bus


async def check_event_bus_connection() -> bool:
    """检查事件总线连接状态"""
    try:
        if _event_bus and _event_bus.redis_client:
            await _event_bus.redis_client.ping()
            return True
        return False
    except Exception:
        return False


async def close_event_bus() -> None:
    """关闭事件总线"""
    global _event_bus
    if _event_bus:
        await _event_bus.disconnect()
        _event_bus = None


# 便捷函数
async def publish_event(event_type: EventType, payload: Dict[str, Any], **kwargs) -> str:
    """发布事件的便捷函数"""
    bus = get_event_bus()
    return await bus.publish(event_type, payload, **kwargs)


async def subscribe_to_event(event_type: EventType, handler: Callable[[Event], None]) -> None:
    """订阅事件的便捷函数"""
    bus = get_event_bus()
    await bus.subscribe(event_type, handler)