/**
 * 数据库连接管理
 * 独立的Neo4j和PostgreSQL连接池
 */

import asyncpg
import redis.asyncio as redis
from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional, AsyncGenerator
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# 数据库连接池
neo4j_driver: Optional[AsyncDriver] = None
postgres_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None


async def init_database() -> None:
    """初始化所有数据库连接"""
    global neo4j_driver, postgres_pool, redis_client

    try:
        # 初始化Neo4j连接
        neo4j_uri = f"bolt://{os.getenv('NEO4J_HOST', 'localhost')}:{os.getenv('NEO4J_PORT', '7687')}"
        neo4j_auth = (os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASSWORD', 'password'))

        neo4j_driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=neo4j_auth,
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
            connection_timeout=30,
            keep_alive=True
        )

        # 测试Neo4j连接
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN 1 as test")
            await result.consume()

        logger.info(f"✅ Neo4j连接成功: {neo4j_uri}")

        # 初始化PostgreSQL连接池
        postgres_dsn = f"postgresql://{os.getenv('POSTGRES_USER', 'user')}:{os.getenv('POSTGRES_PASSWORD', 'password')}@" \
                      f"{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/" \
                      f"{os.getenv('POSTGRES_DB', 'database')}"

        postgres_pool = await asyncpg.create_pool(
            postgres_dsn,
            min_size=5,
            max_size=20,
            max_queries=50000,
            max_inactive_connection_lifetime=300,
            command_timeout=30
        )

        # 测试PostgreSQL连接
        async with postgres_pool.acquire() as conn:
            result = await conn.fetchrow("SELECT 1 as test")
            assert result['test'] == 1

        logger.info(f"✅ PostgreSQL连接池创建成功")

    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise


async def close_database() -> None:
    """关闭所有数据库连接"""
    global neo4j_driver, postgres_pool

    try:
        # 关闭Neo4j连接
        if neo4j_driver:
            await neo4j_driver.close()
            logger.info("🛑 Neo4j连接已关闭")

        # 关闭PostgreSQL连接池
        if postgres_pool:
            await postgres_pool.close()
            logger.info("🛑 PostgreSQL连接池已关闭")

    except Exception as e:
        logger.error(f"❌ 数据库关闭失败: {e}")


async def check_db_connection() -> bool:
    """检查数据库连接状态"""
    try:
        # 检查Neo4j连接
        if neo4j_driver:
            async with neo4j_driver.session() as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                return record and record['test'] == 1
        return False
    except Exception:
        return False


@asynccontextmanager
async def get_neo4j_session() -> AsyncGenerator:
    """获取Neo4j会话"""
    if not neo4j_driver:
        raise RuntimeError("Neo4j驱动未初始化")

    async with neo4j_driver.session() as session:
        yield session


@asynccontextmanager
async def get_postgres_connection() -> AsyncGenerator:
    """获取PostgreSQL连接"""
    if not postgres_pool:
        raise RuntimeError("PostgreSQL连接池未初始化")

    async with postgres_pool.acquire() as connection:
        yield connection


# Neo4j查询辅助函数
async def execute_neo4j_query(query: str, parameters: Optional[dict] = None) -> list:
    """执行Neo4j查询"""
    async with get_neo4j_session() as session:
        result = await session.run(query, parameters or {})
        records = []
        async for record in result:
            records.append(dict(record))
        return records


async def execute_neo4j_transaction(queries: list, parameters: Optional[list] = None) -> list:
    """执行Neo4j事务"""
    async with get_neo4j_session() as session:
        async def _transaction_work(tx):
            results = []
            for i, query in enumerate(queries):
                params = parameters[i] if parameters and i < len(parameters) else {}
                result = await tx.run(query, params)
                records = []
                async for record in result:
                    records.append(dict(record))
                results.append(records)
            return results

        return await session.execute_read(_transaction_work)


# PostgreSQL查询辅助函数
async def execute_postgres_query(query: str, parameters: Optional[list] = None) -> list:
    """执行PostgreSQL查询"""
    async with get_postgres_connection() as conn:
        results = await conn.fetch(query, *(parameters or []))
        return [dict(record) for record in results]


async def execute_postgres_transaction(queries: list, parameters_list: Optional[list] = None) -> list:
    """执行PostgreSQL事务"""
    if not postgres_pool:
        raise RuntimeError("PostgreSQL连接池未初始化")

    async with postgres_pool.acquire() as conn:
        async with conn.transaction():
            results = []
            for i, query in enumerate(queries):
                params = parameters_list[i] if parameters_list and i < len(parameters_list) else []
                result = await conn.fetch(query, *params)
                results.append([dict(record) for record in result])
            return results


# 数据库健康检查
async def check_database_health() -> dict:
    """检查数据库健康状态"""
    health_status = {
        "neo4j": {"status": "unknown", "latency_ms": None},
        "postgres": {"status": "unknown", "latency_ms": None}
    }

    # 检查Neo4j
    try:
        import time
        start_time = time.time()

        async with get_neo4j_session() as session:
            result = await session.run("RETURN 1 as test")
            await result.consume()

        latency = (time.time() - start_time) * 1000
        health_status["neo4j"] = {"status": "healthy", "latency_ms": round(latency, 2)}
    except Exception as e:
        health_status["neo4j"] = {"status": "unhealthy", "error": str(e)}

    # 检查PostgreSQL
    try:
        start_time = time.time()

        async with get_postgres_connection() as conn:
            result = await conn.fetchrow("SELECT 1 as test")

        latency = (time.time() - start_time) * 1000
        health_status["postgres"] = {"status": "healthy", "latency_ms": round(latency, 2)}
    except Exception as e:
        health_status["postgres"] = {"status": "unhealthy", "error": str(e)}

    return health_status


# 连接池监控
async def get_connection_pool_stats() -> dict:
    """获取连接池统计信息"""
    stats = {
        "neo4j": {"connected": False, "pool_size": 0},
        "postgres": {"connected": False, "pool_size": 0, "active_connections": 0, "idle_connections": 0}
    }

    # Neo4j统计
    if neo4j_driver:
        stats["neo4j"]["connected"] = True
        # Neo4j驱动没有直接的池大小统计

    # PostgreSQL统计
    if postgres_pool:
        stats["postgres"]["connected"] = True
        stats["postgres"]["pool_size"] = postgres_pool.get_size()
        stats["postgres"]["active_connections"] = postgres_pool.get_active_connections()
        stats["postgres"]["idle_connections"] = postgres_pool.get_idle_connections()

    return stats


import os  # 需要在文件末尾添加，避免循环导入

__all__ = [
    'init_database',
    'close_database',
    'check_db_connection',
    'get_neo4j_session',
    'get_postgres_connection',
    'execute_neo4j_query',
    'execute_neo4j_transaction',
    'execute_postgres_query',
    'execute_postgres_transaction',
    'check_database_health',
    'get_connection_pool_stats'
]


# 配置文件导入（避免循环导入）
def load_db_config() -> dict:
    """加载数据库配置"""
    return {
        'neo4j': {
            'host': os.getenv('NEO4J_HOST', 'localhost'),
            'port': int(os.getenv('NEO4J_PORT', '7687')),
            'user': os.getenv('NEO4J_USER', 'neo4j'),
            'password': os.getenv('NEO4J_PASSWORD', 'password'),
            'database': os.getenv('NEO4J_DB', 'neo4j')
        },
        'postgres': {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'database'),
            'user': os.getenv('POSTGRES_USER', 'user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'password')
        }
    }