/**
 * 安全模块 - 认证、授权、输入验证
 * 提供WebSocket和API的安全保护
 */

import jwt
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, WebSocket, status
from pydantic import BaseModel, validator
import re

logger = logging.getLogger(__name__)

# 安全配置
SECRET_KEY = secrets.token_urlsafe(32)  # 应该从环境变量读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
MAX_QUERY_LENGTH = 1000
MAX_BATCH_SIZE = 100

class SecurityConfig:
    """安全配置"""
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://mundi.ai",
        "https://anway.mundi.ai"
    ]

    ALLOWED_EVENT_TYPES: List[str] = [
        "hydro:scene_changed",
        "hydro:data_updated",
        "hydro:alert_triggered",
        "hydro:viewport_changed",
        "kg:search_request",
        "kg:search_completed",
        "kg:analysis_request",
        "kg:analysis_completed",
        "spatial:analysis_request",
        "spatial:analysis_completed",
        "system:connected",
        "system:disconnected",
        "system:error"
    ]

    RATE_LIMITS = {
        "ws_connections_per_ip": 10,
        "events_per_minute": 100,
        "search_requests_per_minute": 30,
        "analysis_requests_per_minute": 20
    }

class TokenData(BaseModel):
    """令牌数据"""
    user_id: str
    username: str
    permissions: List[str] = []

class WebSocketAuthRequest(BaseModel):
    """WebSocket认证请求"""
    token: str
    client_id: str

    @validator('token')
    def validate_token(cls, v):
        if not v or len(v) < 10:
            raise ValueError('Invalid token format')
        return v

    @validator('client_id')
    def validate_client_id(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]{8,64}$', v):
            raise ValueError('Invalid client ID format')
        return v

class SanitizedEvent(BaseModel):
    """经过清理的事件"""
    event_type: str
    payload: Dict[str, Any]
    source: str
    correlation_id: Optional[str] = None

    @validator('event_type')
    def validate_event_type(cls, v):
        if v not in SecurityConfig.ALLOWED_EVENT_TYPES:
            raise ValueError(f'Event type {v} is not allowed')
        return v

    @validator('payload')
    def validate_payload(cls, v):
        # 深度验证和清理payload
        return sanitize_payload(v)

    @validator('source')
    def validate_source(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]{3,32}$', v):
            raise ValueError('Invalid source format')
        return v

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """清理字符串输入"""
    if not isinstance(value, str):
        return str(value)

    # 限制长度
    if len(value) > max_length:
        value = value[:max_length]

    # 移除潜在危险字符
    value = re.sub(r'[<>\"\'&]', '', value)

    # 移除SQL注入尝试
    sql_patterns = [
        r'(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)',
        r'(\b(and|or|not|xor)\b.*\b(=|!=|>|<|>=|<=)\b)',
        r'(\b(waitfor|delay|sleep)\b)',
        r'(\/\*.*?\*\/)',  # 注释
        r'(--.*$)',        # SQL注释
    ]

    for pattern in sql_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)

    return value.strip()

def sanitize_payload(payload: Any, max_depth: int = 5, current_depth: int = 0) -> Any:
    """递归清理payload数据"""
    if current_depth > max_depth:
        return None

    if isinstance(payload, str):
        return sanitize_string(payload)
    elif isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            # 清理key
            clean_key = sanitize_string(str(key), max_length=100)
            # 递归清理value
            sanitized[clean_key] = sanitize_payload(value, max_depth, current_depth + 1)
        return sanitized
    elif isinstance(payload, list):
        # 限制列表长度
        if len(payload) > 1000:
            payload = payload[:1000]
        return [sanitize_payload(item, max_depth, current_depth + 1) for item in payload]
    elif isinstance(payload, (int, float, bool)) or payload is None:
        return payload
    else:
        # 对于其他类型，转换为字符串并清理
        return sanitize_string(str(payload))

def validate_coordinates(lat: float, lng: float) -> bool:
    """验证地理坐标"""
    return -90 <= lat <= 90 and -180 <= lng <= 180

def validate_viewport(west: float, south: float, east: float, north: float) -> bool:
    """验证视口边界"""
    return (
        validate_coordinates(south, west) and
        validate_coordinates(north, east) and
        south < north and
        west < east
    )

def validate_radius(radius_km: float) -> bool:
    """验证半径"""
    return 0.1 <= radius_km <= 1000  # 0.1km 到 1000km

