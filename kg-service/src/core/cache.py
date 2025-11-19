/**
 * 缓存管理模块
 * Redis缓存封装，提供高性能数据缓存
 */

import json
import logging
import hashlib
from typing import Any, Optional, Union
from datetime import timedelta
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# 全局Redis客户端
_redis_client: Optional[redis.Redis] = None


class CacheManager:
    """缓存管理器"""

    def __init__(self, redis_client: redis.Redis, default_ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None

            # 尝试JSON反序列化
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        except Exception as e:
            logger.error(f"❌ 缓存获取失败: {key}, 错误: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        try:
            ttl = ttl or self.default_ttl

            # 序列化值
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            else:
                serialized_value = str(value)

            # 设置缓存
            result = await self.redis.setex(key, ttl, serialized_value)
            return bool(result)

        except Exception as e:
            logger.error(f"❌ 缓存设置失败: {key}, 错误: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            result = await self.redis.delete(key)
            return bool(result)

        except Exception as e:
            logger.error(f"❌ 缓存删除失败: {key}, 错误: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            result = await self.redis.exists(key)
            return bool(result)

        except Exception as e:
            logger.error(f"❌ 缓存检查失败: {key}, 错误: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                result = await self.redis.delete(*keys)
                return result
            return 0

        except Exception as e:
            logger.error(f"❌ 缓存模式清除失败: {pattern}, 错误: {e}")
            return 0

    async def get_ttl(self, key: str) -> int:
        """获取缓存TTL"""
        try:
            ttl = await self.redis.ttl(key)
            return ttl

        except Exception as e:
            logger.error(f"❌ 缓存TTL获取失败: {key}, 错误: {e}")
            return -2

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """原子递增"""
        try:
            result = await self.redis.incrby(key, amount)
            return result

        except Exception as e:
            logger.error(f"❌ 缓存递增失败: {key}, 错误: {e}")
            return None

    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """原子递减"""
        try:
            result = await self.redis.decrby(key, amount)
            return result

        except Exception as e:
            logger.error(f"❌ 缓存递减失败: {key}, 错误: {e}")
            return None

    async def get_many(self, keys: list[str]) -> dict[str, Optional[Any]]:
        """批量获取"""
        try:
            values = await self.redis.mget(keys)
            result = {}

            for key, value in zip(keys, values):
                if value is None:
                    result[key] = None
                else:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value

            return result

        except Exception as e:
            logger.error(f"❌ 缓存批量获取失败: {keys}, 错误: {e}")
            return {key: None for key in keys}

    async def set_many(self, mapping: dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置"""
        try:
            ttl = ttl or self.default_ttl
            pipeline = self.redis.pipeline()

            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    serialized_value = json.dumps(value, ensure_ascii=False)
                else:
                    serialized_value = str(value)

                pipeline.setex(key, ttl, serialized_value)

            results = await pipeline.execute()
            return all(results)

        except Exception as e:
            logger.error(f"❌ 缓存批量设置失败: {mapping}, 错误: {e}")
            return False


# 缓存装饰器
def cache_result(ttl: int = 3600, key_prefix: str = ""):
    """缓存函数结果装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()

            # 尝试从缓存获取
            cached_result = await get_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"🎯 缓存命中: {cache_key}")
                return cached_result

            # 执行函数
            result = await func(*args, **kwargs)

            # 缓存结果
            await set_cache(cache_key, result, ttl)
            return result

        return wrapper
    return decorator


# 全局函数
async def init_cache() -> None:
    """初始化缓存"""
    global _redis_client

    try:
        import os
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        db = int(os.getenv('REDIS_DB', '0'))

        _redis_client = redis.from_url(
            redis_url,
            db=db,
            decode_responses=True,
            socket_keepalive=True,
            retry_on_timeout=True,
            max_connections=20
        )

        # 测试连接
        await _redis_client.ping()
        logger.info(f"✅ 缓存初始化成功: {redis_url}")

    except Exception as e:
        logger.error(f"❌ 缓存初始化失败: {e}")
        raise


async def close_cache() -> None:
    """关闭缓存"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        logger.info("🛑 缓存连接已关闭")


def get_cache_manager() -> CacheManager:
    """获取缓存管理器"""
    if _redis_client is None:
        raise RuntimeError("缓存未初始化")
    return CacheManager(_redis_client)


# 便捷函数
async def get_cache(key: str) -> Optional[Any]:
    """获取缓存值的便捷函数"""
    manager = get_cache_manager()
    return await manager.get(key)


async def set_cache(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置缓存值的便捷函数"""
    manager = get_cache_manager()
    return await manager.set(key, value, ttl)


async def delete_cache(key: str) -> bool:
    """删除缓存值的便捷函数"""
    manager = get_cache_manager()
    return await manager.delete(key)


# 专用缓存键生成器
class CacheKeyBuilder:
    """缓存键构建器"""

    @staticmethod
    def hydro_scene_data(scene_id: str, timestamp: int) -> str:
        return f"hydro:scene:{scene_id}:{timestamp}"

    @staticmethod
    def kg_node_data(node_id: str) -> str:
        return f"kg:node:{node_id}"

    @staticmethod
    def spatial_analysis(bounds_hash: str) -> str:
        return f"spatial:analysis:{bounds_hash}"

    @staticmethod
    def hydro_monitoring_data(station_id: str, time_window: str) -> str:
        return f"hydro:monitoring:{station_id}:{time_window}"


__all__ = [
    'CacheManager',
    'CacheKeyBuilder',
    'init_cache',
    'close_cache',
    'get_cache_manager',
    'get_cache',
    'set_cache',
    'delete_cache',
    'cache_result'
]


# 配置导入
def load_cache_config() -> dict:
    """加载缓存配置"""
    import os
    return {
        'redis_url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
        'redis_db': int(os.getenv('REDIS_DB', '0')),
        'default_ttl': int(os.getenv('CACHE_DEFAULT_TTL', '3600')),
        'max_connections': int(os.getenv('CACHE_MAX_CONNECTIONS', '20'))
    }