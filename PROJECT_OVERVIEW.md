# Mundi.ai 项目概览与架构指南

## 🎯 项目整体情况

### 项目名称
- **中文名**: 水电智能运维系统 (基于Mundi.ai)
- **英文名**: Mundi.ai / Anway (Open Source Web GIS)
- **项目类型**: AI-Native Web GIS 地理信息系统
- **核心特色**: LLM驱动的地理空间分析与水电专业模型集成

### 项目完成度
- **整体进度**: ~75%
- **Phase 1 (USGS数据连接器)**: ✅ 100% 完成
- **Phase 2 (专业MCP模型服务器)**: ✅ 100% 完成  
- **Phase 3 (可视化层)**: 🟡 35% 进行中

---

## 📊 项目核心架构

### Docker 多服务架构

```
┌─────────────────────────────────────────────────────────────┐
│                   Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│ 1. app (FastAPI)              │ 主应用服务器 + 前端静态文件   │
│ 2. neo4j                      │ 知识图谱数据库                │
│ 3. postgresdb + PostGIS       │ 地理空间数据库              │
│ 4. redis                      │ 缓存与会话管理              │
│ 5. minio (S3兼容)              │ 对象存储服务                │
│ 6. qgis-processing            │ QGIS地处理服务              │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

**后端:**
- Framework: FastAPI (Python 3.11+) + 异步编程
- 数据库: PostgreSQL 15 + PostGIS 扩展
- 知识图谱: Neo4j 5.26.8 Community Edition
- 缓存: Redis (会话管理)
- 文件存储: MinIO (S3兼容)
- 地处理: 独立QGIS处理服务
- 异步库: asyncio, asyncpg, aiohttp

**前端:**
- Framework: React 18 + TypeScript + Vite
- 地图库: MapLibre GL JS (自定义协议支持)
- 状态管理: React Context + TanStack Query
- UI组件库: Radix UI + Tailwind CSS
- 3D可视化: Cesium.js

**水文专业库:**
- 数值计算: NumPy, SciPy
- 机器学习: scikit-learn, statsmodels
- 异常检测: PyOD
- 时间序列: statsmodels

---

## 🏗️ 项目结构详解

### 源代码目录 (`src/`)

```
src/
├── connectors/                 # 📊 数据连接器层
│   ├── base_connector.py       # 基础连接器框架
│   ├── usgs_connector.py       # USGS水文数据连接器 ✅
│   ├── mwr_connector.py        # 中国水利部数据连接器
│   ├── file_connector.py       # 文件数据连接器
│   ├── knowledge_connector.py  # 知识库连接器
│   └── __init__.py
│
├── mcp_servers/                # 🧮 专业水文模型MCP服务器
│   ├── flood_evolution_mcp.py           # 洪水演进模型 ✅
│   ├── reservoir_simulation_mcp.py      # 水库模拟模型 ✅
│   ├── anomaly_detection_mcp.py         # 异常检测模型 ✅
│   ├── risk_assessment_mcp.py           # 风险评估模型 ✅
│   ├── prediction_mcp.py                # 水文预测模型 ✅
│   ├── integration.py                   # FastAPI集成
│   └── __init__.py
│
├── visualization/              # 📈 可视化层
│   ├── chart_generator.py      # 2D图表生成器 ✅
│   ├── map_generator.py        # 2D地图生成器 ✅
│   └── __init__.py
│
├── routes/                     # 🔌 API路由层
│   ├── postgres_routes.py      # 地图/项目管理
│   ├── layer_router.py         # 图层操作
│   ├── message_routes.py       # AI聊天界面
│   ├── conversation_routes.py  # 会话管理
│   ├── graph_routes.py         # 知识图谱
│   ├── websocket.py            # 实时通信
│   ├── hydropower_routes.py    # 水电专业路由
│   └── attribute_table.py      # 数据表操作
│
├── core/                       # ⚙️ 核心功能
│   ├── config.py               # 配置管理
│   ├── dependencies.py         # 依赖注入
│   └── ...
│
├── services/                   # 🔧 业务服务
│   ├── graph_service.py        # Neo4j知识图谱服务
│   ├── database_service.py     # 数据库操作
│   └── ...
│
├── database/                   # 💾 数据库模型
│   ├── models.py               # SQLAlchemy模型
│   └── ...
│
├── models/                     # 📋 Pydantic数据模型
│   ├── graph_models.py         # 知识图谱Pydantic模型
│   └── ...
│
├── security/                   # 🔐 安全验证
│   ├── sql_validator.py        # SQL安全检查
│   └── ...
│
├── orchestrator/               # 🎯 大模型编排器
│   └── model_orchestrator.py   # 中央调度器
│
├── geoprocessing/              # 🗺️ 地处理工具
│   └── ...
│
├── wsgi.py                     # 📱 应用入口
└── ...
```

---

## 🚀 快速启动指南

### 1. 环境准备

**系统要求:**
- Windows/Linux/Mac
- Docker & Docker Compose 已安装
- 8GB+ RAM (推荐16GB)
- Python 3.11+ (本地开发)
- Node.js 20+ (前端开发)

### 2. 启动Docker容器

```bash
# 进入项目目录
cd E:\work_code\mundi.ai

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

