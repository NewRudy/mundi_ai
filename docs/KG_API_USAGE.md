# Knowledge Graph API Usage Guide

本文档说明如何使用新开发的知识图谱 API 端点。

## 概览

知识图谱 API 提供以下功能:
- **配置管理**: 列出和读取 knowledge_config/ 目录下的配置文件
- **Schema 管理**: 初始化 Neo4j 约束和索引,查看 schema 信息
- **图谱操作**: 应用 ontology JSON 和 YAML 配置,摄取实例和关系
- **查询可视化**: 获取图谱统计,搜索节点,提取子图

## API 端点

### 1. 配置文件管理

#### 列出所有配置文件
```
GET /api/kg/configs?subdir=config
```

响应示例:
```json
{
  "items": [
    {
      "name": "master-mapping.yml",
      "type": "yaml",
      "rel_path": "config/master-mapping.yml",
      "size_bytes": 1234,
      "mtime": "2025-01-22T08:00:00"
    }
  ],
  "total": 15,
  "base_dir": "knowledge_config"
}
```

#### 读取特定配置文件
```
GET /api/kg/configs/{rel_path}
```

示例: `GET /api/kg/configs/电站时空知识图谱.json`

响应示例:
```json
{
  "name": "电站时空知识图谱.json",
  "type": "json",
  "rel_path": "电站时空知识图谱.json",
  "content": { ... parsed JSON ... },
  "raw_content": "... original text ..."
}
```

### 2. Schema 管理

#### 初始化约束和索引
```
POST /api/kg/schema/init
```

创建以下约束和索引:
- 唯一约束: Ontology, Table, Instance, Dataset, Location, Concept, TimePeriod 的 id 字段
- 索引: name, table_name, pg_id 等常用搜索字段

响应示例:
```json
{
  "constraints_created": ["unique_ontology_id", "unique_table_id", ...],
  "indexes_created": ["ontology_name_idx", "table_name_idx", ...],
  "errors": []
}
```

#### 查看 Schema 信息
```
GET /api/kg/schema/info
```

响应示例:
```json
{
  "constraints": [...],
  "indexes": [...],
  "labels": ["Ontology", "Table", "Instance", ...],
  "relationship_types": ["IS_A", "HAS_TABLE", "INSTANCE_OF", ...]
}
```

### 3. 图谱构建

#### 应用 Ontology JSON
```
POST /api/kg/apply-ontology-json
Content-Type: application/json

{
  "ontology_json": {
    "id": "001",
    "name": "根节点",
    "englishName": "Root",
    "subclass": [...]
  }
}
```

响应:
```json
{
  "ontology_created": 50,
  "relations_created": 49
}
```

#### 应用 YAML 配置
```
POST /api/kg/apply-config
Content-Type: application/json

{
  "config_yaml": "version: '0.1'\nontology_nodes:\n  - id: '001'\n    name: 'Root'\n..."
}
```

#### 批量插入实例节点
```
POST /api/kg/upsert-instances
Content-Type: application/json

[
  {
    "table_name": "power_station",
    "pg_id": "123",
    "name": "某电站",
    "properties": {
      "capacity_mw": 500,
      "location": "某市"
    }
  }
]
```

#### 摄取空间关系
```
POST /api/kg/relationships/spatial
Content-Type: application/json

[
  {
    "source": {"table_name": "power_station", "pg_id": "123"},
    "target": {"table_name": "transmission_line", "pg_id": "456"},
    "type": "CONNECTED_TO",
    "properties": {"distance_km": 5.2}
  }
]
```

### 4. 图谱查询和可视化

#### 获取图谱统计
```
GET /api/kg/graph/stats
```

响应示例:
```json
{
  "nodes": {
    "Ontology": 50,
    "Table": 20,
    "Instance": 1000
  },
  "relationships": {
    "IS_A": 49,
    "HAS_TABLE": 20,
    "INSTANCE_OF": 1000
  },
  "total_nodes": 1070,
  "total_relationships": 1069
}
```

#### 搜索节点
```
GET /api/kg/graph/search?name=电站&labels=Ontology,Table&limit=20&offset=0
```

参数:
- `name` (可选): 按名称搜索 (部分匹配)
- `labels` (可选): 逗号分隔的标签列表
- `limit` (默认100, 最大1000): 返回结果数量
- `offset` (默认0): 分页偏移

