/**
 * 高性能连接池管理器
 * 根治连接池癌症，实现连接复用和异步管理
 */

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import time
import asyncpg
from neo4j import AsyncGraphDatabase, AsyncSession
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class ConnectionStatus(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    CLOSED = "closed"
    BROKEN = "broken"

@dataclass
class ConnectionMetrics:
    """连接池指标"""
    created_at: datetime
    last_used: datetime
    use_count: int = 0
    total_use_time: float = 0.0
    average_use_time: float = 0.0
    error_count: int = 0

    def record_usage(self, duration: float):
        self.use_count += 1
        self.total_use_time += duration
        self.average_use_time = self.total_use_time / self.use_count
        self.last_used = datetime.utcnow()

@dataclass
class PoolConfig:
    """连接池配置"""
    max_size: int = 50
    min_size: int = 10
    max_idle_time: int = 300  # 5分钟
    connection_timeout: int = 30
    health_check_interval: int = 60
    max_lifetime: int = 3600  # 1小时
    retry_attempts: int = 3
    retry_delay: int = 1

class AsyncConnectionPool:
    """PostgreSQL异步连接池"""

    def __init__(self, database_url: str, config: PoolConfig = None):
        self.database_url = database_url
        self.config = config or PoolConfig()
        self.pool: Optional[asyncpg.Pool] = None
        self.metrics: Dict[str, ConnectionMetrics] = {}
        self.health_check_task: Optional[asyncio.Task] = None
        self.startup_time = datetime.utcnow()

    async def initialize(self):
        """初始化连接池"""
        try:
            logger.info(f"初始化PostgreSQL连接池: {self.config.min_size}-{self.config.max_size}")

            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=self.config.min_size,
                max_size=self.config.max_size,
                max_queries=50000,  # 单连接最大查询数
                max_inactive_connection_lifetime=self.config.max_idle_time,
                setup=self._connection_setup,
                init=self._connection_init
            )

            # 启动健康检查
            self.health_check_task = asyncio.create_task(self._health_check_loop())

            logger.info("PostgreSQL连接池初始化完成")

        except Exception as e:
            logger.error(f"连接池初始化失败: {e}")
            raise

    async def _connection_setup(self, conn):
        """连接设置"""
        await conn.execute("""
            SET statement_timeout = '30s';
            SET lock_timeout = '10s';
            SET idle_in_transaction_session_timeout = '5min';
        """)

    async def _connection_init(self, conn):
        """连接初始化"""
        # 设置类型转换
        await conn.set_type_codec(
            'json', encoder=json.dumps, decoder=json.loads, schema='pg_catalog'
        )
        await conn.set_type_codec(
            'jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog'
        )

    async def acquire(self) -> asyncpg.Connection:
        """获取连接"""
        if not self.pool:
            raise RuntimeError("连接池未初始化")

        start_time = time.time()

        try:
            conn = await self.pool.acquire(timeout=self.config.connection_timeout)

            # 记录指标
            conn_id = id(conn)
            if str(conn_id) not in self.metrics:
                self.metrics[str(conn_id)] = ConnectionMetrics(
                    created_at=datetime.utcnow(),
                    last_used=datetime.utcnow()
                )

            return conn

        except asyncio.TimeoutError:
            logger.error(f"获取连接超时: {self.config.connection_timeout}s")
            raise
        except Exception as e:
            logger.error(f"获取连接失败: {e}")
            raise

    async def release(self, conn: asyncpg.Connection):
        """释放连接"""
        if not self.pool:
            return

        try:
            await self.pool.release(conn)

            # 更新指标
            conn_id = str(id(conn))
            if conn_id in self.metrics:
                self.metrics[conn_id].record_usage(0.0)  # 使用时间在归还时更新

        except Exception as e:
            logger.error(f"释放连接失败: {e}")

    async def execute(self, query: str, *args, **kwargs) -> Any:
        """执行查询（自动管理连接）"""
        conn = None
        start_time = time.time()

        try:
            conn = await self.acquire()
            result = await conn.fetch(query, *args, **kwargs)

            duration = time.time() - start_time

            # 记录慢查询
            if duration > 1.0:  # 超过1秒认为是慢查询
                logger.warning(f"慢查询: {duration:.2f}s - {query[:100]}...")

            return result

        except Exception as e:
            logger.error(f"查询执行失败: {e} - Query: {query[:100]}...")
            raise
        finally:
            if conn:
                await self.release(conn)

    async def execute_one(self, query: str, *args, **kwargs) -> Optional[Dict]:
        """执行查询并返回单行结果"""
        results = await self.execute(query, *args, **kwargs)
        return results[0] if results else None

    async def execute_val(self, query: str, *args, **kwargs) -> Any:
        """执行查询并返回单个值"""
        result = await self.execute_one(query, *args, **kwargs)
        return result[0] if result else None

    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查失败: {e}")

    async def _perform_health_check(self):
        """执行健康检查"""
        try:
            # 简单查询测试
            conn = await self.acquire()
            try:
                await conn.execute("SELECT 1")
                logger.debug("PostgreSQL健康检查通过")
            finally:
                await self.release(conn)
        except Exception as e:
            logger.error(f"PostgreSQL健康检查失败: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        if not self.pool:
            return {"status": "not_initialized"}

        try:
            # 获取池统计信息
            stats = {
                "pool_size": self.pool.get_size(),
                "idle_connections": self.pool.get_idle_size(),
                "active_connections": self.pool.get_size() - self.pool.get_idle_size(),
                "total_queries": sum(m.use_count for m in self.metrics.values()),
                "avg_use_time": sum(m.average_use_time for m in self.metrics.values()) / len(self.metrics) if self.metrics else 0,
                "error_count": sum(m.error_count for m in self.metrics.values()),
                "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
                "status": "healthy" if self.pool.get_size() > 0 else "unhealthy"
            }

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"status": "error", "error": str(e)}

    async def close(self):
        """关闭连接池"""
        logger.info("关闭PostgreSQL连接池")

        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        if self.pool:
            await self.pool.close()
            self.pool = None