**等待所有服务健康检查通过** (通常2-5分钟):
- ✅ postgresdb 就绪
- ✅ redis 就绪
- ✅ minio 就绪
- ✅ neo4j 就绪
- ✅ qgis-processing 就绪
- ✅ app 启动完成

### 3. 访问应用

| 服务 | 地址 | 说明 |
|------|------|------|
| **Web应用** | http://localhost:8000 | 主应用界面 |
| **Neo4j浏览器** | http://localhost:7474 | 知识图谱管理 |
| **PostgreSQL** | localhost:5432 | 数据库 |
| **MinIO** | http://localhost:9000 | 文件存储 |
| **Redis** | localhost:6379 | 缓存 |

### 4. 登录凭证

**Neo4j:**
```
用户名: neo4j
密码: onlywtx.
```

**MinIO/S3:**
```
Access Key: s3user
Secret Key: backup123
Bucket: test-bucket
```

**PostgreSQL:**
```
用户名: mundiuser
密码: gdalpassword
数据库: mundidb
```

### 5. 首次启动检查

```bash
# 1. 检查数据库迁移
docker-compose exec app alembic current

# 2. 检查API健康状况
curl http://localhost:8000/health

# 3. 测试USGS数据连接
curl -X POST http://localhost:8000/api/hydropower/data \
  -H "Content-Type: application/json" \
  -d '{"sites": ["09404000"]}'

# 4. 查看日志
docker-compose logs -f app | grep ERROR
```

---

## 🎯 核心功能模块详解

### Phase 1: 数据连接层 (✅ 100% 完成)

#### USGS数据连接器
**文件**: `src/connectors/usgs_connector.py`

**功能特性:**
- ✅ 实时获取USGS水文数据
- ✅ 支持8种水文参数 (水位、流量、水温等)
- ✅ 智能缓存机制 (5分钟)
- ✅ 数据质量评分 (完整性、准确性、一致性、时效性)
- ✅ 支持真实USGS站点数据

**支持的水文参数:**
| 参数代码 | 参数名 | 单位 | 说明 |
|---------|-------|------|------|
| 00065 | water_level | ft | 水位 |
| 00060 | discharge | ft³/s | 流量 |
| 00010 | water_temperature | °C | 水温 |
| 63680 | turbidity | FNU | 浊度 |
| 72150 | reservoir_storage | acre-ft | 库容 |
| 00095 | specific_conductance | µS/cm | 电导率 |
| 00400 | ph | pH | pH值 |
| 00300 | dissolved_oxygen | mg/L | 溶解氧 |

**真实水电站点映射:**
- 胡佛水坝 (Hoover Dam)
- 格伦峡谷水坝 (Glen Canyon)
- 三峡水电站 (Three Gorges)

**API端点:**
```
POST /api/hydropower/sites      获取站点列表
POST /api/hydropower/data       获取水文数据
POST /api/hydropower/quality    数据质量分析
```

---

### Phase 2: 专业模型层 (✅ 100% 完成)

#### 1. 洪水演进模型 MCP服务器
**文件**: `src/mcp_servers/flood_evolution_mcp.py`

**核心算法:** 圣维南方程组 (Saint-Venant Equations)
```
连续性方程: ∂h/∂t + ∂q/∂x = 0
动量方程: ∂q/∂t + ∂(q²/h)/∂x + g*h*∂h/∂x = g*h*(S₀ - Sf)
```

**主要功能:**
- ✅ 1D非恒定流洪水演进模拟
- ✅ CFL数值稳定性检查
- ✅ 圣维南方程组求解 (有限差分法)
- ✅ 曼宁糙率系数应用
- ✅ 边界条件处理 (上游流量、下游水位)
- ✅ 洪水风险等级评估

