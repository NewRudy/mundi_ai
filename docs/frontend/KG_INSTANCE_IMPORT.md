# KG Instance Import 使用指南

本页介绍如何从前端批量向知识图谱（Neo4j）写入实例节点。

## 入口
- 左侧侧边栏 → Knowledge Graph → Import Instances
- 路由：/kg/import/instances

## 使用流程
1. 选择 Project（自动列出你的项目）
2. （可选）选择 PostgreSQL 连接，仅用于指示要写入的 Neo4j 连接 ID（后端支持 `connection_id`，默认写入主连接）
3. 在文本框粘贴实例数组 JSON，点击 Validate 验证结构
4. 点击 Upsert Instances 执行导入

## JSON 格式
传入数组，每个元素格式如下：
```json
[
  {
    "table_name": "power_station",
    "pg_id": "123",
    "name": "某电站",
    "properties": { "capacity_mw": 500, "schema": "public" }
  },
  {
    "table_name": "airport",
    "pg_id": "A001",
    "name": "某机场",
    "properties": { "city": "某市" }
  }
]
```
- table_name: 表名（字符串）
- pg_id: 主键或唯一标识（字符串/数字皆可，会被转为字符串）
- name: 可选显示名
- properties: 可选属性字典（将作为实例节点属性写入）

## 后端接口
- POST /api/kg/upsert-instances（可选 query: connection_id）
  - 请求体：上面的数组
  - 响应：`{ "count": number, "instance_ids": string[] }`

## 注意事项
- 本页暂不直接从 PostgreSQL 抽取数据，请先在数据库中准备好主键与字段，再导出为 JSON 粘贴导入。
- 若需将导入与具体 Neo4j 连接绑定，可在“PostgreSQL Connection”下拉中选择相应连接（仅传递 connection_id）。
- 大规模导入建议分批进行，观察响应时间与服务器资源占用。

## 未来计划
- 从 PostgreSQL 表直接选择并批量抽取记录
- 字段映射向导（自动识别主键/name/几何字段）
- 导入进度与断点续传（WebSocket）
