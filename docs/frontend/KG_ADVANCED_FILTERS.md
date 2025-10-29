# 高级过滤使用指南

本指南介绍在“KG Overview / KG Spatial Relations”中使用高级过滤器的方法。

## 入口
- KG Overview → Subgraph Visualization → Advanced Filters
- KG Spatial Relations → Browse → 右侧预览上方（节点过滤器、关系类型、多条件）

## 功能
- 节点过滤（AND 组合）
  - 条目：key + operator + value
  - operator：contains / equals / gt / lt（gt/lt 仅对数值有效）
  - 匹配对象：节点顶层属性或 properties 内属性
- 关系过滤（AND 组合）
  - 条目：key + operator + value（同上）
  - 关系类型：多选（为空代表全部）
- 文本筛选（KG Overview）
  - 对节点 JSON 文本进行包含匹配（与节点条件同为 AND 关系）

## 可视化
- 悬停邻接高亮：鼠标悬停节点，高亮其相邻边
- 边标签：可开关显示关系类型文字
- 导出
  - KG Overview：导出筛选后的子图 JSON
  - Spatial Relations：导出筛选后的关系 CSV

## 提示
- 数值比较时（gt/lt）请确保 value 为数字；若被比较的属性不是数字，条件会忽略该行（判为 false）
- 复杂筛选建议先从较少条件开始，逐步添加