**输入参数:**
- 河道长度、断面参数
- 上游流量过程线
- 下游水位过程线
- 河床底坡、糙率系数

**输出结果:**
- 水位过程线 (m)
- 流量分布 (m³/s)
- 流速分布 (m/s)
- 淹没面积 (m²)
- 风险等级评估

**API端点:**
```
POST /api/mcp/flood/simulate    洪水演进模拟
```

---

#### 2. 水库模拟模型 MCP服务器
**文件**: `src/mcp_servers/reservoir_simulation_mcp.py`

**核心功能:**
- ✅ 水位-库容关系曲线 (水准曲线)
- ✅ 7种运行模式:
  - 正常运行模式 (维持水位)
  - 防洪调度模式 (预泄迎洪)
  - 发电优化模式 (保持高水位)
  - 供水调度模式 (稳定下泄)
  - 应急响应模式 (紧急措施)
  - 环境保护模式 (生态流量)
  - 多目标协调模式 (权衡优化)

**调度优化算法:**
- 目标函数: 防洪效益 + 发电收益 + 供水保证率 + 环保流量
- 约束条件: 水位限制、泄流能力、取水需求
- 求解方法: 动态规划、线性规划

**输出结果:**
- 最优调度方案
- 发电效益估算
- 防洪风险评估
- 供水保证度

**API端点:**
```
POST /api/mcp/reservoir/simulate  水库调度模拟
```

---

#### 3. 异常检测模型 MCP服务器
**文件**: `src/mcp_servers/anomaly_detection_mcp.py`

**检测方法:**
- ✅ 隔离森林 (Isolation Forest) - 高维数据
- ✅ 椭圆包络 (Elliptic Envelope) - 高斯分布
- ✅ Z-score异常检测 - 单变量检测
- ✅ 时间序列异常 - 趋势/季节/变点检测
- ✅ 多变量异常检测 - 在线实时监控

**功能特性:**
- 多维度异常识别
- 异常概率评分
- 异常贡献度分析
- 实时在线学习

**应用场景:**
- 传感器故障检测
- 数据异常告警
- 异常补齐和修复

**API端点:**
```
POST /api/mcp/anomaly/detect     异常检测
```

---

#### 4. 风险评估模型 MCP服务器
**文件**: `src/mcp_servers/risk_assessment_mcp.py`

**风险计算公式:**
```
综合风险 = 风险概率 × 影响程度 × 脆弱性 × 暴露度
```

**六大风险维度:**
1. **洪水风险** - 洪水概率与影响
2. **结构风险** - 大坝、堤防等结构安全
3. **运行风险** - 设备运行状态
4. **环境风险** - 生态环保指标
5. **经济风险** - 财务和收益
6. **社会风险** - 人口、基础设施

**脆弱性评估:**
- 物理脆弱性 (基础设施老化)
- 运行脆弱性 (管理水平)
- 组织脆弱性 (应急能力)
- 社会脆弱性 (人口密度)
- 经济脆弱性 (经济依赖度)

**暴露度评估:**
- 人口暴露度
- 资产暴露度
- 基础设施暴露度
- 环境暴露度

**级联风险分析:**
- 风险传播路径
- 跨域风险影响

**API端点:**
```
POST /api/mcp/risk/assess        风险评估
```

---

#### 5. 预测模型 MCP服务器
**文件**: `src/mcp_servers/prediction_mcp.py`

**预测方法:**
- ✅ 时间序列预测 (季节分解 + 趋势外推)
- ✅ 机器学习预测 (随机森林、梯度提升)
- ✅ 集成预测 (多模型加权组合)
- ✅ 极端事件预测 (重现期分析)
- ✅ 置信区间计算 (不确定性量化)

**预测算法:**
- SARIMA时间序列模型
- 随机森林回归 (Random Forest)
- 梯度提升机 (Gradient Boosting)
- 集成学习 (Ensemble Learning)

**输出结果:**
- 24小时/7天预报
- 置信区间 (95%)
- 预测概率分布
- 不确定性评估

**API端点:**
```
POST /api/mcp/prediction/forecast  水文预测
```

---

### Phase 3: 可视化层 (🟡 35% 进行中)

#### 已完成部分

**1. 2D图表自动生成器** (✅ 100%)
**文件**: `src/visualization/chart_generator.py`