响应示例:
```json
{
  "nodes": [
    {
      "id": "ontology:001_003_003",
      "labels": ["Ontology"],
      "name": "电站",
      "english_name": "PowerStation",
      "created_at": "2025-01-22T08:00:00"
    }
  ],
  "page": {
    "limit": 20,
    "offset": 0,
    "total": 5,
    "has_more": false
  }
}
```

#### 提取子图
```
GET /api/kg/graph/subgraph?root_id=ontology:001&depth=2&labels=Ontology,Table&limit=200&offset=0
```

参数:
- `root_id` (必需): 根节点 ID
- `depth` (默认2, 范围1-3): 遍历深度
- `labels` (可选): 逗号分隔的标签过滤
- `limit` (默认200, 最大1000): 最大节点数
- `offset` (默认0): 分页偏移

响应示例:
```json
{
  "nodes": [
    {
      "id": "ontology:001",
      "labels": ["Ontology"],
      "name": "根节点"
    },
    {
      "id": "ontology:001_003",
      "labels": ["Ontology"],
      "name": "基础设施"
    }
  ],
  "relationships": [
    {
      "id": "rel-uuid-123",
      "type": "IS_A",
      "start_node_id": "ontology:001_003",
      "end_node_id": "ontology:001",
      "created_at": "2025-01-22T08:00:00"
    }
  ],
  "page": {
    "limit": 200,
    "offset": 0,
    "has_more": false
  },
  "meta": {
    "root_id": "ontology:001",
    "depth": 2,
    "node_count": 2,
    "relationship_count": 1
  }
}
```

## 节点和关系约定

### 节点 ID 格式
- Ontology: `ontology:{ontology_id}` (如 `ontology:001_003_003`)
- Table: `table:{schema}.{table_name}` (如 `table:public.power_station`)
- Instance: `instance:{schema}.{table}:{pg_id}` (如 `instance:public.power_station:123`)

### 标签 (Labels)
- `Ontology`: 本体节点
- `Table`: 表映射节点
- `Instance`: 实例节点
- `Location`, `Dataset`, `Concept`, `TimePeriod`: 其他领域节点

### 关系类型 (Relationship Types)
- `IS_A`: 本体层次 (子类→父类)
- `HAS_TABLE`: 本体→表映射
- `INSTANCE_OF`: 实例→表
- `CONTAINS`, `ADJACENT_TO`, `RELATED_TO`: 空间关系
- `OCCURS_DURING`: 时间关系

## 安全和限制

### 配置文件访问
- 仅允许访问 `knowledge_config/` 目录
- 禁止 `..` 和绝对路径
- 最大文件大小: 2MB
- 仅支持 `.yml`, `.yaml`, `.json` 格式

### 查询限制
- 子图提取最大深度: 3
- 单次查询最大节点数: 1000
- 单次查询最大关系数: 4000
- 所有 Cypher 查询均参数化,防止注入

## 典型工作流

### 1. 初始化
```bash
# 1. 初始化 schema
POST /api/kg/schema/init

# 2. 查看当前 schema
GET /api/kg/schema/info
```

### 2. 导入本体
```bash
# 1. 列出配置文件
GET /api/kg/configs

# 2. 读取 ontology JSON
GET /api/kg/configs/电站时空知识图谱.json

# 3. 应用 ontology
POST /api/kg/apply-ontology-json
```

### 3. 导入表映射
```bash
# 1. 读取 master mapping
GET /api/kg/configs/config/master-mapping.yml

# 2. 应用配置
POST /api/kg/apply-config
```

### 4. 摄取数据
```bash
# 1. 批量插入实例
POST /api/kg/upsert-instances

# 2. 添加空间关系
POST /api/kg/relationships/spatial
```

### 5. 查询可视化
```bash
# 1. 获取统计
GET /api/kg/graph/stats

# 2. 搜索节点
GET /api/kg/graph/search?name=电站

# 3. 提取子图
GET /api/kg/graph/subgraph?root_id=ontology:001&depth=2
```

## 测试

运行测试脚本:
```bash
python test_kg_api.py
```

测试覆盖:
- Schema 初始化和查询
- 配置文件列表和读取
- 图谱统计
- 节点搜索
- 子图提取

## 下一步

- 前端 UI: `/kg/new` (配置选择和应用) 和 `/kg/overview` (统计和可视化)
- 实例摄取 UI: 从 PostgreSQL 表批量导入
- 空间分析集成: 从 QGIS 结果自动生成关系
- WebSocket 进度通知: 大规模导入时的实时反馈
