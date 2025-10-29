# KG Schema Manager 使用指南

本页介绍前端“Neo4j Schema Manager”页面的使用方法，用于初始化并查看知识图谱数据库（Neo4j）的约束与索引。

## 访问入口
- 左侧侧边栏 → Knowledge Graph → Schema
- 也可直接访问路由：/kg/schema

## 页面功能
- 顶部按钮：
  - Refresh：刷新当前Schema信息
  - Initialize Schema：一键初始化建议的唯一约束与常用索引
- 概览卡片：
  - Constraints：当前约束数量
  - Indexes：当前索引数量
  - Labels：当前标签数量
  - Relationship Types：当前关系类型数量
- 详情区域：
  - Constraints：按项展开查看约束完整信息
  - Indexes：按项展开查看索引完整信息
  - Labels：以标签形式展示现有节点标签
  - Relationship Types：以标签形式展示现有关系类型
- 初始化结果回显：
  - 执行 Initialize Schema 后展示服务端返回的创建结果与错误列表

## 后端接口
- GET /api/kg/schema/info
  - 返回 constraints/indexes/labels/relationship_types 四类信息
- POST /api/kg/schema/init
  - 创建推荐的唯一约束与常用索引

## 常见问题
1. 初始化失败或无变化
   - 若 Neo4j 中已存在相同名称的约束/索引，初始化会跳过创建
   - 可通过 Refresh 查看最新状态
2. 权限或连接错误
   - 确保 Neo4j 服务可用，并已在后端正确配置连接
3. 统计为0
   - 正常情况（初次运行或空库），可先通过 /kg/new 导入本体/配置后再查看

## 后续改进（计划）
- 约束/索引的手动创建与删除
- 健康检查与性能建议
- 连接选择（多 Neo4j 连接场景）