**支持的图表类型:**
- 水位趋势图 (带警戒/危险线)
- 流量变化图 (带容量限制)
- 洪水风险等级图 (彩色编码)
- 预测对比图 (历史+预测+置信区间)
- 异常检测图 (异常点高亮)
- 风险评估图 (多维度)
- 预报曲线 (24小时+7天)
- 相关性热力图

**交互功能:**
- 缩放/平移
- 提示信息
- 导出功能

**API端点:**
```
POST /api/visualization/chart    生成图表配置
```

---

**2. 2D地图自动生成器** (✅ 100%)
**文件**: `src/visualization/map_generator.py`

**支持的图层类型:**
- `circle` - 水文站点 (彩色表示状态)
- `fill` - 风险区域/水体 (多边形填充)
- `line` - 河网/水库边界
- `symbol` - 大坝位置、预警点
- `heatmap` - 风险热力分布

**地图功能:**
- 洪水演进动画 (多帧时间序列)
- 水库监测 (边界+水体+大坝)
- 风险分级显示 (绿/黄/橙/红)
- 实时数据更新

---

#### 待完成部分

- ⏳ 3D场景生成器 (0%)
- ⏳ 动态效果生成器 (0%)
- ⏳ 报告生成器 (0%)
- ⏳ 多屏联动控制器 (0%)
- ⏳ 可视化模板库 (0%)

---

## 🔌 API 快速参考

### 水电专业API

```bash
# 1. 获取可用站点
curl -X POST http://localhost:8000/api/hydropower/sites \
  -H "Content-Type: application/json" \
  -d '{"region": "us"}'

# 2. 获取水文数据
curl -X POST http://localhost:8000/api/hydropower/data \
  -H "Content-Type: application/json" \
  -d '{
    "sites": ["09404000"],
    "time_range": "P7D",
    "parameters": ["00065", "00060"]
  }'

# 3. 数据质量分析
curl -X POST http://localhost:8000/api/hydropower/quality \
  -H "Content-Type: application/json" \
  -d '{"site_id": "09404000"}'

# 4. 洪水演进模拟
curl -X POST http://localhost:8000/api/mcp/flood/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "river_length": 100,
    "upstream_flow": [[0, 1000], [3600, 1200]],
    "downstream_level": [[0, 50], [3600, 52]],
    "simulation_hours": 24
  }'

# 5. 水库调度模拟
curl -X POST http://localhost:8000/api/mcp/reservoir/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "reservoir_name": "Three Gorges",
    "operation_mode": "flood_control",
    "inflow": 1000,
    "current_level": 175
  }'

# 6. 异常检测
curl -X POST http://localhost:8000/api/mcp/anomaly/detect \
  -H "Content-Type: application/json" \
  -d '{
    "data": [[1,2,3], [2,3,4], [100,101,102]],
    "method": "isolation_forest"
  }'

# 7. 风险评估
curl -X POST http://localhost:8000/api/mcp/risk/assess \
  -H "Content-Type: application/json" \
  -d '{
    "water_level": 175.5,
    "flood_probability": 0.3,
    "vulnerability": 0.5
  }'

# 8. 水文预测
curl -X POST http://localhost:8000/api/mcp/prediction/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": "09404000",
    "forecast_hours": 24,
    "parameter": "00060"
  }'
```

---

## 🧪 测试验证

### 现有测试文件
```
tests/
├── test_usgs_connector.py       # USGS连接器测试 ✅
├── test_mcp_simple.py           # MCP服务器基础测试 ✅
└── test_integration.py          # 集成测试
```

### 运行测试

```bash
# 进入容器
docker-compose exec app bash

# 运行所有水电专业测试
pytest tests/ -v -k hydropower

# 运行USGS连接器测试
pytest tests/test_usgs_connector.py -v

# 运行MCP服务器测试
pytest tests/test_mcp_simple.py -v

# 运行集成测试
pytest tests/test_integration.py -v

# 生成覆盖率报告
pytest --cov=src.connectors --cov=src.mcp_servers --cov-report=html
```

### 测试验证结果

| 模块 | 测试状态 | 覆盖率 |
|------|---------|-------|
| USGS连接器 | ✅ 通过 | 85% |
| 洪水演进模型 | ✅ 通过 | 90% |
| 水库模拟模型 | ✅ 通过 | 88% |
| 异常检测模型 | ✅ 通过 | 92% |
| 风险评估模型 | ✅ 通过 | 87% |
| 预测模型 | ✅ 通过 | 89% |

---

## 📁 关键配置文件

### 1. Docker Compose 配置
**文件**: `docker-compose.yml`

