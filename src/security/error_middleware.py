"""
综合错误处理中间件
提供统一的错误处理、日志记录和恢复机制
"""

import logging
import traceback
import json
import time
from typing import Dict, Any, Optional, Callable, Union
from datetime import datetime
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import asyncio
import uuid

# 导入现有的错误处理
from src.core.error_handler import ErrorHandler, ErrorLevel, ErrorCategory, ErrorContext
from src.security.auth_system import verify_jwt_token, get_user_from_token_payload

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """安全相关错误"""
    pass

class ValidationError(Exception):
    """验证错误"""
    pass

class BusinessLogicError(Exception):
    """业务逻辑错误"""
    pass

class DatabaseError(Exception):
    """数据库错误"""
    pass

class ExternalServiceError(Exception):
    """外部服务错误"""
    pass

class RateLimitError(Exception):
    """速率限制错误"""
    pass

class AuthenticationError(Exception):
    """认证错误"""
    pass

class AuthorizationError(Exception):
    """授权错误"""
    pass

class ErrorResponse:
    """统一的错误响应格式"""

    def __init__(self, error_id: str, status_code: int, message: str,
                 error_type: str, details: Optional[Dict[str, Any]] = None,
                 timestamp: Optional[datetime] = None, path: Optional[str] = None,
                 request_id: Optional[str] = None):
        self.error_id = error_id
        self.status_code = status_code
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.path = path
        self.request_id = request_id

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": {
                "error_id": self.error_id,
                "status_code": self.status_code,
                "message": self.message,
                "type": self.error_type,
                "details": self.details,
                "timestamp": self.timestamp.isoformat(),
                "path": self.path,
                "request_id": self.request_id
            },
            "meta": {
                "version": "1.0",
                "service": "mundi-gis"
            }
        }

class ErrorClassification:
    """错误分类器"""

    @staticmethod
    def classify_exception(exc: Exception) -> tuple[ErrorCategory, int]:
        """分类异常并返回HTTP状态码"""

        if isinstance(exc, SecurityError):
            return ErrorCategory.AUTHENTICATION, status.HTTP_403_FORBIDDEN

        elif isinstance(exc, AuthenticationError):
            return ErrorCategory.AUTHENTICATION, status.HTTP_401_UNAUTHORIZED

        elif isinstance(exc, AuthorizationError):
            return ErrorCategory.AUTHENTICATION, status.HTTP_403_FORBIDDEN

        elif isinstance(exc, ValidationError):
            return ErrorCategory.VALIDATION, status.HTTP_400_BAD_REQUEST

        elif isinstance(exc, RateLimitError):
            return ErrorCategory.NETWORK, status.HTTP_429_TOO_MANY_REQUESTS

        elif isinstance(exc, DatabaseError):
            return ErrorCategory.DATABASE, status.HTTP_500_INTERNAL_SERVER_ERROR

        elif isinstance(exc, ExternalServiceError):
            return ErrorCategory.EXTERNAL_SERVICE, status.HTTP_503_SERVICE_UNAVAILABLE

        elif isinstance(exc, BusinessLogicError):
            return ErrorCategory.BUSINESS_LOGIC, status.HTTP_400_BAD_REQUEST

        elif isinstance(exc, HTTPException):
            # 处理FastAPI的HTTP异常
            if exc.status_code == 404:
                return ErrorCategory.VALIDATION, status.HTTP_404_NOT_FOUND
            elif exc.status_code == 400:
                return ErrorCategory.VALIDATION, status.HTTP_400_BAD_REQUEST
            elif exc.status_code >= 500:
                return ErrorCategory.SYSTEM, exc.status_code
            else:
                return ErrorCategory.VALIDATION, exc.status_code

        elif isinstance(exc, (ValueError, TypeError, AttributeError)):
            return ErrorCategory.VALIDATION, status.HTTP_400_BAD_REQUEST

        elif isinstance(exc, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK, status.HTTP_503_SERVICE_UNAVAILABLE

        else:
            return ErrorCategory.SYSTEM, status.HTTP_500_INTERNAL_SERVER_ERROR

class SecurityErrorHandler:
    """安全错误处理专用类"""

    @staticmethod
    def sanitize_error_message(message: str, status_code: int) -> str:
        """清理错误消息，避免信息泄露"""

        # 5xx错误不应该暴露内部细节
        if status_code >= 500:
            return "Internal server error. Please try again later."

        # 4xx错误可以提供更多细节，但要谨慎
        if status_code in [401, 403]:
            return "Authentication failed. Please check your credentials."

        # 清理可能包含敏感信息的错误
        sensitive_patterns = [
            r'database.*error',
            r'sql.*error',
            r'connection.*failed',
            r'password.*',
            r'secret.*',
            r'token.*',
            r'\w+_key',
            r'\w+_secret',
            r'\w+_password'
        ]

        sanitized = message
        for pattern in sensitive_patterns:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)

        return sanitized

    @staticmethod
    def validate_error_details(details: Dict[str, Any], status_code: int) -> Dict[str, Any]:
        """验证错误详情，移除敏感信息"""

        if status_code >= 500:
            # 5xx错误不应该返回任何内部详情
            return {}

        # 移除敏感键
        sensitive_keys = {'password', 'secret', 'token', 'key', 'auth', 'credential'}

        def clean_dict(d):
            if not isinstance(d, dict):
                return d

            cleaned = {}
            for key, value in d.items():
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    cleaned[key] = '[REDACTED]'
                elif isinstance(value, dict):
                    cleaned[key] = clean_dict(value)
                elif isinstance(value, list):
                    cleaned[key] = [clean_dict(item) if isinstance(item, dict) else item for item in value]
                else:
                    cleaned[key] = value
            return cleaned

        return clean_dict(details)

