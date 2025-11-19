"""
PostGIS安全补丁
快速修复SQL注入漏洞，替换原有的危险SQL拼接
"""

import logging
from typing import Dict, Any, List
import asyncpg
from .secure_postgis import SecurePostGISProcessor, ValidationLevel

logger = logging.getLogger(__name__)

async def secure_process_postgis_layer(pg_conn: asyncpg.Connection, query: str,
                                     layer_name: str) -> Dict[str, Any]:
    """
    安全地处理PostGIS图层查询
    替代原有的危险SQL拼接实现

    Args:
        pg_conn: PostgreSQL连接
        query: 用户提交的查询
        layer_name: 图层名称

    Returns:
        处理结果，包含元数据和验证信息
    """

    try:
        # 使用安全处理器
        processor = SecurePostGISProcessor(pg_conn, ValidationLevel.STRICT)

        # 1. 验证查询并获取列信息
        validation_result, attribute_names = await processor.validate_and_prepare_query(query)

        if not validation_result.is_valid:
            return {
                "status": "error",
                "error": f"查询验证失败: {', '.join(validation_result.errors)}",
                "validation_errors": validation_result.errors
            }

        # 2. 获取空间元数据
        metadata = await processor.get_spatial_metadata(query)
        metadata["attribute_names"] = attribute_names or []

        # 验证必需的数据
        if metadata["feature_count"] is None:
            return {
                "status": "error",
                "error": "无法获取要素数量",
                "metadata": metadata
            }

        if not metadata["geometry_type"]:
            return {
                "status": "error",
                "error": "无法检测几何类型",
                "metadata": metadata
            }

        if not metadata["bounds"]:
            return {
                "status": "error",
                "error": "无法计算边界框",
                "metadata": metadata
            }

        # 3. 构建图层元数据
        layer_metadata = {
            "feature_count": metadata["feature_count"],
            "geometry_type": metadata["geometry_type"],
            "bounds": metadata["bounds"],
            "attribute_names": attribute_names or [],
            "srid": metadata["srid"],
            "validation_confidence": validation_result.query_type.value
        }

        return {
            "status": "success",
            "layer_name": layer_name,
            "metadata": layer_metadata,
            "query_type": validation_result.query_type.value,
            "is_safe": True
        }

    except Exception as e:
        logger.error(f"PostGIS图层处理失败: {e}")
        return {
            "status": "error",
            "error": f"处理图层时发生错误: {str(e)}",
            "metadata": None
        }

# 向后兼容的包装函数
async def check_postgis_query_safety(pg_conn: asyncpg.Connection, query: str) -> Dict[str, Any]:
    """
    检查PostGIS查询安全性（向后兼容）

    Args:
        pg_conn: PostgreSQL连接
        query: 查询字符串

    Returns:
        安全检查结果
    """
    try:
        processor = SecurePostGISProcessor(pg_conn, ValidationLevel.STRICT)
        validation_result, _ = await processor.validate_and_prepare_query(query)

        return {
            "is_safe": validation_result.is_valid,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "query_type": validation_result.query_type.value,
            "validation_level": validation_result.validation_level.value
        }

    except Exception as e:
        logger.error(f"查询安全检查失败: {e}")
        return {
            "is_safe": False,
            "errors": [str(e)],
            "warnings": [],
            "query_type": "unknown",
            "validation_level": "strict"
        }

def escape_sql_identifier(identifier: str) -> str:
    """
    转义SQL标识符，防止注入

    Args:
        identifier: 标识符（表名、列名等）

    Returns:
        转义后的标识符
    """
    # 只允许字母数字下划线
    if not identifier.replace('_', '').replace('-', '').isalnum():
        raise ValueError(f"非法的SQL标识符: {identifier}")

    # 使用双引号包围标识符
    return f'"{identifier}"'

def validate_table_name(table_name: str) -> bool:
    """
    验证表名是否合法

    Args:
        table_name: 表名

    Returns:
        是否合法
    """
    # 只允许字母数字下划线
    return table_name.replace('_', '').isalnum()

def validate_column_name(column_name: str) -> bool:
    """
    验证列名是否合法

    Args:
        column_name: 列名

    Returns:
        是否合法
    """
    # 只允许字母数字下划线
    return column_name.replace('_', '').isalnum()

# 危险函数黑名单（不应在查询中使用）
DANGEROUS_FUNCTIONS = {
    'pg_sleep', 'pg_sleep_for', 'pg_sleep_until',
    'lo_import', 'lo_export', 'lo_unlink',
    'system', 'exec', 'eval',
    'current_database', 'current_schema', 'current_user',
    'session_user', 'inet_server_addr', 'inet_server_port'
}

def check_function_safety(function_name: str) -> bool:
    """
    检查函数是否安全

    Args:
        function_name: 函数名

    Returns:
        是否安全
    """
    return function_name.lower() not in DANGEROUS_FUNCTIONS

# 注入攻击模式黑名单
INJECTION_PATTERNS = [
    r';',
    r'--',
    r'/\*',
    r'\*/',
    r'@@',
    r'char\s*\(',
    r'exec\s*\(',
    r'execute\s+',
    r'sp_',
    r'xp_'
]

def check_injection_patterns(query: str) -> List[str]:
    """
    检查查询中的注入攻击模式

    Args:
        query: SQL查询字符串

    Returns:
        发现的可疑模式列表
    """
    import re
    found_patterns = []

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            found_patterns.append(pattern)

    return found_patterns

# 便捷函数
async def safe_execute_postgis_query(pg_conn: asyncpg.Connection, query: str,
                                   bounds: Dict[str, float] = None,
                                   limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
    """
    安全执行PostGIS查询

    Args:
        pg_conn: PostgreSQL连接
        query: 基础查询
        bounds: 空间边界框
        limit: 限制数量
        offset: 偏移量

    Returns:
        查询结果
    """
    processor = SecurePostGISProcessor(pg_conn, ValidationLevel.STRICT)
    return await processor.execute_spatial_query(query, bounds, limit, offset)

async def safe_get_feature_count(pg_conn: asyncpg.Connection, query: str,
                               bounds: Dict[str, float] = None) -> int:
    """
    安全获取要素数量

    Args:
        pg_conn: PostgreSQL连接
        query: 基础查询
        bounds: 空间边界框

    Returns:
        要素数量
    """
    processor = SecurePostGISProcessor(pg_conn, ValidationLevel.STRICT)
    return await processor.get_spatial_metadata(query)["feature_count"]
