/**
 * 错误处理和日志模块
 * 提供系统级的错误处理、日志记录和监控功能
 */

import asyncio
import logging
import traceback
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import sys
from contextlib import contextmanager
import functools

# 日志配置
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler('kg_service.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class ErrorLevel(Enum):
    """错误级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    FATAL = "fatal"

class ErrorCategory(Enum):
    """错误类别"""
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """错误上下文信息"""
    error_id: str
    timestamp: datetime
    level: ErrorLevel
    category: ErrorCategory
    message: str
    exception_type: str
    stack_trace: str
    context_data: Dict[str, Any]
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    service_name: str = "kg_service"
    component: Optional[str] = None
    recovery_suggestion: Optional[str] = None

class ErrorHandler:
    """全局错误处理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.error_log: List[ErrorContext] = []
        self.max_error_log_size = 1000
        self.error_callbacks: Dict[ErrorCategory, List[Callable]] = {}
        self.recovery_strategies: Dict[ErrorCategory, Callable] = {}
        self.metrics = {
            "total_errors": 0,
            "errors_by_level": {level: 0 for level in ErrorLevel},
            "errors_by_category": {category: 0 for category in ErrorCategory},
            "last_error_time": None,
            "error_rate": 0.0  # 错误率 (errors/minute)
        }
        self.error_timestamps: List[datetime] = []
        self.error_rate_window = 300  # 5分钟窗口

    def register_error_callback(self, category: ErrorCategory, callback: Callable):
        """注册错误回调函数"""
        if category not in self.error_callbacks:
            self.error_callbacks[category] = []
        self.error_callbacks[category].append(callback)

    def register_recovery_strategy(self, category: ErrorCategory, strategy: Callable):
        """注册恢复策略"""
        self.recovery_strategies[category] = strategy

    def generate_error_id(self) -> str:
        """生成唯一错误ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        random_part = hashlib.md5(str(datetime.utcnow().timestamp()).encode()).hexdigest()[:8]
        return f"ERR_{timestamp}_{random_part}"

    def classify_error(self, exception: Exception) -> ErrorCategory:
        """对异常进行分类"""
        exception_type = type(exception).__name__
        exception_message = str(exception).lower()

        # 数据库错误
        if any(keyword in exception_message for keyword in [
            'connection', 'timeout', 'deadlock', 'constraint', 'syntax',
            'neo4j', 'postgresql', 'sqlite', 'mysql'
        ]) or 'database' in exception_type.lower():
            return ErrorCategory.DATABASE

        # 网络错误
        if any(keyword in exception_message for keyword in [
            'network', 'connection', 'timeout', 'refused', 'reset',
            'websocket', 'http', 'tcp', 'udp'
        ]) or 'network' in exception_type.lower():
            return ErrorCategory.NETWORK

        # 认证错误
        if any(keyword in exception_message for keyword in [
            'auth', 'unauthorized', 'forbidden', 'token', 'permission',
            'login', 'password', 'credential'
        ]) or 'auth' in exception_type.lower():
            return ErrorCategory.AUTHENTICATION

        # 验证错误
        if any(keyword in exception_message for keyword in [
            'validation', 'invalid', 'required', 'format', 'range',
            'schema', 'constraint'
        ]) or 'validation' in exception_type.lower():
            return ErrorCategory.VALIDATION

        # 外部服务错误
        if any(keyword in exception_message for keyword in [
            'external', 'service', 'api', 'third_party', 'remote'
        ]):
            return ErrorCategory.EXTERNAL_SERVICE

        # 业务逻辑错误
        if any(keyword in exception_message for keyword in [
            'business', 'logic', 'rule', 'condition', 'state'
        ]):
            return ErrorCategory.BUSINESS_LOGIC

        # 系统错误
        if any(keyword in exception_message for keyword in [
            'system', 'memory', 'resource', 'limit', 'overflow'
        ]) or 'system' in exception_type.lower():
            return ErrorCategory.SYSTEM

        return ErrorCategory.UNKNOWN

    def determine_error_level(self, exception: Exception, category: ErrorCategory) -> ErrorLevel:
        """确定错误级别"""
        exception_type = type(exception).__name__
        exception_message = str(exception).lower()

        # 致命错误
        if any(keyword in exception_message for keyword in [
            'fatal', 'critical', 'emergency', 'panic', 'crash'
        ]) or 'fatal' in exception_type.lower():
            return ErrorLevel.FATAL

        # 严重错误
        if any(keyword in exception_message for keyword in [
            'critical', 'severe', 'major', 'emergency'
        ]) or category in [ErrorCategory.DATABASE, ErrorCategory.SYSTEM]:
            return ErrorLevel.CRITICAL

        # 高级错误
        if any(keyword in exception_message for keyword in [
            'error', 'failed', 'unavailable', 'timeout'
        ]) or category in [ErrorCategory.NETWORK, ErrorCategory.EXTERNAL_SERVICE]:
            return ErrorLevel.HIGH

        # 中级错误
        if any(keyword in exception_message for keyword in [
            'warning', 'invalid', 'unauthorized', 'forbidden'
        ]) or category in [ErrorCategory.AUTHENTICATION, ErrorCategory.BUSINESS_LOGIC]:
            return ErrorLevel.MEDIUM

        return ErrorLevel.LOW

    def calculate_error_rate(self) -> float:
        """计算错误率（每分钟的错误数）"""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(seconds=self.error_rate_window)

        # 清理过期的时间戳
        self.error_timestamps = [
            timestamp for timestamp in self.error_timestamps
            if timestamp > cutoff_time
        ]

        # 计算错误率
        if len(self.error_timestamps) >= 2:
            time_span = (self.error_timestamps[-1] - self.error_timestamps[0]).total_seconds()
            if time_span > 0:
                return len(self.error_timestamps) / (time_span / 60)  # 错误/分钟

        return 0.0

    async def handle_error(
        self,
        exception: Exception,
        context_data: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        component: Optional[str] = None
    ) -> ErrorContext:
        """处理错误并返回错误上下文"""
        try:
            # 生成错误ID
            error_id = self.generate_error_id()

            # 分类错误
            category = self.classify_error(exception)
            level = self.determine_error_level(exception, category)

            # 获取堆栈跟踪
            stack_trace = traceback.format_exc()

            # 创建错误上下文
            error_context = ErrorContext(
                error_id=error_id,
                timestamp=datetime.utcnow(),
                level=level,
                category=category,
                message=str(exception),
                exception_type=type(exception).__name__,
                stack_trace=stack_trace,
                context_data=context_data or {},
                user_id=user_id,
                request_id=request_id,
                component=component,
                recovery_suggestion=self._generate_recovery_suggestion(category, exception)
            )

            # 记录错误
            await self._log_error(error_context)

            # 更新指标
            self._update_metrics(error_context)

            # 执行错误回调
            await self._execute_error_callbacks(error_context)

            # 尝试恢复
            await self._attempt_recovery(error_context)

            return error_context

        except Exception as e:
            # 防止错误处理本身出错
            self.logger.critical(f"错误处理失败: {e}")
            self.logger.critical(traceback.format_exc())
            return ErrorContext(
                error_id="CRITICAL_ERROR_HANDLER_FAILURE",
                timestamp=datetime.utcnow(),
                level=ErrorLevel.FATAL,
                category=ErrorCategory.SYSTEM,
                message="Critical error in error handler",
                exception_type="ErrorHandlerFailure",
                stack_trace=traceback.format_exc(),
                context_data={"original_error": str(exception), "handler_error": str(e)}
            )

    async def _log_error(self, error_context: ErrorContext):
        """记录错误日志"""
        # 添加到错误日志
        self.error_log.append(error_context)
        if len(self.error_log) > self.max_error_log_size:
            self.error_log.pop(0)

        # 记录到日志系统
        log_message = f"Error {error_context.error_id}: {error_context.message}"
        log_data = {
            "error_id": error_context.error_id,
            "level": error_context.level.value,
            "category": error_context.category.value,
            "component": error_context.component,
            "user_id": error_context.user_id,
            "request_id": error_context.request_id,
            "context": error_context.context_data
        }

        if error_context.level == ErrorLevel.FATAL:
            self.logger.critical(log_message, extra=log_data)
        elif error_context.level == ErrorLevel.CRITICAL:
            self.logger.error(log_message, extra=log_data)
        elif error_context.level == ErrorLevel.HIGH:
            self.logger.error(log_message, extra=log_data)
        elif error_context.level == ErrorLevel.MEDIUM:
            self.logger.warning(log_message, extra=log_data)
        else:
            self.logger.info(log_message, extra=log_data)

    def _update_metrics(self, error_context: ErrorContext):
        """更新错误指标"""
        self.metrics["total_errors"] += 1
        self.metrics["errors_by_level"][error_context.level] += 1
        self.metrics["errors_by_category"][error_context.category] += 1
        self.metrics["last_error_time"] = error_context.timestamp

        # 添加时间戳用于错误率计算
        self.error_timestamps.append(error_context.timestamp)
        self.metrics["error_rate"] = self.calculate_error_rate()

    async def _execute_error_callbacks(self, error_context: ErrorContext):
        """执行错误回调"""
        callbacks = self.error_callbacks.get(error_context.category, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error_context)
                else:
                    callback(error_context)
            except Exception as e:
                self.logger.error(f"错误回调执行失败: {e}")

    async def _attempt_recovery(self, error_context: ErrorContext):
        """尝试错误恢复"""
        recovery_strategy = self.recovery_strategies.get(error_context.category)
        if recovery_strategy:
            try:
                if asyncio.iscoroutinefunction(recovery_strategy):
                    await recovery_strategy(error_context)
                else:
                    recovery_strategy(error_context)
                self.logger.info(f"错误恢复策略执行成功: {error_context.error_id}")
            except Exception as e:
                self.logger.error(f"错误恢复策略执行失败: {e}")

    def _generate_recovery_suggestion(self, category: ErrorCategory, exception: Exception) -> str:
        """生成恢复建议"""
        suggestions = {
            ErrorCategory.DATABASE: [
                "检查数据库连接配置",
                "验证数据库服务状态",
                "检查网络连接",
                "尝试重新连接数据库"
            ],
            ErrorCategory.NETWORK: [
                "检查网络连接",
                "验证服务端点配置",
                "检查防火墙设置",
                "尝试重新连接"
            ],
            ErrorCategory.AUTHENTICATION: [
                "检查认证凭据",
                "验证用户权限",
                "重新登录获取新令牌",
                "联系系统管理员"
            ],
            ErrorCategory.VALIDATION: [
                "检查输入数据格式",
                "验证必填字段",
                "检查数据类型",
                "参考API文档"
            ],
            ErrorCategory.BUSINESS_LOGIC: [
                "检查业务规则",
                "验证数据状态",
                "查看相关约束条件",
                "联系业务支持"
            ],
            ErrorCategory.EXTERNAL_SERVICE: [
                "检查外部服务状态",
                "验证服务配置",
                "查看服务文档",
                "联系服务提供商"
            ],
            ErrorCategory.SYSTEM: [
                "检查系统资源",
                "查看系统日志",
                "重启相关服务",
                "联系系统管理员"
            ]
        }

        category_suggestions = suggestions.get(category, [
            "检查系统状态",
            "查看详细错误信息",
            "尝试重新操作",
            "联系技术支持"
        ])

        return category_suggestions[0] if category_suggestions else "请查看详细错误信息"

    def get_error_statistics(self, time_range: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """获取错误统计信息"""
        cutoff_time = datetime.utcnow() - time_range

        recent_errors = [
            error for error in self.error_log
            if error.timestamp >= cutoff_time
        ]

        return {
            "time_range_hours": time_range.total_seconds() / 3600,
            "total_errors": len(recent_errors),
            "errors_by_level": {
                level.value: sum(1 for error in recent_errors if error.level == level)
                for level in ErrorLevel
            },
            "errors_by_category": {
                category.value: sum(1 for error in recent_errors if error.category == category)
                for category in ErrorCategory
            },
            "error_rate_per_minute": self.calculate_error_rate(),
            "most_common_errors": self._get_most_common_errors(recent_errors),
            "recent_error_ids": [error.error_id for error in recent_errors[-10:]]
        }

    def _get_most_common_errors(self, errors: List[ErrorContext]) -> List[Dict[str, Any]]:
        """获取最常见的错误"""
        error_counts = {}
        for error in errors:
            key = f"{error.category.value}:{error.exception_type}"
            error_counts[key] = error_counts.get(key, 0) + 1

        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"error_type": error_type, "count": count}
            for error_type, count in sorted_errors[:5]
        ]

    def get_health_status(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        error_rate = self.calculate_error_rate()
        recent_errors = [
            error for error in self.error_log
            if (datetime.utcnow() - error.timestamp) <= timedelta(minutes=5)
        ]

        # 健康评分 (0-100)
        health_score = 100

        # 根据错误率扣分
        if error_rate > 10:  # >10 errors/minute
            health_score -= 50
        elif error_rate > 5:  # >5 errors/minute
            health_score -= 30
        elif error_rate > 1:  # >1 error/minute
            health_score -= 10

        # 根据最近错误扣分
        if recent_errors:
            critical_count = sum(1 for error in recent_errors if error.level in [ErrorLevel.CRITICAL, ErrorLevel.FATAL])
            if critical_count > 0:
                health_score -= 20 * critical_count

        health_score = max(0, health_score)

        status = "healthy"
        if health_score < 50:
            status = "critical"
        elif health_score < 70:
            status = "warning"
        elif health_score < 90:
            status = "degraded"

        return {
            "status": status,
            "health_score": health_score,
            "error_rate": error_rate,
            "recent_errors": len(recent_errors),
            "critical_errors": sum(1 for error in recent_errors if error.level in [ErrorLevel.CRITICAL, ErrorLevel.FATAL]),
            "last_error_time": self.metrics["last_error_time"],
            "total_errors": self.metrics["total_errors"]
        }

# 装饰器函数
def with_error_handling(
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    user_id: Optional[str] = None,
    component: Optional[str] = None,
    reraise: bool = True
):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # 获取请求ID（如果可用）
                request_id = kwargs.get('request_id') or getattr(args[0] if args else None, 'request_id', None)

                error_context = await error_handler.handle_error(
                    e,
                    context_data={"function": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                    user_id=user_id,
                    request_id=request_id,
                    component=component or func.__module__ + "." + func.__name__
                )

                if reraise:
                    raise
                return error_context

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 异步处理错误
                asyncio.create_task(error_handler.handle_error(
                    e,
                    context_data={"function": func.__name__, "args": str(args), "kwargs": str(kwargs)},
                    user_id=user_id,
                    request_id=kwargs.get('request_id'),
                    component=component or func.__module__ + "." + func.__name__
                ))

                if reraise:
                    raise
                return None

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

@contextmanager
def error_handling_context(
    operation_name: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    component: Optional[str] = None
):
    """错误处理上下文管理器"""
    try:
        yield
    except Exception as e:
        asyncio.create_task(error_handler.handle_error(
            e,
            context_data={"operation": operation_name},
            user_id=user_id,
            request_id=request_id,
            component=component
        ))
        raise

# 全局错误处理器实例
error_handler = ErrorHandler()

# 注册默认的恢复策略
async def database_recovery_strategy(error_context: ErrorContext):
    """数据库恢复策略"""
    logger.info(f"执行数据库恢复策略: {error_context.error_id}")
    # 这里可以添加数据库重连逻辑
    pass

async def network_recovery_strategy(error_context: ErrorContext):
    """网络恢复策略"""
    logger.info(f"执行网络恢复策略: {error_context.error_id}")
    # 这里可以添加网络重试逻辑
    pass

error_handler.register_recovery_strategy(ErrorCategory.DATABASE, database_recovery_strategy)
error_handler.register_recovery_strategy(ErrorCategory.NETWORK, network_recovery_strategy)

# 便捷函数
async def handle_error_safe(exception: Exception, **kwargs) -> ErrorContext:
    """安全地处理错误"""
    return await error_handler.handle_error(exception, **kwargs)

def get_error_statistics(**kwargs) -> Dict[str, Any]:
    """获取错误统计"""
    return error_handler.get_error_statistics(**kwargs)

def get_system_health() -> Dict[str, Any]:
    """获取系统健康状态"""
    return error_handler.get_health_status()