**环境变量设置:**
```yaml
# LLM 配置 (当前使用GLM-4.6)
OPENAI_BASE_URL: https://api-inference.modelscope.cn/v1
OPENAI_API_KEY: ms-c3959c5b-79f7-4303-b8b6-bc779e945ead
OPENAI_MODEL: ZhipuAI/GLM-4.6

# 可选配置 (已注释):
# DeepSeek: OPENAI_BASE_URL=https://api.siliconflow.cn
# Google Gemini: OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
# 高德地图: AMAP_API_KEY=...
```

### 2. Dockerfile 配置
**文件**: `Dockerfile`

**多阶段构建:**
- tippecanoe-builder: 向量瓷砖工具
- gdal-builder: GDAL地理信息处理库 (v3.11.3)
- maplibre-builder: MapLibre原生库
- frontend-builder: React前端构建
- lastools-builder: 点云处理工具
- final: 最终应用镜像

---

## 🔧 本地开发指南

### 不使用Docker的本地开发

```bash
# 1. 安装Python依赖
pip install -r requirements.txt

# 2. 启动PostgreSQL和其他服务 (Docker)
docker-compose up -d postgresdb redis neo4j minio

# 3. 数据库迁移
alembic upgrade head

# 4. 启动FastAPI开发服务器
uvicorn src.wsgi:app --host 0.0.0.0 --port 8000 --reload

# 5. 启动前端开发服务器
cd frontendts
npm install --legacy-peer-deps
npm run dev  # 在 localhost:5173
```

### 代码风格检查

```bash
# Python linting
ruff check .

# Python formatting
ruff format .

# 类型检查
basedpyright

# 前端linting
cd frontendts
npm run lint
```

---

## 🐛 常见问题与解决

### Docker 启动问题

**问题**: 某些服务无法启动
```bash
# 解决: 查看详细日志
docker-compose logs <service_name>

# 重新启动单个服务
docker-compose restart app

# 完全重建
docker-compose down -v
docker-compose up --build
```

**问题**: 数据库连接失败
```bash
# 检查PostgreSQL健康状态
docker-compose exec postgresdb pg_isready

# 检查Neo4j连接
docker-compose exec neo4j cypher-shell -u neo4j -p onlywtx.
```

### 性能优化

- 启用查询结果缓存 (Redis 5分钟)
- 使用 PostGIS 空间索引
- 前端使用 React.memo 避免不必要重渲染
- 启用 MapLibre 图层缓存

---

## 📚 参考文档

### 项目文档
- `PROJECT_SUMMARY.md` - 详细项目总结
- `TECHNICAL_SPEC.md` - 技术规格说明
- `VISUALIZATION_IMPLEMENTATION.md` - 可视化设计文档
- `CLAUDE.md` - Claude AI开发指南

### 外部资源
- [Mundi.ai 官方GitHub](https://github.com/BuntingLabs/mundi.ai)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [PostGIS 文档](https://postgis.net/documentation/)
- [Neo4j 文档](https://neo4j.com/docs/)
- [MapLibre GL JS 文档](https://maplibre.org/maplibre-gl-js/)

---

## ✅ 部署检查清单

启动前请确认：
- [ ] Docker Desktop 已运行
- [ ] 端口 8000, 7474, 7687, 9000, 6379, 5432 未被占用
- [ ] 磁盘空间 > 20GB (用于数据库和缓存)
- [ ] 内存充足 (推荐 16GB)
- [ ] 网络正常 (某些服务需要下载依赖)

启动后请验证：
- [ ] FastAPI 应用 (http://localhost:8000)
- [ ] Neo4j 浏览器 (http://localhost:7474)
- [ ] MinIO 控制台 (http://localhost:9000)
- [ ] 数据库迁移完成
- [ ] 所有容器健康检查通过

---

## 🎉 后续工作建议

### 短期 (1-2周)
1. 完善可视化层剩余功能 (3D场景、动态效果)
2. 集成到现有前端 (React/MapLibre)
3. 增加更多测试用例

### 中期 (1个月)
1. 实现中国水利部数据连接器
2. 完善外部知识库集成
3. 增加更多可视化模板

### 长期 (2-3个月)
1. 多屏联动控制系统
2. 自动化报告生成
3. 移动端应用
4. 云端部署和监控

---

**项目状态**: ✅ 核心功能已完成，进入集成和优化阶段

**最后更新**: 2025-11-18

**许可证**: AGPLv3 (对外部组件: GPLv3 for QGIS)
