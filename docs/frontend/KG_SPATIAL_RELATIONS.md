# KG Spatial Relations 使用指南

本页提供“空间关系管理”能力：浏览子图中的关系、按类型过滤、删除关系；以及批量导入空间关系。

## 入口
- 侧边栏：Knowledge Graph → Spatial Relations
- 路由：/kg/spatial-relations

## 功能
### Browse（浏览）
1. 选择 Project（可选选择 Neo4j 连接）
2. 按名称和标签搜索节点，点击某个节点作为 Root
3. 选择 Depth（1-3）和关系类型过滤
4. 查看当前子图内的关系表格（Type/Start/End）
5. 可对某条关系执行 Delete（删除）

后端接口：
- GET /api/kg/graph/stats
- GET /api/kg/graph/search?name=&labels=&limit=50
- GET /api/kg/graph/subgraph?root_id=&depth=&limit=500
- DELETE /api/graph/relationships/{relationshipId}

可通过 query 参数 `connection_id` 指定 Neo4j 连接。

### Import（导入）
粘贴 JSON 数组，点击 Validate 验证格式，再点击 Import 调用批量导入。

格式示例：
```json
[
  {
    "source": { "table_name": "power_station", "pg_id": "123" },
    "target": { "table_name": "airport", "pg_id": "A001" },
    "type": "NEARBY",
    "properties": { "distance_km": 7.5 }
  },
  {
    "source": { "node_id": "instance:public.power_station:123" },
    "target": { "node_id": "instance:public.transmission_line:456" },
    "type": "INTERSECTS"
  }
]
```
- 支持类型：CONTAINS、ADJACENT_TO、NEARBY、INTERSECTS、RELATED_TO
- 注意：NEARBY 会映射为 ADJACENT_TO，并在属性中保留 `semantic_type: NEARBY`

后端接口：
- POST /api/kg/relationships/spatial（可选 `connection_id`）

## 注意
- Browse 视图的关系列表基于当前 Root 与 Depth 的“子图”，非全图。
- 导入成功后，如当前已选择 Root，会自动刷新子图以便查看新关系。
