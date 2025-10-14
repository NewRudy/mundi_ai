#!/usr/bin/env python3
"""
测试多模式 PostgreSQL 数据库查询
"""
import asyncio
import asyncpg
import os

async def test_multi_schema_query():
    """测试查询所有模式的表"""
    
    # 从环境变量读取连接信息
    connection_uri = "postgresql://postgres:onlywtx@127.0.0.1:5432/lp_knowledge_dev?sslmode=disable"
    
    if not connection_uri:
        print("❌ 请设置 TEST_POSTGRES_URI 环境变量")
        print("例如: $env:TEST_POSTGRES_URI='postgresql://user:pass@host:port/dbname?sslmode=disable'")
        return
    
    print("=" * 80)
    print("🔍 测试多模式 PostgreSQL 数据库查询")
    print("=" * 80)
    print(f"连接: {connection_uri.split('@')[0].split(':')[0]}@...")
    print()
    
    try:
        # 解析 sslmode
        from urllib.parse import urlparse, parse_qs
        import ssl as _ssl
        
        parsed = urlparse(connection_uri)
        query = parse_qs(parsed.query)
        sslmode = (query.get("sslmode", [None])[0] or "").lower()
        
        ssl_param = False if sslmode == "disable" else True
        
        # 连接数据库
        conn = await asyncpg.connect(connection_uri, ssl=ssl_param)
        
        print("✅ 数据库连接成功！\n")
        
        # 查询所有非系统模式的表
        tables = await conn.fetch(
            """
            SELECT table_schema, table_name, 
                   (SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE columns.table_schema = tables.table_schema 
                      AND columns.table_name = tables.table_name) as column_count
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_type = 'BASE TABLE'
            ORDER BY table_schema, table_name
            """
        )
        
        if not tables:
            print("⚠️  未找到任何用户表")
            await conn.close()
            return
        
        # 按模式分组统计
        schema_stats = {}
        for table in tables:
            schema = table["table_schema"]
            if schema not in schema_stats:
                schema_stats[schema] = {"tables": [], "total_columns": 0}
            schema_stats[schema]["tables"].append(table["table_name"])
            schema_stats[schema]["total_columns"] += table["column_count"]
        
        print(f"📊 数据库统计:")
        print(f"   总模式数: {len(schema_stats)}")
        print(f"   总表数: {len(tables)}")
        print()
        
        # 显示每个模式的详细信息
        print("📁 模式详情:")
        print("-" * 80)
        
        for schema_name, stats in schema_stats.items():
            table_count = len(stats["tables"])
            col_count = stats["total_columns"]
            print(f"\n🗂️  {schema_name}")
            print(f"   表数量: {table_count}")
            print(f"   列总数: {col_count}")
            print(f"   表列表: {', '.join(stats['tables'][:10])}")
            if table_count > 10:
                print(f"            ... 还有 {table_count - 10} 个表")
        
        print("\n" + "=" * 80)
        print("✅ 多模式查询测试完成")
        print("=" * 80)
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_multi_schema_query())