def create_access_token(user_id: str, username: str, permissions: List[str] = None) -> str:
    """创建访问令牌"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "username": username,
        "permissions": permissions or [],
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": secrets.token_urlsafe(16)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def verify_token(token: str) -> Optional[TokenData]:
    """验证令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 检查过期时间
        exp = datetime.fromtimestamp(payload.get("exp", 0))
        if exp < datetime.utcnow():
            return None

        return TokenData(
            user_id=payload.get("sub"),
            username=payload.get("username"),
            permissions=payload.get("permissions", [])
        )
    except jwt.JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        return None

async def authenticate_websocket(websocket: WebSocket, auth_request: WebSocketAuthRequest) -> Optional[TokenData]:
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

        logger.info(f"WebSocket authenticated for user {token_data.username}")
        return token_data

    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        await websocket.close(code=4400, reason="Authentication error")
        return None

def validate_search_query(query: str) -> str:
    """验证搜索查询"""
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string")

    query = sanitize_string(query, max_length=MAX_QUERY_LENGTH)

    if len(query) < 2:
        raise ValueError("Query must be at least 2 characters long")

    # 检查特殊字符比例
    special_chars = sum(1 for c in query if not c.isalnum() and c not in " .,;:!?-")
    if special_chars > len(query) * 0.3:
        raise ValueError("Query contains too many special characters")

    return query

def validate_spatial_request(bounds: Dict[str, float]) -> bool:
    """验证空间分析请求"""
    required_fields = ["west", "south", "east", "north"]

    for field in required_fields:
        if field not in bounds:
            raise ValueError(f"Missing required field: {field}")

        value = bounds[field]
        if not isinstance(value, (int, float)):
            raise ValueError(f"Field {field} must be numeric")

    # 验证坐标
    if not validate_viewport(bounds["west"], bounds["south"], bounds["east"], bounds["north"]):
        raise ValueError("Invalid viewport coordinates")

    # 验证面积限制 (最大 10000 平方公里)
    area = (bounds["east"] - bounds["west"]) * (bounds["north"] - bounds["south"])
    if area > 100:  # 约100度平方，实际面积会更大
        raise ValueError("Analysis area too large")

    return True

def validate_node_types(node_types: List[str]) -> List[str]:
    """验证节点类型列表"""
    if not isinstance(node_types, list):
        raise ValueError("Node types must be a list")

    if len(node_types) > 50:
        raise ValueError("Too many node types specified")

    allowed_types = [
        "Location", "AdministrativeUnit", "Feature",
        "Dataset", "Concept", "TimePeriod",
        "MonitoringStation", "FloodRisk", "River", "Dam"
    ]

    sanitized_types = []
    for node_type in node_types:
        if not isinstance(node_type, str):
            continue

        sanitized = sanitize_string(node_type, max_length=50)
        if sanitized in allowed_types:
            sanitized_types.append(sanitized)

    return sanitized_types

def create_correlation_id() -> str:
    """创建关联ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_urlsafe(8)
    return f"corr_{timestamp}_{random_part}"

def hash_sensitive_data(data: str) -> str:
    """哈希敏感数据"""
    return hashlib.sha256(data.encode() + SECRET_KEY.encode()).hexdigest()

# 速率限制装饰器
class RateLimiter:
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = {}

    def is_allowed(self, identifier: str) -> bool:
        now = datetime.utcnow()

        # 清理旧的记录
        self.calls = {
            k: v for k, v in self.calls.items()
            if now - v[-1] < timedelta(seconds=self.time_window)
        }

        if identifier not in self.calls:
            self.calls[identifier] = [now]
            return True

        # 移除时间窗口外的记录
        self.calls[identifier] = [
            call_time for call_time in self.calls[identifier]
            if now - call_time < timedelta(seconds=self.time_window)
        ]

        if len(self.calls[identifier]) < self.max_calls:
            self.calls[identifier].append(now)
            return True

        return False

# 创建速率限制器实例
rate_limiters = {
    "websocket_auth": RateLimiter(10, 60),  # 每分钟10次认证尝试
    "events": RateLimiter(100, 60),         # 每分钟100个事件
    "search": RateLimiter(30, 60),          # 每分钟30次搜索
    "analysis": RateLimiter(20, 60),        # 每分钟20次分析
}

def check_rate_limit(limit_type: str, identifier: str) -> bool:
    """检查速率限制"""
    if limit_type not in rate_limiters:
        return True

    return rate_limiters[limit_type].is_allowed(identifier)