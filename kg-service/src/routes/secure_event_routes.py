/**
 * 安全事件路由
 * 提供带认证和验证的事件发布和订阅接口
 */

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Header
from pydantic import BaseModel, Field, validator

from ..core.event_bus import (
    EventType, Event, publish_event, get_event_bus,
    subscribe_to_event, unsubscribe_from_event
)
from ..core.security import (
    validate_search_query, validate_spatial_request,
    validate_node_types, SanitizedEvent, create_correlation_id,
    check_rate_limit, verify_token, TokenData
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 认证依赖项
async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[TokenData]:
    """获取当前用户"""
    if not authorization:
        return None

    try:
        # 提取Bearer token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            return verify_token(token)
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")

    return None

# 数据模型

class SecurePublishEventRequest(BaseModel):
    """安全发布事件请求"""
    event_type: str = Field(..., description="事件类型")
    payload: Dict[str, Any] = Field(..., description="事件负载")
    source: str = Field("api", description="事件源")
    correlation_id: Optional[str] = Field(None, description="关联ID")
    reply_to: Optional[str] = Field(None, description="回复队列")

    @validator('event_type')
    def validate_event_type(cls, v):
        allowed_types = [
            "hydro:scene_changed", "hydro:data_updated", "hydro:alert_triggered",
            "hydro:viewport_changed", "kg:search_request", "kg:search_completed",
            "kg:analysis_request", "kg:analysis_completed", "spatial:analysis_request",
            "spatial:analysis_completed", "system:connected", "system:disconnected",
            "system:error", "auth:request", "auth:success", "auth:failed", "auth:required"
        ]
        if v not in allowed_types:
            raise ValueError(f"Event type {v} is not allowed")
        return v

    @validator('source')
    def validate_source(cls, v):
        if not v or len(v) < 3 or len(v) > 32:
            raise ValueError("Source must be between 3 and 32 characters")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Source can only contain alphanumeric characters, underscores and hyphens")
        return v

    @validator('payload')
    def validate_payload(cls, v):
        # 限制payload大小
        payload_str = json.dumps(v)
        if len(payload_str) > 1024 * 1024:  # 1MB
            raise ValueError("Payload too large")
        return v

class SecurePublishEventResponse(BaseModel):
    """安全发布事件响应"""
    event_id: str
    event_type: str
    status: str
    timestamp: str
    user_id: Optional[str] = None

class SecureKGSearchRequest(BaseModel):
    """安全KG搜索请求"""
    query: str = Field(..., description="搜索查询")
    limit: int = Field(50, ge=1, le=1000, description="结果数量限制")
    node_types: Optional[List[str]] = Field(None, description="节点类型过滤")
    include_relationships: bool = Field(True, description="是否包含关系")

    @validator('query')
    def validate_query(cls, v):
        return validate_search_query(v)

    @validator('node_types')
    def validate_node_types(cls, v):
        if v is not None:
            return validate_node_types(v)
        return v

class SecureSpatialAnalysisRequest(BaseModel):
    """安全空间分析请求"""
    west: float = Field(..., description="西边界", ge=-180, le=180)
    south: float = Field(..., description="南边界", ge=-90, le=90)
    east: float = Field(..., description="东边界", ge=-180, le=180)
    north: float = Field(..., description="北边界", ge=-90, le=90)
    analysis_type: str = Field("hydro_monitoring", description="分析类型")
    max_distance_km: float = Field(10.0, ge=0.1, le=50.0, description="最大分析距离(km)")

    @validator('west', 'south', 'east', 'north')
    def validate_coordinates(cls, v, values):
        return v

    @validator('analysis_type')
    def validate_analysis_type(cls, v):
        allowed_types = ["hydro_monitoring", "flood_risk", "spatial_relations"]
        if v not in allowed_types:
            raise ValueError(f"Analysis type {v} is not allowed")
        return v

    @validator('max_distance_km')
    def validate_distance(cls, v):
        if v < 0.1 or v > 50.0:
            raise ValueError("Distance must be between 0.1 and 50.0 km")
        return v

    def validate_bounds(self):
        """验证边界逻辑"""
        if self.south >= self.north:
            raise ValueError("South boundary must be less than north boundary")
        if self.west >= self.east:
            raise ValueError("West boundary must be less than east boundary")

        # 检查面积限制 (约10000平方公里)
        area = (self.east - self.west) * (self.north - self.south)
        if area > 100:  # 约100度平方
            raise ValueError("Analysis area too large")

class WebSocketAuthRequest(BaseModel):
    """WebSocket认证请求"""
    token: str = Field(..., description="认证令牌")
    client_id: str = Field(..., description="客户端ID")

    @validator('token')
    def validate_token(cls, v):
        if not v or len(v) < 10:
            raise ValueError("Invalid token format")
        return v

    @validator('client_id')
    def validate_client_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]{8,64}$', v):
            raise ValueError("Invalid client ID format")
        return v

