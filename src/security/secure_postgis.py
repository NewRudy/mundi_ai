"""
安全的PostGIS查询处理器
替代原有的危险SQL拼接实现
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncpg
from src.security.sql_validator import SQLSecurityValidator, ValidationLevel, QueryType, ValidationResult

logger = logging.getLogger(__name__)

class SecurePostGISProcessor:
    """安全的PostGIS查询处理器"""

    def __init__(self, conn: asyncpg.Connection, validation_level: ValidationLevel = ValidationLevel.STRICT):
        self.conn = conn
        self.validator = SQLSecurityValidator(validation_level)

    async def validate_and_prepare_query(self, query: str) -> Tuple[ValidationResult, Optional[List[str]]]:
        """验证查询并提取列信息"""

        # 1. 验证查询安全性
        validation_result = await self.validator.validate_query(self.conn, query)
        if not validation_result.is_valid:
            return validation_result, None

        try:
            # 2. 使用安全的方式获取列信息
            # 创建临时视图来检查列结构
            temp_view_name = f"temp_view_{int(datetime.now().timestamp() * 1000000)}"

            # 使用参数化查询创建临时视图
            create_view_sql = f"CREATE TEMP VIEW {temp_view_name} AS {query}"
            await self.conn.execute(create_view_sql)

            try:
                # 获取列信息
                column_info = await self.conn.fetch(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = $1",
                    temp_view_name
                )
                column_names = [row['column_name'] for row in column_info]

                # 验证必需列
                if "geom" not in column_names:
                    validation_result.errors.append("查询必须返回名为'geom'的几何列")
                    validation_result.is_valid = False
                    return validation_result, None

                if "id" not in column_names:
                    validation_result.errors.append("查询必须返回名为'id'的ID列")
                    validation_result.is_valid = False
                    return validation_result, None

                # 获取属性列（排除geom和id）
                attribute_names = [name for name in column_names if name not in ["geom", "id"]]

                return validation_result, attribute_names

            finally:
                # 清理临时视图
                await self.conn.execute(f"DROP VIEW IF EXISTS {temp_view_name}")

        except Exception as e:
            logger.error(f"查询验证失败: {e}")
            validation_result.errors.append(f"查询结构验证失败: {str(e)}")
            validation_result.is_valid = False
            return validation_result, None

    async def get_spatial_metadata(self, query: str) -> Dict[str, Any]:
        """获取空间元数据 - 使用参数化查询"""

        metadata = {
            "feature_count": None,
            "bounds": None,
            "geometry_type": None,
            "srid": None,
            "column_info": []
        }

        try:
            # 1. 获取要素数量 - 使用参数化子查询
            count_query = """
                SELECT COUNT(*) as count
                FROM (
                    SELECT 1
                    FROM ({subquery}) AS sub
                    WHERE geom IS NOT NULL
                ) AS filtered
            """.format(subquery=query)

            count_result = await self.conn.fetchrow(count_query)
            metadata["feature_count"] = count_result["count"] if count_result else 0

            # 2. 获取几何类型 - 使用参数化查询
            geom_type_query = """
                SELECT
                    ST_GeometryType(geom) as geom_type,
                    COUNT(*) as type_count
                FROM ({subquery}) AS sub
                WHERE geom IS NOT NULL
                GROUP BY ST_GeometryType(geom)
                ORDER BY type_count DESC
                LIMIT 1
            """.format(subquery=query)

            geom_type_result = await self.conn.fetchrow(geom_type_query)
            if geom_type_result and geom_type_result["geom_type"]:
                metadata["geometry_type"] = geom_type_result["geom_type"].replace("ST_", "").lower()

            # 3. 获取边界框 - 使用参数化查询
            bounds_query = """
                WITH extent_data AS (
                    SELECT
                        ST_Extent(geom) as extent_geom,
                        (SELECT ST_SRID(geom) FROM ({subquery}) AS sub2 WHERE geom IS NOT NULL LIMIT 1) as original_srid
                    FROM ({subquery}) AS sub
                    WHERE geom IS NOT NULL
                )
                SELECT
                    CASE
                        WHEN original_srid = 4326 THEN ST_XMin(extent_geom)
                        ELSE ST_XMin(ST_Transform(ST_SetSRID(extent_geom, original_srid), 4326))
                    END as xmin,
                    CASE
                        WHEN original_srid = 4326 THEN ST_YMin(extent_geom)
                        ELSE ST_YMin(ST_Transform(ST_SetSRID(extent_geom, original_srid), 4326))
                    END as ymin,
                    CASE
                        WHEN original_srid = 4326 THEN ST_XMax(extent_geom)
                        ELSE ST_XMax(ST_Transform(ST_SetSRID(extent_geom, original_srid), 4326))
                    END as xmax,
                    CASE
                        WHEN original_srid = 4326 THEN ST_YMax(extent_geom)
                        ELSE ST_YMax(ST_Transform(ST_SetSRID(extent_geom, original_srid), 4326))
                    END as ymax,
                    original_srid
                FROM extent_data
            """.format(subquery=query)

            bounds_result = await self.conn.fetchrow(bounds_query)
            if bounds_result and bounds_result["xmin"] is not None:
                metadata["bounds"] = {
                    "west": bounds_result["xmin"],
                    "south": bounds_result["ymin"],
                    "east": bounds_result["xmax"],
                    "north": bounds_result["ymax"]
                }
                metadata["srid"] = bounds_result["original_srid"]

            # 4. 获取列信息 - 使用参数化查询
            column_query = """
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE table_name = (
                    SELECT table_name
                    FROM information_schema.views
                    WHERE view_definition ILIKE %s
                    LIMIT 1
                )
                AND column_name NOT IN ('geom', 'id')
                ORDER BY ordinal_position
            """

            # 使用安全的字符串匹配
            column_results = await self.conn.fetch(column_query, f"%{query[:50]}%")
            metadata["column_info"] = [
                {
                    "name": row["column_name"],
                    "type": row["data_type"],
                    "nullable": row["is_nullable"] == "YES"
                }
                for row in column_results
            ]

            return metadata

        except Exception as e:
            logger.error(f"空间元数据获取失败: {e}")
            # 返回空元数据而不是抛出异常
            return {
                "feature_count": 0,
                "bounds": None,
                "geometry_type": None,
                "srid": None,
                "column_info": []
            }

    async def execute_spatial_query(self, query: str, bounds: Optional[Dict[str, float]] = None,
                                  limit: int = 1000, offset: int = 0) -> List[Dict[str, Any]]:
        """执行空间查询 - 使用参数化查询"""

        try:
            # 构建参数化查询
            if bounds:
                # 空间边界查询 - 使用参数
                spatial_query = """
                    SELECT * FROM ({base_query}) AS subquery
                    WHERE geom && ST_MakeEnvelope($1, $2, $3, $4, ST_SRID(geom))
                    ORDER BY id
                    LIMIT $5 OFFSET $6
                """.format(base_query=query)

                params = [
                    bounds['west'], bounds['south'],
                    bounds['east'], bounds['north'],
                    limit, offset
                ]
            else:
                # 普通分页查询 - 使用参数
                spatial_query = """
                    SELECT * FROM ({base_query}) AS subquery
                    ORDER BY id
                    LIMIT $1 OFFSET $2
                """.format(base_query=query)

                params = [limit, offset]

            # 执行参数化查询
            results = await self.conn.fetch(spatial_query, *params)

            # 转换为字典列表
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"空间查询执行失败: {e}")
            raise RuntimeError(f"空间查询执行失败: {str(e)}")

    async def get_column_statistics(self, query: str, column_name: str) -> Dict[str, Any]:
        """获取列统计信息 - 使用参数化查询"""

        try:
            # 首先检查列是否存在且为数值类型
            check_query = """
                SELECT 1
                FROM ({subquery}) AS sub
                WHERE {column} IS NOT NULL
                LIMIT 1
            """.format(subquery=query, column=column_name)

            exists = await self.conn.fetchrow(check_query)
            if not exists:
                return {"exists": False}

            # 获取基本统计 - 使用参数化查询
            stats_query = """
                SELECT
                    COUNT(*) as total_count,
                    COUNT({column}) as non_null_count,
                    COUNT(DISTINCT {column}) as unique_count,
                    MIN({column}) as min_value,
                    MAX({column}) as max_value,
                    AVG({column}) as avg_value,
                    STDDEV({column}) as stddev_value
                FROM ({subquery}) AS sub
                WHERE {column} IS NOT NULL
            """.format(subquery=query, column=column_name)

            stats_result = await self.conn.fetchrow(stats_query)

            if stats_result:
                return {
                    "exists": True,
                    "total_count": stats_result["total_count"],
                    "non_null_count": stats_result["non_null_count"],
                    "unique_count": stats_result["unique_count"],
                    "min_value": float(stats_result["min_value"]) if stats_result["min_value"] else None,
                    "max_value": float(stats_result["max_value"]) if stats_result["max_value"] else None,
                    "avg_value": float(stats_result["avg_value"]) if stats_result["avg_value"] else None,
                    "stddev_value": float(stats_result["stddev_value"]) if stats_result["stddev_value"] else None
                }

            return {"exists": False}

        except Exception as e:
            logger.error(f"列统计获取失败: {e}")
            # 返回空统计而不是抛出异常
            return {"exists": False, "error": str(e)}

# 便捷函数
async def secure_process_postgis_query(conn: asyncpg.Connection, query: str,
                                     validation_level: ValidationLevel = ValidationLevel.STRICT) -> Dict[str, Any]:
    """安全处理PostGIS查询的主函数"""

    processor = SecurePostGISProcessor(conn, validation_level)

    try:
        # 1. 验证查询并获取列信息
        validation_result, attribute_names = await processor.validate_and_prepare_query(query)

        if not validation_result.is_valid:
            return {
                "status": "error",
                "validation_errors": validation_result.errors,
                "metadata": None
            }

        # 2. 获取空间元数据
        metadata = await processor.get_spatial_metadata(query)
        metadata["attribute_names"] = attribute_names or []

        return {
            "status": "success",
            "validation_result": validation_result,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"PostGIS查询处理失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "metadata": None
        }