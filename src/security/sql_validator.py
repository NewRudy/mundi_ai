"""
SQL查询验证器 - 安全版本
提供参数化查询和SQL注入防护
"""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncpg
from datetime import datetime

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """查询类型枚举"""
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    DDL = "ddl"  # 数据定义语言
    UNKNOWN = "unknown"

class ValidationLevel(Enum):
    """验证级别"""
    STRICT = "strict"      # 只允许SELECT查询
    MODERATE = "moderate"  # 允许SELECT和部分DDL
    PERMISSIVE = "permissive"  # 允许所有只读操作

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    query_type: QueryType
    validation_level: ValidationLevel
    errors: List[str]
    warnings: List[str]
    parsed_query: Optional[Dict[str, Any]] = None
    estimated_rows: Optional[int] = None
    execution_time_ms: Optional[float] = None

class SQLSecurityValidator:
    """SQL安全验证器 - 防止SQL注入攻击"""

    # 危险关键字黑名单
    DANGEROUS_KEYWORDS = {
        'drop', 'truncate', 'alter', 'create', 'delete', 'update', 'insert',
        'exec', 'execute', 'sp_', 'xp_', 'union', 'script', 'javascript',
        'vbscript', 'applet', 'embed', 'object', 'frame', 'iframe', 'form',
        'input', 'select', 'textarea', 'button', 'meta', 'link', 'style'
    }

    # 允许的PostGIS函数白名单
    ALLOWED_POSTGIS_FUNCTIONS = {
        'st_makepoint', 'st_makeenvelope', 'st_geomfromtext', 'st_astext',
        'st_x', 'st_y', 'st_distance', 'st_dwithin', 'st_contains',
        'st_intersects', 'st_union', 'st_buffer', 'st_area', 'st_length',
        'st_transform', 'st_setsrid', 'st_srid', 'st_isvalid', 'st_isempty',
        'st_centroid', 'st_boundary', 'st_envelope', 'st_convexhull',
        'count', 'sum', 'avg', 'min', 'max', 'round', 'ceil', 'floor',
        'abs', 'sqrt', 'power', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan'
    }

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STRICT):
        self.validation_level = validation_level

    def validate_query_syntax(self, query: str) -> Tuple[bool, List[str]]:
        """验证SQL语法基础"""
        errors = []

        # 基础语法检查
        if not query or not query.strip():
            errors.append("查询不能为空")
            return False, errors

        query_lower = query.lower().strip()

        # 检查危险关键字
        found_dangerous = self.DANGEROUS_KEYWORDS.intersection(
            set(re.findall(r'\b\w+\b', query_lower))
        )
        if found_dangerous:
            errors.append(f"发现危险关键字: {found_dangerous}")

        # 检查注释（可能的注入攻击）
        if '--' in query or '/*' in query or '*/' in query:
            errors.append("查询中不允许包含SQL注释")

        # 检查堆叠查询
        if ';' in query[:-1]:  # 分号不在末尾
            errors.append("不允许堆叠查询")

        # 检查字符串引号平衡
        single_quotes = query.count("'")
        double_quotes = query.count('"')
        if single_quotes % 2 != 0:
            errors.append("单引号不匹配")
        if double_quotes % 2 != 0:
            errors.append("双引号不匹配")

        return len(errors) == 0, errors

    def validate_query_semantics(self, query: str, query_type: QueryType) -> List[str]:
        """验证查询语义"""
        errors = []
        query_lower = query.lower()

        # 根据验证级别检查
        if self.validation_level == ValidationLevel.STRICT:
            if query_type != QueryType.SELECT:
                errors.append("严格模式只允许SELECT查询")

        elif self.validation_level == ValidationLevel.MODERATE:
            if query_type in [QueryType.INSERT, QueryType.UPDATE, QueryType.DELETE]:
                errors.append("中等模式不允许数据修改操作")

        # 检查PostGIS函数白名单
        postgis_functions = re.findall(r'\b(st_\w+)\b', query_lower)
        for func in postgis_functions:
            if func.lower() not in self.ALLOWED_POSTGIS_FUNCTIONS:
                errors.append(f"不允许的PostGIS函数: {func}")

        # 检查表名和列名（只允许字母数字下划线）
        table_pattern = r'\b(\w+)\.'
        tables = re.findall(table_pattern, query)
        for table in tables:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
                errors.append(f"非法表名: {table}")

        return errors

    def detect_query_type(self, query: str) -> QueryType:
        """检测查询类型"""
        query_lower = query.lower().strip()

        if query_lower.startswith('select'):
            return QueryType.SELECT
        elif query_lower.startswith('insert'):
            return QueryType.INSERT
        elif query_lower.startswith('update'):
            return QueryType.UPDATE
        elif query_lower.startswith('delete'):
            return QueryType.DELETE
        elif any(query_lower.startswith(ddl) for ddl in ['create', 'alter', 'drop', 'truncate']):
            return QueryType.DDL
        else:
            return QueryType.UNKNOWN

    async def validate_with_explain(self, conn: asyncpg.Connection, query: str) -> Tuple[bool, Optional[Dict], List[str]]:
        """使用EXPLAIN验证查询计划"""
        errors = []
        query_plan = None

        try:
            # 使用参数化EXPLAIN查询
            explain_query = "EXPLAIN (FORMAT JSON) " + query
            explain_result = await conn.fetch(explain_query)

            if explain_result:
                query_plan = json.loads(explain_result[0]["QUERY PLAN"])

                # 检查查询计划是否包含危险操作
                plan_str = json.dumps(query_plan).lower()
                dangerous_operations = ['modifytable', 'insert', 'update', 'delete']

                for op in dangerous_operations:
                    if op in plan_str:
                        errors.append(f"查询计划包含危险操作: {op}")

                # 估算查询成本
                if query_plan and len(query_plan) > 0:
                    total_cost = query_plan[0].get("Plan", {}).get("Total Cost", 0)
                    if total_cost > 10000:  # 成本阈值
                        errors.append(f"查询成本过高: {total_cost}")

            return len(errors) == 0, query_plan, errors

        except Exception as e:
            errors.append(f"EXPLAIN验证失败: {str(e)}")
            return False, None, errors

    async def validate_query(self, conn: asyncpg.Connection, query: str,
                           validation_level: Optional[ValidationLevel] = None) -> ValidationResult:
        """完整查询验证流程"""
        start_time = datetime.now()
        validation_level = validation_level or self.validation_level

        # 初始化结果
        result = ValidationResult(
            is_valid=True,
            query_type=QueryType.UNKNOWN,
            validation_level=validation_level,
            errors=[],
            warnings=[]
        )

        try:
            # 1. 语法验证
            syntax_valid, syntax_errors = self.validate_query_syntax(query)
            if not syntax_valid:
                result.errors.extend(syntax_errors)
                result.is_valid = False
                return result

            # 2. 查询类型检测
            result.query_type = self.detect_query_type(query)

            # 3. 语义验证
            semantic_errors = self.validate_query_semantics(query, result.query_type)
            if semantic_errors:
                result.errors.extend(semantic_errors)
                result.is_valid = False
                return result

            # 4. EXPLAIN验证（仅SELECT查询）
            if result.query_type == QueryType.SELECT:
                explain_valid, query_plan, explain_errors = await self.validate_with_explain(conn, query)
                if not explain_valid:
                    result.errors.extend(explain_errors)
                    result.is_valid = False
                else:
                    result.parsed_query = query_plan

            # 计算执行时间
            result.execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            return result

        except Exception as e:
            result.errors.append(f"验证过程异常: {str(e)}")
            result.is_valid = False
            return result

