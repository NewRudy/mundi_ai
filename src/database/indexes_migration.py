"""
数据库索引优化迁移
为空间查询和高频查询创建性能索引
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
import asyncpg
from src.core.connection_pool import get_postgres_pool

logger = logging.getLogger(__name__)

class SpatialIndexOptimizer:
    """空间索引优化器"""

    # 空间索引定义
    SPATIAL_INDEXES = [
        {
            "table": "monitoring_stations",
            "column": "geom",
            "index_type": "GIST",
            "name": "idx_monitoring_stations_geom",
            "condition": "geom IS NOT NULL",
            "description": "监测站空间位置索引"
        },
        {
            "table": "water_level_stations",
            "column": "geom",
            "index_type": "GIST",
            "name": "idx_water_level_stations_geom",
            "condition": "geom IS NOT NULL",
            "description": "水位站空间位置索引"
        },
        {
            "table": "flood_risk_areas",
            "column": "location",
            "index_type": "GIST",
            "name": "idx_flood_risk_areas_location",
            "condition": "location IS NOT NULL",
            "description": "洪水风险区域空间索引"
        },
        {
            "table": "spatial_features",
            "column": "geom",
            "index_type": "GIST",
            "name": "idx_spatial_features_geom",
            "condition": "geom IS NOT NULL",
            "description": "空间要素通用索引"
        },
        {
            "table": "historical_flood_events",
            "column": "geom",
            "index_type": "GIST",
            "name": "idx_historical_flood_events_geom",
            "condition": "geom IS NOT NULL",
            "description": "历史洪水事件空间索引"
        }
    ]

    # 复合索引定义
    COMPOSITE_INDEXES = [
        {
            "table": "monitoring_stations",
            "columns": ["type", "status", "last_updated"],
            "name": "idx_monitoring_stations_type_status_updated",
            "description": "监测站类型状态时间复合索引"
        },
        {
            "table": "flood_risk_areas",
            "columns": ["severity", "last_updated"],
            "name": "idx_flood_risk_severity_updated",
            "description": "洪水风险等级时间复合索引"
        },
        {
            "table": "water_level_stations",
            "columns": ["status", "current_level", "alert_level"],
            "name": "idx_water_level_status_levels",
            "description": "水位站状态和等级复合索引"
        },
        {
            "table": "messages",
            "columns": ["conversation_id", "created_at"],
            "name": "idx_messages_conversation_created",
            "description": "消息会话时间复合索引"
        },
        {
            "table": "layers",
            "columns": ["map_id", "type", "visible"],
            "name": "idx_layers_map_type_visible",
            "description": "图层地图类型可见性复合索引"
        }
    ]

    # 单列索引定义
    SINGLE_COLUMN_INDEXES = [
        {
            "table": "users",
            "column": "email",
            "name": "idx_users_email_unique",
            "unique": True,
            "description": "用户邮箱唯一索引"
        },
        {
            "table": "users",
            "column": "username",
            "name": "idx_users_username_unique",
            "unique": True,
            "description": "用户名唯一索引"
        },
        {
            "table": "projects",
            "column": "user_id",
            "name": "idx_projects_user_id",
            "description": "项目用户ID索引"
        },
        {
            "table": "maps",
            "column": "project_id",
            "name": "idx_maps_project_id",
            "description": "地图项目ID索引"
        },
        {
            "table": "conversations",
            "column": "user_id",
            "name": "idx_conversations_user_id",
            "description": "会话用户ID索引"
        },
        {
            "table": "project_postgres_connections",
            "column": "user_id",
            "name": "idx_connections_user_id",
            "description": "数据库连接用户ID索引"
        }
    ]

    # 时间序列索引
    TIME_SERIES_INDEXES = [
        {
            "table": "water_level_measurements",
            "column": "measurement_time",
            "name": "idx_water_level_measurement_time",
            "description": "水位测量时间索引"
        },
        {
            "table": "flood_events",
            "column": "occurrence_date",
            "name": "idx_flood_events_date",
            "description": "洪水事件日期索引"
        },
        {
            "table": "messages",
            "column": "created_at",
            "name": "idx_messages_created_at",
            "description": "消息创建时间索引"
        }
    ]

    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def check_index_exists(self, index_name: str) -> bool:
        """检查索引是否存在"""
        try:
            result = await self.conn.fetchrow("""
                SELECT 1 FROM pg_indexes WHERE indexname = $1
            """, index_name)
            return result is not None
        except Exception as e:
            logger.error(f"检查索引存在性失败 {index_name}: {e}")
            return False

    async def create_spatial_index(self, index_config: Dict[str, Any]) -> bool:
        """创建空间索引"""
        index_name = index_config["name"]
        table = index_config["table"]
        column = index_config["column"]
        index_type = index_config["index_type"]
        condition = index_config.get("condition", "")

        try:
            # 检查索引是否已存在
            if await self.check_index_exists(index_name):
                logger.info(f"索引 {index_name} 已存在，跳过创建")
                return True

            # 构建索引创建SQL
            sql = f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name}
                ON {table} USING {index_type} ({column})
            """

            if condition:
                sql += f" WHERE {condition}"

            logger.info(f"创建空间索引: {index_name} - {index_config['description']}")
            await self.conn.execute(sql)
            logger.info(f"✅ 空间索引 {index_name} 创建成功")
            return True

        except Exception as e:
            logger.error(f"创建空间索引 {index_name} 失败: {e}")
            return False

    async def create_composite_index(self, index_config: Dict[str, Any]) -> bool:
        """创建复合索引"""
        index_name = index_config["name"]
        table = index_config["table"]
        columns = index_config["columns"]

        try:
            # 检查索引是否已存在
            if await self.check_index_exists(index_name):
                logger.info(f"索引 {index_name} 已存在，跳过创建")
                return True

            # 构建列列表
            columns_str = ", ".join(columns)

            sql = f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name}
                ON {table} ({columns_str})
            """

            logger.info(f"创建复合索引: {index_name} - {index_config['description']}")
            await self.conn.execute(sql)
            logger.info(f"✅ 复合索引 {index_name} 创建成功")
            return True

        except Exception as e:
            logger.error(f"创建复合索引 {index_name} 失败: {e}")
            return False

    async def create_single_column_index(self, index_config: Dict[str, Any]) -> bool:
        """创建单列索引"""
        index_name = index_config["name"]
        table = index_config["table"]
        column = index_config["column"]
        unique = index_config.get("unique", False)

        try:
            # 检查索引是否已存在
            if await self.check_index_exists(index_name):
                logger.info(f"索引 {index_name} 已存在，跳过创建")
                return True

            unique_str = "UNIQUE " if unique else ""
            sql = f"""
                CREATE {unique_str}INDEX CONCURRENTLY IF NOT EXISTS {index_name}
                ON {table} ({column})
            """

            logger.info(f"创建单列索引: {index_name} - {index_config['description']}")
            await self.conn.execute(sql)
            logger.info(f"✅ 单列索引 {index_name} 创建成功")
            return True

        except Exception as e:
            logger.error(f"创建单列索引 {index_name} 失败: {e}")
            return False

    async def create_time_series_index(self, index_config: Dict[str, Any]) -> bool:
        """创建时间序列索引"""
        index_name = index_config["name"]
        table = index_config["table"]
        column = index_config["column"]

        try:
            # 检查索引是否已存在
            if await self.check_index_exists(index_name):
                logger.info(f"索引 {index_name} 已存在，跳过创建")
                return True

            # 时间序列索引通常需要BRIN索引以提高性能
            sql = f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name}
                ON {table} USING BRIN ({column})
            """

            logger.info(f"创建时间序列索引: {index_name} - {index_config['description']}")
            await self.conn.execute(sql)
            logger.info(f"✅ 时间序列索引 {index_name} 创建成功")
            return True

        except Exception as e:
            logger.error(f"创建时间序列索引 {index_name} 失败: {e}")
            return False

    async def analyze_table_stats(self, table_name: str) -> bool:
        """分析表统计信息"""
        try:
            logger.info(f"分析表统计信息: {table_name}")
            await self.conn.execute(f"ANALYZE {table_name}")
            logger.info(f"✅ 表 {table_name} 统计信息更新成功")
            return True
        except Exception as e:
            logger.error(f"分析表统计信息失败 {table_name}: {e}")
            return False

    async def get_index_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            # 获取索引使用情况统计
            index_stats = await self.conn.fetch("""
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    indexdef,
                    tablespace,
                    indexprs,
                    indpred,
                    indisunique,
                    indisprimary,
                    indisexclusion,
                    indimmediate,
                    indisclustered,
                    indisvalid,
                    indcheckxmin,
                    indisready,
                    indislive,
                    indisreplident,
                    indoption,
                    indexprs,
                    indpred
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname
            """)

            # 获取索引大小统计
            index_sizes = await self.conn.fetch("""
                SELECT
                    indexname,
                    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
                FROM pg_indexes
                WHERE schemaname = 'public'
            """)

            return {
                "total_indexes": len(index_stats),
                "index_list": [dict(row) for row in index_stats],
                "index_sizes": [dict(row) for row in index_sizes],
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"获取索引统计信息失败: {e}")
            return {"error": str(e)}

    async def create_all_indexes(self) -> Dict[str, Any]:
        """创建所有索引"""
        logger.info("🚀 开始创建数据库索引优化...")

        results = {
            "spatial_indexes": {"created": 0, "failed": 0, "skipped": 0, "details": []},
            "composite_indexes": {"created": 0, "failed": 0, "skipped": 0, "details": []},
            "single_column_indexes": {"created": 0, "failed": 0, "skipped": 0, "details": []},
            "time_series_indexes": {"created": 0, "failed": 0, "skipped": 0, "details": []},
            "start_time": datetime.utcnow(),
            "end_time": None
        }

        # 1. 创建空间索引
        logger.info("🗺️ 创建空间索引...")
        for index_config in self.SPATIAL_INDEXES:
            success = await self.create_spatial_index(index_config)
            if success:
                results["spatial_indexes"]["created"] += 1
                results["spatial_indexes"]["details"].append({
                    "name": index_config["name"],
                    "status": "created",
                    "description": index_config["description"]
                })
            else:
                results["spatial_indexes"]["failed"] += 1
                results["spatial_indexes"]["details"].append({
                    "name": index_config["name"],
                    "status": "failed",
                    "description": index_config["description"]
                })

        # 2. 创建复合索引
        logger.info("🔗 创建复合索引...")
        for index_config in self.COMPOSITE_INDEXES:
            success = await self.create_composite_index(index_config)
            if success:
                results["composite_indexes"]["created"] += 1
                results["composite_indexes"]["details"].append({
                    "name": index_config["name"],
                    "status": "created",
                    "description": index_config["description"]
                })
            else:
                results["composite_indexes"]["failed"] += 1
                results["composite_indexes"]["details"].append({
                    "name": index_config["name"],
                    "status": "failed",
                    "description": index_config["description"]
                })

        # 3. 创建单列索引
        logger.info("📊 创建单列索引...")
        for index_config in self.SINGLE_COLUMN_INDEXES:
            success = await self.create_single_column_index(index_config)
            if success:
                results["single_column_indexes"]["created"] += 1
                results["single_column_indexes"]["details"].append({
                    "name": index_config["name"],
                    "status": "created",
                    "description": index_config["description"]
                })
            else:
                results["single_column_indexes"]["failed"] += 1
                results["single_column_indexes"]["details"].append({
                    "name": index_config["name"],
                    "status": "failed",
                    "description": index_config["description"]
                })

        # 4. 创建时间序列索引
        logger.info("⏰ 创建时间序列索引...")
        for index_config in self.TIME_SERIES_INDEXES:
            success = await self.create_time_series_index(index_config)
            if success:
                results["time_series_indexes"]["created"] += 1
                results["time_series_indexes"]["details"].append({
                    "name": index_config["name"],
                    "status": "created",
                    "description": index_config["description"]
                })
            else:
                results["time_series_indexes"]["failed"] += 1
                results["time_series_indexes"]["details"].append({
                    "name": index_config["name"],
                    "status": "failed",
                    "description": index_config["description"]
                })

        # 5. 分析表统计信息
        logger.info("📈 分析表统计信息...")
        tables_to_analyze = set()
        for index_list in [self.SPATIAL_INDEXES, self.COMPOSITE_INDEXES,
                          self.SINGLE_COLUMN_INDEXES, self.TIME_SERIES_INDEXES]:
            for index_config in index_list:
                tables_to_analyze.add(index_config["table"])

        for table in tables_to_analyze:
            await self.analyze_table_stats(table)

        # 6. 获取索引统计
        logger.info("📊 获取索引统计信息...")
        index_stats = await self.get_index_stats()

        results["end_time"] = datetime.utcnow()
        results["index_stats"] = index_stats
        results["duration_seconds"] = (results["end_time"] - results["start_time"]).total_seconds()

        # 总结
        total_created = (results["spatial_indexes"]["created"] +
                        results["composite_indexes"]["created"] +
                        results["single_column_indexes"]["created"] +
                        results["time_series_indexes"]["created"])

        total_failed = (results["spatial_indexes"]["failed"] +
                       results["composite_indexes"]["failed"] +
                       results["single_column_indexes"]["failed"] +
                       results["time_series_indexes"]["failed"])

        logger.info(f"🎉 索引优化完成!")
        logger.info(f"   成功创建: {total_created} 个索引")
        logger.info(f"   失败: {total_failed} 个索引")
        logger.info(f"   总耗时: {results['duration_seconds']:.2f} 秒")

        return results

# 便捷的迁移函数
async def migrate_spatial_indexes():
    """执行空间索引迁移"""
    logger.info("开始空间索引优化迁移...")

    try:
        # 获取数据库连接
        conn = get_postgres_pool()
        optimizer = SpatialIndexOptimizer(conn)

        # 执行索引创建
        results = await optimizer.create_all_indexes()

        # 记录结果
        logger.info("空间索引迁移完成")
        return results

    except Exception as e:
        logger.error(f"空间索引迁移失败: {e}")
        raise

if __name__ == "__main__":
    # 运行迁移
    async def main():
        results = await migrate_spatial_indexes()
        print(json.dumps(results, indent=2, default=str))

    asyncio.run(main())