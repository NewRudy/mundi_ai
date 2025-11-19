/**
 * 事件路由
 * 提供事件发布和订阅的HTTP接口
 */

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..core.event_bus import (
    EventType, Event, publish_event, get_event_bus,
    subscribe_to_event, unsubscribe_from_event
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 数据模型

class PublishEventRequest(BaseModel):
    """发布事件请求"""
    event_type: str = Field(..., description="事件类型")
    payload: Dict[str, Any] = Field(..., description="事件负载")
    source: str = Field("api", description="事件源")
    correlation_id: str = Field(None, description="关联ID")
    reply_to: str = Field(None, description="回复队列")


class PublishEventResponse(BaseModel):
    """发布事件响应"""
    event_id: str
    event_type: str
    status: str
    timestamp: str


class SubscribeEventRequest(BaseModel):
    """订阅事件请求"""
    event_types: List[str] = Field(..., description="要订阅的事件类型列表")
    webhook_url: str = Field(None, description="Webhook URL（可选）")


class SubscribeEventResponse(BaseModel):
    """订阅事件响应"""
    subscription_id: str
    event_types: List[str]
    status: str
    webhook_url: str = None


class EventHistoryResponse(BaseModel):
    """事件历史响应"""
    events: List[Dict[str, Any]]
    total_count: int
    last_event_time: str


# WebSocket连接管理
class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.event_subscriptions: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket连接已建立: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            # 从所有订阅中移除
            for event_type, connections in self.event_subscriptions.items():
                if websocket in connections:
                    connections.remove(websocket)
        logger.info(f"🔌 WebSocket连接已断开: {websocket.client}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"❌ 发送个人消息失败: {e}")

    async def broadcast_event(self, event: Event):
        """广播事件给所有订阅的WebSocket连接"""
        event_type_str = event.type.value
        subscribed_connections = self.event_subscriptions.get(event_type_str, [])

        if subscribed_connections:
            message = {
                "type": "event",
                "event": {
                    "id": event.id,
                    "type": event.type.value,
                    "source": event.source,
                    "timestamp": event.timestamp.isoformat(),
                    "payload": event.payload,
                    "correlation_id": event.correlation_id
                }
            }

            # 广播给所有订阅的连接
            disconnected_connections = []
            for connection in subscribed_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"❌ 广播事件失败: {e}")
                    disconnected_connections.append(connection)

            # 移除断开的连接
            for connection in disconnected_connections:
                if connection in subscribed_connections:
                    subscribed_connections.remove(connection)

    def subscribe_to_event_type(self, event_type: str, websocket: WebSocket):
        """订阅特定事件类型"""
        if event_type not in self.event_subscriptions:
            self.event_subscriptions[event_type] = []
        if websocket not in self.event_subscriptions[event_type]:
            self.event_subscriptions[event_type].append(websocket)
            logger.info(f"👂 WebSocket订阅事件: {event_type}")

    def unsubscribe_from_event_type(self, event_type: str, websocket: WebSocket):
        """取消订阅特定事件类型"""
        if event_type in self.event_subscriptions:
            if websocket in self.event_subscriptions[event_type]:
                self.event_subscriptions[event_type].remove(websocket)
                logger.info(f"👋 WebSocket取消订阅事件: {event_type}")


# 全局连接管理器
connection_manager = ConnectionManager()


# 路由定义

@router.post("/publish", response_model=PublishEventResponse)
async def publish_event_endpoint(request: PublishEventRequest):
    """发布事件"""
    try:
        # 验证事件类型
        try:
            event_type = EventType(request.event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的事件类型: {request.event_type}")

        # 发布事件
        event_bus = get_event_bus()
        event_id = await event_bus.publish(
            event_type,
            request.payload,
            source=request.source,
            correlation_id=request.correlation_id,
            reply_to=request.reply_to
        )

        logger.info(f"📤 发布事件: {request.event_type} (ID: {event_id})")

        return PublishEventResponse(
            event_id=event_id,
            event_type=request.event_type,
            status="published",
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"❌ 发布事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"发布事件失败: {str(e)}")


@router.post("/subscribe", response_model=SubscribeEventResponse)
async def subscribe_to_events_endpoint(request: SubscribeEventRequest):
    """订阅事件"""
    try:
        # 验证事件类型
        valid_event_types = []
        invalid_event_types = []

        for event_type_str in request.event_types:
            try:
                event_type = EventType(event_type_str)
                valid_event_types.append(event_type)
            except ValueError:
                invalid_event_types.append(event_type_str)

        if invalid_event_types:
            raise HTTPException(
                status_code=400,
                detail=f"无效的事件类型: {', '.join(invalid_event_types)}"
            )

        # 生成订阅ID
        subscription_id = f"sub_{datetime.now().timestamp()}"

        # 注册事件处理器（这里只是返回订阅信息，实际处理在WebSocket或其他地方）
        logger.info(f"👂 订阅事件: {request.event_types}")

        return SubscribeEventResponse(
            subscription_id=subscription_id,
            event_types=request.event_types,
            status="subscribed",
            webhook_url=request.webhook_url
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 订阅事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"订阅失败: {str(e)}")


@router.get("/history")
async def get_event_history(
    event_type: str = None,
    limit: int = 100,
    offset: int = 0
):
    """获取事件历史（简化实现）"""
    try:
        # 这里应该实现真实的事件历史存储
        # 目前返回模拟数据
        mock_events = [
            {
                "id": f"event_{i}",
                "type": event_type or "kg:search_completed",
                "source": "kg-service",
                "timestamp": datetime.now().isoformat(),
                "payload": {"results": [f"result_{i}"]}
            }
            for i in range(min(limit, 10))
        ]

        return EventHistoryResponse(
            events=mock_events[offset:offset + limit],
            total_count=len(mock_events),
            last_event_time=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"❌ 获取事件历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点用于实时事件推送"""
    await connection_manager.connect(websocket)

    try:
        # 发送欢迎消息
        await connection_manager.send_personal_message({
            "type": "connection",
            "message": "已连接到KG事件总线",
            "timestamp": datetime.now().isoformat()
        }, websocket)

        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            # 处理不同类型的消息
            if data.get("type") == "subscribe":
                # 订阅事件
                event_types = data.get("event_types", [])
                for event_type in event_types:
                    connection_manager.subscribe_to_event_type(event_type, websocket)

                await connection_manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "event_types": event_types,
                    "timestamp": datetime.now().isoformat()
                }, websocket)

            elif data.get("type") == "unsubscribe":
                # 取消订阅事件
                event_types = data.get("event_types", [])
                for event_type in event_types:
                    connection_manager.unsubscribe_from_event_type(event_type, websocket)

                await connection_manager.send_personal_message({
                    "type": "unsubscription_confirmed",
                    "event_types": event_types,
                    "timestamp": datetime.now().isoformat()
                }, websocket)

            elif data.get("type") == "ping":
                # 心跳响应
                await connection_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, websocket)

            else:
                # 未知消息类型
                await connection_manager.send_personal_message({
                    "type": "error",
                    "message": f"未知消息类型: {data.get('type')}",
                    "timestamp": datetime.now().isoformat()
                }, websocket)

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info(f"🔌 WebSocket客户端断开连接: {websocket.client}")

    except Exception as e:
        logger.error(f"❌ WebSocket错误: {e}")
        connection_manager.disconnect(websocket)


# 事件监听器注册
async def register_event_listeners():
    """注册事件监听器"""

    async def hydro_scene_change_handler(event: Event):
        """处理水电场景变化事件"""
        logger.info(f"🌊 收到水电场景变化事件: {event.payload}")
        # 触发相关的KG分析
        # ... 具体的KG分析逻辑

    async def kg_search_request_handler(event: Event):
        """处理KG搜索请求事件"""
        logger.info(f"🔍 收到KG搜索请求事件: {event.payload}")
        # 执行搜索并发布结果
        # ... 具体的搜索逻辑

    # 注册处理器
    await subscribe_to_event(EventType.HYDRO_SCENE_CHANGED, hydro_scene_change_handler)
    await subscribe_to_event(EventType.KG_SEARCH_REQUEST, kg_search_request_handler)

    logger.info("✅ 事件监听器注册完成")


# 启动时注册事件监听器
@router.on_event("startup")
async def startup_event_handler():
    """启动事件处理"""
    await register_event_listeners()
    logger.info("🚀 事件路由启动完成")


@router.on_event("shutdown")
async def shutdown_event_handler():
    """关闭事件处理"""
    logger.info("🛑 事件路由关闭完成")"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py"} "file_path":"E:\work_code\mundi.ai\kg-service\src\routes\event_routes.py