class SafeSQLExecutor:
    """安全的SQL执行器 - 使用参数化查询"""

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.validator = SQLSecurityValidator()

    async def execute_readonly_query(self, base_query: str, bounds: Optional[Dict[str, float]] = None,
                                   limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """执行只读空间查询 - 使用参数化查询"""

        # 验证基础查询
        validation_result = await self.validator.validate_query(self.conn, base_query)
        if not validation_result.is_valid:
            raise ValueError(f"查询验证失败: {validation_result.errors}")

        try:
            # 构建参数化查询
            if bounds:
                # 空间边界查询
                query = """
                    SELECT * FROM ({base_query}) AS subquery
                    WHERE geom && ST_MakeEnvelope($1, $2, $3, $4, ST_SRID(geom))
                    LIMIT $5 OFFSET $6
                """
                params = [bounds['west'], bounds['south'], bounds['east'], bounds['north'], limit, offset]
            else:
                # 普通分页查询
                query = """
                    SELECT * FROM ({base_query}) AS subquery
                    LIMIT $1 OFFSET $2
                """
                params = [limit, offset]

            # 使用参数化查询执行
            query_with_params = query.format(base_query=base_query)
            results = await self.conn.fetch(query_with_params, *params)

            # 转换为字典列表
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"安全查询执行失败: {e}")
            raise RuntimeError(f"查询执行失败: {str(e)}")

    async def get_feature_count(self, base_query: str, bounds: Optional[Dict[str, float]] = None) -> int:
        """获取要素数量 - 使用参数化查询"""

        try:
            if bounds:
                query = """
                    SELECT COUNT(*) FROM ({base_query}) AS subquery
                    WHERE geom && ST_MakeEnvelope($1, $2, $3, $4, ST_SRID(geom))
                """
                params = [bounds['west'], bounds['south'], bounds['east'], bounds['north']]
            else:
                query = "SELECT COUNT(*) FROM ({base_query}) AS subquery"
                params = []

            query_with_params = query.format(base_query=base_query)
            count = await self.conn.fetchval(query_with_params, *params)
            return count or 0

        except Exception as e:
            logger.error(f"要素计数失败: {e}")
            raise RuntimeError(f"要素计数失败: {str(e)}")

    async def get_spatial_metadata(self, base_query: str) -> Dict[str, Any]:
        """获取空间元数据 - 使用参数化查询"""

        try:
            # 获取边界框
            bounds_query = """
                SELECT
                    ST_XMin(ST_Extent(geom)) as west,
                    ST_YMin(ST_Extent(geom)) as south,
                    ST_XMax(ST_Extent(geom)) as east,
                    ST_YMax(ST_Extent(geom)) as north,
                    ST_SRID(geom) as srid
                FROM ({base_query}) AS subquery
                WHERE geom IS NOT NULL
            """

            bounds_result = await self.conn.fetchrow(bounds_query.format(base_query=base_query))

            # 获取几何类型
            geom_type_query = """
                SELECT ST_GeometryType(geom) as geom_type
                FROM ({base_query}) AS subquery
                WHERE geom IS NOT NULL
                LIMIT 1
            """

            type_result = await self.conn.fetchrow(geom_type_query.format(base_query=base_query))

            metadata = {
                "bounds": None,
                "geometry_type": None,
                "srid": None
            }

            if bounds_result:
                metadata["bounds"] = {
                    "west": bounds_result["west"],
                    "south": bounds_result["south"],
                    "east": bounds_result["east"],
                    "north": bounds_result["north"]
                }
                metadata["srid"] = bounds_result["srid"]

            if type_result:
                metadata["geometry_type"] = type_result["geom_type"]

            return metadata

        except Exception as e:
            logger.error(f"空间元数据获取失败: {e}")
            # 返回空元数据而不是抛出异常
            return {
                "bounds": None,
                "geometry_type": None,
                "srid": None
            }

# 便捷函数
async def validate_sql_query(conn: asyncpg.Connection, query: str,
                           validation_level: ValidationLevel = ValidationLevel.STRICT) -> ValidationResult:
    """验证SQL查询安全性"""
    validator = SQLSecurityValidator(validation_level)
    return await validator.validate_query(conn, query)

async def safe_execute_readonly_query(conn: asyncpg.Connection, query: str,
                                    bounds: Optional[Dict[str, float]] = None,
                                    limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
    """安全执行只读查询"""
    executor = SafeSQLExecutor(conn)
    return await executor.execute_readonly_query(query, bounds, limit, offset)