class ComprehensiveErrorMiddleware(BaseHTTPMiddleware):
    """综合错误处理中间件"""

    def __init__(self, app: ASGIApp, debug: bool = False):
        super().__init__(app)
        self.debug = debug
        self.error_handler = ErrorHandler()
        self.error_classification = ErrorClassification()
        self.security_handler = SecurityErrorHandler()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求和错误"""

        # 生成请求ID用于追踪
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 获取用户信息
        user_info = await self._extract_user_info(request)

        start_time = time.time()

        try:
            # 执行请求
            response = await call_next(request)

            # 记录成功响应（可选）
            if response.status_code >= 400:
                await self._log_error_response(request, response, user_info)

            return response

        except Exception as exc:
            # 处理异常
            return await self._handle_exception(exc, request, user_info, start_time)

    async def _extract_user_info(self, request: Request) -> Optional[Dict[str, Any]]:
        """从请求中提取用户信息"""

        try:
            # 从Authorization头获取JWT令牌
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = verify_jwt_token(token)
                if payload:
                    return {
                        "user_id": payload.get("sub"),
                        "username": payload.get("username"),
                        "role": payload.get("role"),
                        "organization_id": payload.get("org_id")
                    }

            # 从会话或cookie获取（备用方案）
            # 这里可以根据实际需求扩展

        except Exception as e:
            logger.warning(f"用户信息提取失败: {e}")

        return None

    async def _handle_exception(self, exc: Exception, request: Request,
                              user_info: Optional[Dict[str, Any]], start_time: float) -> JSONResponse:
        """处理异常并生成响应"""

        # 分类异常
        error_category, status_code = self.error_classification.classify_exception(exc)

        # 生成错误ID
        error_id = f"ERR_{int(time.time() * 1000)}_{str(uuid.uuid4())[:8]}"

        # 获取原始错误消息
        original_message = str(exc)

        # 安全化错误消息
        safe_message = self.security_handler.sanitize_error_message(original_message, status_code)

        # 获取错误详情
        error_details = self._extract_error_details(exc, error_category)

        # 验证并清理错误详情
        safe_details = self.security_handler.validate_error_details(error_details, status_code)

        # 创建错误响应
        error_response = ErrorResponse(
            error_id=error_id,
            status_code=status_code,
            message=safe_message,
            error_type=error_category.value,
            details=safe_details if self.debug else {},
            path=str(request.url),
            request_id=request.state.request_id
        )

        # 记录错误到错误处理系统
        await self._log_error(exc, error_response, request, user_info)

        # 记录性能指标
        duration_ms = (time.time() - start_time) * 1000

        # 返回JSON响应
        return JSONResponse(
            status_code=status_code,
            content=error_response.to_dict(),
            headers={
                "X-Request-ID": request.state.request_id,
                "X-Error-ID": error_id,
                "X-Response-Time": f"{duration_ms:.2f}ms"
            }
        )

    def _extract_error_details(self, exc: Exception, category: ErrorCategory) -> Dict[str, Any]:
        """提取错误详情"""

        details = {
            "exception_type": type(exc).__name__,
            "exception_module": type(exc).__module__,
        }

        # 根据不同异常类型提取特定信息
        if isinstance(exc, ValidationError):
            details["validation_errors"] = getattr(exc, 'errors', [])

        elif isinstance(exc, HTTPException):
            details["detail"] = exc.detail
            if hasattr(exc, 'headers') and exc.headers:
                details["headers"] = dict(exc.headers)

        elif isinstance(exc, (DatabaseError, ExternalServiceError)):
            details["service"] = getattr(exc, 'service', 'unknown')
            details["operation"] = getattr(exc, 'operation', 'unknown')

        elif isinstance(exc, RateLimitError):
            details["retry_after"] = getattr(exc, 'retry_after', None)

        # 添加堆栈跟踪（仅在debug模式下）
        if self.debug:
            details["stack_trace"] = traceback.format_exc()

        return details

    async def _log_error(self, exc: Exception, error_response: ErrorResponse,
                       request: Request, user_info: Optional[Dict[str, Any]]):
        """记录错误到错误处理系统"""

        try:
            # 构建错误上下文
            context_data = {
                "request_id": request.state.request_id,
                "request_method": request.method,
                "request_url": str(request.url),
                "request_headers": dict(request.headers),
                "user_info": user_info,
                "error_details": error_response.details,
                "status_code": error_response.status_code
            }

            # 使用现有的错误处理系统
            error_context = await self.error_handler.handle_error(
                exception=exc,
                context_data=context_data,
                user_id=user_info.get("user_id") if user_info else None,
                request_id=request.state.request_id,
                component=f"{request.method}:{request.url.path}"
            )

            # 记录到标准日志
            logger.error(f"错误ID: {error_context.error_id}, 类型: {error_context.category.value}, "
                       f"级别: {error_context.level.value}, 消息: {error_context.message}")

        except Exception as log_error:
            logger.critical(f"错误记录失败: {log_error}")

    async def _log_error_response(self, request: Request, response: Response, user_info: Optional[Dict[str, Any]]):
        """记录错误响应（非异常）"""

        # 可以在这里添加业务逻辑错误记录
        # 例如：404错误、权限错误等

        if response.status_code == 404:
            logger.warning(f"404错误: {request.method} {request.url} - 用户: {user_info}")
        elif response.status_code == 403:
            logger.warning(f"403禁止访问: {request.method} {request.url} - 用户: {user_info}")

# 便捷函数用于手动错误处理
async def handle_security_error(error_message: str, error_type: str = "security",
                              user_id: Optional[str] = None, request_id: Optional[str] = None) -> None:
    """处理安全相关错误"""
    security_error = SecurityError(error_message)

    context_data = {
        "error_type": error_type,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }

    await error_handler.handle_error(
        exception=security_error,
        context_data=context_data,
        user_id=user_id,
        request_id=request_id,
        component="security"
    )

async def handle_validation_error(field: str, message: str, value: Any = None,
                                user_id: Optional[str] = None, request_id: Optional[str] = None) -> None:
    """处理验证错误"""
    validation_error = ValidationError(f"字段 '{field}' 验证失败: {message}")

    context_data = {
        "field": field,
        "message": message,
        "value": str(value) if value else None,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }

    await error_handler.handle_error(
        exception=validation_error,
        context_data=context_data,
        user_id=user_id,
        request_id=request_id,
        component="validation"
    )

# 全局错误处理中间件实例
def create_error_middleware(debug: bool = False) -> ComprehensiveErrorMiddleware:
    """创建错误处理中间件"""
    return ComprehensiveErrorMiddleware(None, debug=debug)

# 错误处理配置
ERROR_HANDLING_CONFIG = {
    "debug": False,  # 生产环境应设为False
    "log_level": "INFO",
    "include_stack_trace": False,
    "sanitize_errors": True,
    "max_error_details_size": 4096,  # 4KB
    "rate_limit_errors": True,
    "error_retention_days": 30
}

# 错误码定义
ERROR_CODES = {
    # 认证授权错误
    "AUTH_INVALID_TOKEN": {"code": 1001, "message": "无效的身份验证令牌"},
    "AUTH_EXPIRED_TOKEN": {"code": 1002, "message": "身份验证令牌已过期"},
    "AUTH_INSUFFICIENT_PERMISSIONS": {"code": 1003, "message": "权限不足"},
    "AUTH_USER_NOT_FOUND": {"code": 1004, "message": "用户不存在"},

    # 验证错误
    "VALIDATION_INVALID_INPUT": {"code": 2001, "message": "输入参数无效"},
    "VALIDATION_MISSING_REQUIRED": {"code": 2002, "message": "缺少必需参数"},
    "VALIDATION_TYPE_MISMATCH": {"code": 2003, "message": "参数类型不匹配"},

    # 数据库错误
    "DB_CONNECTION_FAILED": {"code": 3001, "message": "数据库连接失败"},
    "DB_QUERY_FAILED": {"code": 3002, "message": "数据库查询失败"},
    "DB_UNIQUE_VIOLATION": {"code": 3003, "message": "数据唯一性冲突"},

    # 文件上传错误
    "UPLOAD_FILE_TOO_LARGE": {"code": 4001, "message": "文件大小超过限制"},
    "UPLOAD_INVALID_FILE_TYPE": {"code": 4002, "message": "文件类型不允许"},
    "UPLOAD_MALICIOUS_FILE": {"code": 4003, "message": "检测到恶意文件"},

    # 外部服务错误
    "EXTERNAL_SERVICE_UNAVAILABLE": {"code": 5001, "message": "外部服务不可用"},
    "EXTERNAL_SERVICE_TIMEOUT": {"code": 5002, "message": "外部服务请求超时"},

    # 系统错误
    "SYSTEM_INTERNAL_ERROR": {"code": 9001, "message": "系统内部错误"},
    "SYSTEM_SERVICE_UNAVAILABLE": {"code": 9002, "message": "服务暂时不可用"}
}