class AsyncNeo4jPool:
    """Neo4j异步连接池"""

    def __init__(self, uri: str, auth: tuple, config: PoolConfig = None):
        self.uri = uri
        self.auth = auth
        self.config = config or PoolConfig()
        self.driver = None
        self.session_pool: List[AsyncSession] = []
        self.pool_lock = asyncio.Lock()
        self.metrics: Dict[str, ConnectionMetrics] = {}
        self.startup_time = datetime.utcnow()

    async def initialize(self):
        """初始化Neo4j连接池"""
        try:
            logger.info(f"初始化Neo4j连接池: {self.config.min_size}-{self.config.max_size}")

            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=self.auth,
                max_connection_lifetime=self.config.max_lifetime,
                max_connection_pool_size=self.config.max_size,
                connection_timeout=self.config.connection_timeout
            )

            # 预创建会话池
            async with self.pool_lock:
                for _ in range(self.config.min_size):
                    session = self.driver.session()
                    self.session_pool.append(session)

            logger.info("Neo4j连接池初始化完成")

        except Exception as e:
            logger.error(f"Neo4j连接池初始化失败: {e}")
            raise

    async def acquire(self) -> AsyncSession:
        """获取Neo4j会话"""
        async with self.pool_lock:
            if self.session_pool:
                session = self.session_pool.pop()
                conn_id = id(session)
                if str(conn_id) not in self.metrics:
                    self.metrics[str(conn_id)] = ConnectionMetrics(
                        created_at=datetime.utcnow(),
                        last_used=datetime.utcnow()
                    )
                return session
            else:
                # 创建新会话
                session = self.driver.session()
                conn_id = id(session)
                self.metrics[str(conn_id)] = ConnectionMetrics(
                    created_at=datetime.utcnow(),
                    last_used=datetime.utcnow()
                )
                return session

    async def release(self, session: AsyncSession):
        """释放Neo4j会话"""
        async with self.pool_lock:
            if len(self.session_pool) < self.config.max_size:
                self.session_pool.append(session)
            else:
                # 池已满，关闭会话
                await session.close()

    async def execute(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """执行Cypher查询（自动管理连接）"""
        session = None
        start_time = time.time()

        try:
            session = await self.acquire()

            result = await session.run(query, parameters or {})
            records = []
            async for record in result:
                records.append(dict(record))

            duration = time.time() - start_time

            # 记录慢查询
            if duration > 1.0:
                logger.warning(f"慢Cypher查询: {duration:.2f}s - {query[:100]}...")

            return records

        except Exception as e:
            logger.error(f"Cypher查询执行失败: {e} - Query: {query[:100]}...")
            raise
        finally:
            if session:
                await self.release(session)

    async def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        async with self.pool_lock:
            stats = {
                "pool_size": len(self.session_pool),
                "total_sessions": len(self.metrics),
                "active_sessions": len(self.metrics) - len(self.session_pool),
                "total_queries": sum(m.use_count for m in self.metrics.values()),
                "avg_use_time": sum(m.average_use_time for m in self.metrics.values()) / len(self.metrics) if self.metrics else 0,
                "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
                "status": "healthy" if self.driver else "unhealthy"
            }
            return stats

    async def close(self):
        """关闭Neo4j连接池"""
        logger.info("关闭Neo4j连接池")

        async with self.pool_lock:
            # 关闭所有会话
            for session in self.session_pool:
                await session.close()
            self.session_pool.clear()

        if self.driver:
            await self.driver.close()
            self.driver = None

class ConnectionPoolManager:
    """连接池管理器 - 统一管理所有数据库连接池"""

    def __init__(self):
        self.pools: Dict[str, AsyncConnectionPool] = {}
        self.neo4j_pool: Optional[AsyncNeo4jPool] = None
        self.redis_pool: Optional[redis.Redis] = None
        self.initialized = False

    async def initialize(self, config: Dict[str, Any]):
        """初始化所有连接池"""
        if self.initialized:
            return

        try:
            logger.info("初始化连接池管理器")

            # PostgreSQL连接池
            postgres_config = PoolConfig(
                max_size=config.get('postgres_max_connections', 50),
                min_size=config.get('postgres_min_connections', 10),
                max_idle_time=config.get('postgres_idle_timeout', 300),
                connection_timeout=config.get('postgres_connect_timeout', 30)
            )

            self.pools['postgres'] = AsyncConnectionPool(
                config['postgres_url'],
                postgres_config
            )
            await self.pools['postgres'].initialize()

            # Neo4j连接池
            neo4j_config = PoolConfig(
                max_size=config.get('neo4j_max_connections', 30),
                min_size=config.get('neo4j_min_connections', 5),
                connection_timeout=config.get('neo4j_connect_timeout', 30)
            )

            self.neo4j_pool = AsyncNeo4jPool(
                config['neo4j_uri'],
                (config['neo4j_user'], config['neo4j_password']),
                neo4j_config
            )
            await self.neo4j_pool.initialize()

            # Redis连接池
            self.redis_pool = redis.from_url(
                config['redis_url'],
                max_connections=config.get('redis_max_connections', 100),
                decode_responses=True
            )

            self.initialized = True
            logger.info("连接池管理器初始化完成")

        except Exception as e:
            logger.error(f"连接池管理器初始化失败: {e}")
            await self.close()
            raise

    def get_postgres_pool(self) -> AsyncConnectionPool:
        """获取PostgreSQL连接池"""
        return self.pools['postgres']

    def get_neo4j_pool(self) -> AsyncNeo4jPool:
        """获取Neo4j连接池"""
        return self.neo4j_pool

    def get_redis_pool(self) -> redis.Redis:
        """获取Redis连接池"""
        return self.redis_pool

    async def get_all_stats(self) -> Dict[str, Any]:
        """获取所有连接池的统计信息"""
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "pools": {}
        }

        # PostgreSQL统计
        if 'postgres' in self.pools:
            stats["pools"]["postgres"] = await self.pools['postgres'].get_stats()

        # Neo4j统计
        if self.neo4j_pool:
            stats["pools"]["neo4j"] = await self.neo4j_pool.get_stats()

        # Redis统计 (简化)
        if self.redis_pool:
            try:
                redis_info = await self.redis_pool.info()
                stats["pools"]["redis"] = {
                    "connected_clients": redis_info.get("connected_clients", 0),
                    "used_memory_human": redis_info.get("used_memory_human", "0B"),
                    "keyspace_hits": redis_info.get("keyspace_hits", 0),
                    "keyspace_misses": redis_info.get("keyspace_misses", 0)
                }
            except:
                stats["pools"]["redis"] = {"status": "error"}

        return stats

    async def close(self):
        """关闭所有连接池"""
        logger.info("关闭连接池管理器")

        # 关闭PostgreSQL连接池
        for name, pool in self.pools.items():
            try:
                await pool.close()
            except Exception as e:
                logger.error(f"关闭{name}连接池失败: {e}")

        # 关闭Neo4j连接池
        if self.neo4j_pool:
            try:
                await self.neo4j_pool.close()
            except Exception as e:
                logger.error(f"关闭Neo4j连接池失败: {e}")

        # 关闭Redis连接池
        if self.redis_pool:
            try:
                await self.redis_pool.close()
            except Exception as e:
                logger.error(f"关闭Redis连接池失败: {e}")

        self.pools.clear()
        self.initialized = False

# 全局连接池管理器实例
connection_manager = ConnectionPoolManager()

# 便捷函数
def get_postgres_pool() -> AsyncConnectionPool:
    """获取PostgreSQL连接池"""
    return connection_manager.get_postgres_pool()

def get_neo4j_pool() -> AsyncNeo4jPool:
    """获取Neo4j连接池"""
    return connection_manager.get_neo4j_pool()

def get_redis_pool() -> redis.Redis:
    """获取Redis连接池"""
    return connection_manager.get_redis_pool()

# 装饰器 - 自动管理连接
async def with_connection(pool_name: str):
    """连接池装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            pool = connection_manager.pools.get(pool_name) or connection_manager.neo4j_pool
            if not pool:
                raise RuntimeError(f"连接池 {pool_name} 未初始化")

            # 自动获取连接并执行函数
            if pool_name == 'postgres':
                return await pool.execute(*args, **kwargs)
            else:
                # Neo4j查询
                query = args[0] if args else kwargs.get('query')
                parameters = args[1] if len(args) > 1 else kwargs.get('parameters')
                return await pool.execute(query, parameters)

        return wrapper
    return decorator