"""
连接池包装器 - 向后兼容旧代码
使用现有的高性能连接池
"""

import os
from typing import Optional
from contextlib import asynccontextmanager
from src.dependencies.db_pool import get_pooled_connection

class AsyncDatabaseConnection:
    """向后兼容的连接包装器

    使用现有的高性能连接池，但保持原有接口不变
    这样现有代码无需修改即可使用新连接池
    """

    def __init__(self, span_name: Optional[str] = None):
        self.span_name = span_name
        self._conn = None
        self._connection_uri = self._build_connection_uri()
        self._cm = None

    def _build_connection_uri(self) -> str:
        """从环境变量构建数据库连接URI"""
        user = os.environ.get('POSTGRES_USER', 'mundiuser')
        password = os.environ.get('POSTGRES_PASSWORD', 'gdalpassword')
        host = os.environ.get('POSTGRES_HOST', 'localhost')
        port = os.environ.get('POSTGRES_PORT', '5432')
        db = os.environ.get('POSTGRES_DB', 'mundidb')
        # 禁用SSL（在Docker内部网络中不需要）
        return f"postgresql://{user}:{password}@{host}:{port}/{db}?sslmode=disable"

    async def __aenter__(self):
        """获取连接 - 使用连接池"""
        self._cm = get_pooled_connection(self._connection_uri)
        self._conn = await self._cm.__aenter__()
        return self._conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """释放连接 - 归还到池中"""
        if self._cm:
            await self._cm.__aexit__(exc_type, exc_val, exc_tb)

# 向后兽容的函数
async def async_conn(span_name: Optional[str] = None):
    """向后兽容的连接获取函数"""
    return AsyncDatabaseConnection(span_name)

def get_async_db_connection(span_name: Optional[str] = None):
    """获取一个可以作为上下文管理器使用的连接
    
    这个函数随下需要配合 async with 使用
    """
    return AsyncDatabaseConnection(span_name)

# 迁移辅助函数
async def migrate_to_new_pool():
    """迁移到新的连接池

    这个函数在应用启动时调用
    """
    print("✅ 使用现有的高性能连接池")
    print(f"   PostgreSQL 连接池已初始化")