# WebSocket连接管理
class SecureConnectionManager:
    """安全的WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}  # client_id -> websocket
        self.authenticated_connections: Dict[str, TokenData] = {}  # client_id -> token_data
        self.event_subscriptions: Dict[str, List[str]] = {}  # event_type -> client_ids
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}  # client_id -> metadata

    async def authenticate_connection(
        self,
        websocket: WebSocket,
        auth_request: WebSocketAuthRequest
    ) -> Optional[TokenData]:
        """认证WebSocket连接"""
        try:
            # 验证请求格式
            if not auth_request.token or not auth_request.client_id:
                await websocket.close(code=4401, reason="Missing authentication data")
                return None

            # 验证令牌
            token_data = verify_token(auth_request.token)
            if not token_data:
                await websocket.close(code=4401, reason="Invalid token")
                return None

            # 检查权限
            required_permissions = ["websocket.connect", "events.subscribe", "events.publish"]
            for permission in required_permissions:
                if permission not in token_data.permissions:
                    await websocket.close(code=4403, reason="Insufficient permissions")
                    return None

            # 检查速率限制
            if not check_rate_limit("websocket_auth", auth_request.client_id):
                await websocket.close(code=4408, reason="Rate limit exceeded")
                return None

            logger.info(f"WebSocket authenticated for user {token_data.username}")
            return token_data

        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            await websocket.close(code=4400, reason="Authentication error")
            return None

    async def connect(self, websocket: WebSocket, client_id: str, token_data: Optional[TokenData] = None):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

        if token_data:
            self.authenticated_connections[client_id] = token_data

        self.connection_metadata[client_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "user_id": token_data.user_id if token_data else None,
            "username": token_data.username if token_data else None
        }

        logger.info(f"🔌 WebSocket连接已建立: {client_id}")

    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

            if client_id in self.authenticated_connections:
                del self.authenticated_connections[client_id]

            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]

            # 从所有订阅中移除
            for event_type, client_ids in self.event_subscriptions.items():
                if client_id in client_ids:
                    client_ids.remove(client_id)

            logger.info(f"🔌 WebSocket连接已断开: {client_id}")

    async def send_personal_message(self, message: Dict[str, Any], client_id: str):
        """发送个人消息"""
        websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"❌ 发送个人消息失败: {e}")
                self.disconnect(client_id)

    async def broadcast_event(self, event: Event, exclude_client_id: Optional[str] = None):
        """广播事件给所有订阅的WebSocket连接"""
        event_type_str = event.type.value
        subscribed_client_ids = self.event_subscriptions.get(event_type_str, [])

        if subscribed_client_ids:
            message = {
                "type": "event",
                "event": {
                    "id": event.id,
                    "type": event.type.value,
                    "source": event.source,
                    "timestamp": event.timestamp.isoformat(),
                    "payload": event.payload,
                    "correlation_id": event.correlation_id,
                    "user_id": getattr(event, 'user_id', None)
                }
            }

            # 广播给所有订阅的连接
            disconnected_clients = []
            for client_id in subscribed_client_ids:
                if client_id == exclude_client_id:
                    continue

                websocket = self.active_connections.get(client_id)
                if websocket:
                    try:
                        await websocket.send_json(message)
                    except Exception as e:
                        logger.error(f"❌ 广播事件失败: {e}")
                        disconnected_clients.append(client_id)

            # 移除断开的连接
            for client_id in disconnected_clients:
                self.disconnect(client_id)

    def subscribe_to_event_type(self, event_type: str, client_id: str):
        """订阅特定事件类型"""
        if event_type not in self.event_subscriptions:
            self.event_subscriptions[event_type] = []

        if client_id not in self.event_subscriptions[event_type]:
            self.event_subscriptions[event_type].append(client_id)
            logger.info(f"👂 WebSocket订阅事件: {event_type} for client {client_id}")

    def unsubscribe_from_event_type(self, event_type: str, client_id: str):
        """取消订阅特定事件类型"""
        if event_type in self.event_subscriptions:
            if client_id in self.event_subscriptions[event_type]:
                self.event_subscriptions[event_type].remove(client_id)
                logger.info(f"👋 WebSocket取消订阅事件: {event_type} for client {client_id}")

    def is_authenticated(self, client_id: str) -> bool:
        """检查连接是否已认证"""
        return client_id in self.authenticated_connections

    def get_user_data(self, client_id: str) -> Optional[TokenData]:
        """获取用户数据"""
        return self.authenticated_connections.get(client_id)

# 全局连接管理器
secure_connection_manager = SecureConnectionManager()

# 路由定义

@router.post("/publish", response_model=SecurePublishEventResponse)
async def publish_secure_event(
    request: SecurePublishEventRequest,
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    """安全发布事件"""
    try:
        # 检查速率限制
        client_id = current_user.user_id if current_user else "anonymous"
        if not check_rate_limit("events", client_id):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # 验证事件类型
        try:
            event_type = EventType(request.event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {request.event_type}")

        # 检查权限
        if current_user:
            required_permission = f"events.{request.event_type}.publish"
            if required_permission not in current_user.permissions and "*" not in current_user.permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions")

        # 发布事件
        event_bus = get_event_bus()
        event_id = await event_bus.publish(
            event_type,
            request.payload,
            source=request.source,
            correlation_id=request.correlation_id,
            reply_to=request.reply_to
        )

        logger.info(f"📤 发布安全事件: {request.event_type} (ID: {event_id}) by {client_id}")

        return SecurePublishEventResponse(
            event_id=event_id,
            event_type=request.event_type,
            status="published",
            timestamp=datetime.now().isoformat(),
            user_id=current_user.user_id if current_user else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 发布安全事件失败: {e}")
        raise HTTPException(status_code=500, detail=f"发布事件失败: {str(e)}")

@router.post("/search", response_model=Dict[str, Any])
async def secure_kg_search(
    request: SecureKGSearchRequest,
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    """安全KG搜索"""
    try:
        # 检查速率限制
        client_id = current_user.user_id if current_user else "anonymous"
        if not check_rate_limit("search", client_id):
            raise HTTPException(status_code=429, detail="Search rate limit exceeded")

        # 检查权限
        if current_user:
            if "kg.search" not in current_user.permissions and "*" not in current_user.permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions for search")

        # 执行搜索逻辑
        # ... 这里应该调用实际的KG搜索服务

        results = []  # 模拟结果

        logger.info(f"🔍 KG安全搜索: {request.query} by {client_id}")

        return {
            "request_id": f"search_{datetime.now().timestamp()}",
            "results": results,
            "total_count": len(results),
            "query": request.query,
            "user_id": current_user.user_id if current_user else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ KG安全搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.post("/spatial-analysis", response_model=Dict[str, Any])
async def secure_spatial_analysis(
    request: SecureSpatialAnalysisRequest,
    current_user: Optional[TokenData] = Depends(get_current_user)
):
    """安全空间分析"""
    try:
        # 验证边界逻辑
        request.validate_bounds()

        # 检查速率限制
        client_id = current_user.user_id if current_user else "anonymous"
        if not check_rate_limit("analysis", client_id):
            raise HTTPException(status_code=429, detail="Analysis rate limit exceeded")

        # 检查权限
        if current_user:
            if "spatial.analysis" not in current_user.permissions and "*" not in current_user.permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions for spatial analysis")

        # 执行分析逻辑
        # ... 这里应该调用实际的空间分析服务

        results = []  # 模拟结果

        logger.info(f"🌍 安全空间分析: {request.analysis_type} by {client_id}")

        return {
            "request_id": f"spatial_{datetime.now().timestamp()}",
            "results": results,
            "bounds": {
                "west": request.west,
                "south": request.south,
                "east": request.east,
                "north": request.north
            },
            "user_id": current_user.user_id if current_user else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 安全空间分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@router.websocket("/ws")
async def secure_websocket_endpoint(websocket: WebSocket):
    """安全WebSocket端点用于实时事件推送"""
    client_id = None
    token_data = None

    try:
        # 等待认证消息
        auth_data = await websocket.receive_json()

        if auth_data.get("type") != "auth_request":
            await websocket.close(code=4401, reason="First message must be authentication")
            return

        # 解析认证请求
        try:
            auth_request = WebSocketAuthRequest(**auth_data)
        except Exception as e:
            await websocket.close(code=4400, reason=f"Invalid authentication format: {e}")
            return

        # 认证连接
        client_id = auth_request.client_id
        token_data = await secure_connection_manager.authenticate_connection(websocket, auth_request)

        if not token_data:
            return  # 连接已被关闭

        # 接受连接
        await secure_connection_manager.connect(websocket, client_id, token_data)

        # 发送认证成功消息
        await secure_connection_manager.send_personal_message({
            "type": "auth_success",
            "token_data": {
                "user_id": token_data.user_id,
                "username": token_data.username,
                "permissions": token_data.permissions
            },
            "timestamp": datetime.now().isoformat()
        }, client_id)

        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            # 检查认证状态
            if not secure_connection_manager.is_authenticated(client_id):
                await websocket.close(code=4401, reason="Not authenticated")
                break

            # 处理不同类型的消息
            message_type = data.get("type")

            if message_type == "subscribe":
                # 订阅事件
                event_types = data.get("event_types", [])
                user_permissions = token_data.permissions if token_data else []

                for event_type in event_types:
                    # 检查权限
                    required_permission = f"events.{event_type}.subscribe"
                    if required_permission in user_permissions or "*" in user_permissions:
                        secure_connection_manager.subscribe_to_event_type(event_type, client_id)
                    else:
                        await secure_connection_manager.send_personal_message({
                            "type": "error",
                            "message": f"No permission to subscribe to {event_type}",
                            "timestamp": datetime.now().isoformat()
                        }, client_id)

                await secure_connection_manager.send_personal_message({
                    "type": "subscription_confirmed",
                    "event_types": event_types,
                    "timestamp": datetime.now().isoformat()
                }, client_id)

            elif message_type == "unsubscribe":
                # 取消订阅事件
                event_types = data.get("event_types", [])
                for event_type in event_types:
                    secure_connection_manager.unsubscribe_from_event_type(event_type, client_id)

                await secure_connection_manager.send_personal_message({
                    "type": "unsubscription_confirmed",
                    "event_types": event_types,
                    "timestamp": datetime.now().isoformat()
                }, client_id)

            elif message_type == "ping":
                # 心跳响应
                await secure_connection_manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, client_id)

            elif message_type == "publish_event":
                # 发布事件
                event_type = data.get("event_type")
                payload = data.get("payload", {})
                source = data.get("source", "websocket")

                # 检查权限
                required_permission = f"events.{event_type}.publish"
                user_permissions = token_data.permissions if token_data else []

                if required_permission in user_permissions or "*" in user_permissions:
                    # 创建并发布事件
                    event = Event(
                        id=f"evt_{datetime.now().timestamp()}",
                        type=EventType(event_type),
                        source=source,
                        timestamp=datetime.utcnow(),
                        payload=payload,
                        correlation_id=data.get("correlation_id"),
                        reply_to=data.get("reply_to"),
                        user_id=token_data.user_id if token_data else None
                    )

                    # 广播给订阅者（排除发送者）
                    await secure_connection_manager.broadcast_event(event, client_id)

                    logger.info(f"📤 WebSocket发布事件: {event_type} by {client_id}")
                else:
                    await secure_connection_manager.send_personal_message({
                        "type": "error",
                        "message": f"No permission to publish {event_type}",
                        "timestamp": datetime.now().isoformat()
                    }, client_id)

            else:
                # 未知消息类型
                await secure_connection_manager.send_personal_message({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.now().isoformat()
                }, client_id)

    except WebSocketDisconnect:
        if client_id:
            secure_connection_manager.disconnect(client_id)
            logger.info(f"🔌 WebSocket客户端断开连接: {client_id}")

    except Exception as e:
        logger.error(f"❌ WebSocket错误: {e}")
        if client_id:
            secure_connection_manager.disconnect(client_id)

# 事件监听器注册
async def register_secure_event_listeners():
    """注册安全事件监听器"""

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

    logger.info("✅ 安全事件监听器注册完成")

# 启动时注册事件监听器
@router.on_event("startup")
async def startup_secure_event_handler():
    """启动安全事件处理"""
    await register_secure_event_listeners()
    logger.info("🚀 安全事件路由启动完成")

@router.on_event("shutdown")
async def shutdown_secure_event_handler():
    """关闭安全事件处理"""
    logger.info("🛑 安全事件路由关闭完成")