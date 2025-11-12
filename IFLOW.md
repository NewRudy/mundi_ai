# Mundi.ai (Anway) 项目概览

## 项目简介

**名称**: Mundi.ai / Anway  
**描述**: 开源 AI 原生 Web GIS 平台  
**许可证**: AGPLv3 (QGIS 集成组件为 GPLv3)  
**技术栈**: FastAPI (Python) + React/TypeScript + Neo4j + PostgreSQL/PostGIS + MinIO + Redis

Anway 是一个可自托管的、AI 驱动的地理信息系统，支持：
- 矢量、栅格和点云数据
- 空间数据库 (PostGIS) 连接
- LLM 驱动的地理处理和符号化编辑
- 通过 WebSocket 实现实时协作
- 基于知识图谱的时空推理

## 核心架构

### 多服务架构

```
┌──────────────────────────────────────────────────────────────┐
│                       Docker Compose 栈                      │
├──────────────────────────────────────────────────────────────┤
│ 1. app (FastAPI)         - 主应用服务器                        │
│ 2. neo4j                 - 知识图谱数据库                        │
│ 3. postgresdb            - 主数据库 + PostGIS                   │
│ 4. redis                 - 缓存和会话管理                        │
│ 5. minio (S3)            - 文件对象存储                          │
│ 6. qgis-processing       - 独立地理处理服务                      │
└──────────────────────────────────────────────────────────────┘
```

### 核心服务

1. **主应用** (app 容器)
   - FastAPI 后端，提供 REST API + SPA
   - Uvicorn ASGI 服务器 (端口 8000)
   - 内置前端服务 (Vite 构建的 React SPA)
   - Python 3.11+, 基于 asyncio

2. **Neo4j 知识图谱** (neo4j 容器)
   - 版本: 5.26.8 社区版
   - 端口: 7474 (浏览器), 7687 (Bolt 协议)
   - 用途: 时空知识图谱
   - 启用 APOC 插件

3. **PostgreSQL + PostGIS** (postgresdb 容器)
   - 版本: PostgreSQL 15
   - 带 PostGIS 扩展的主数据库
   - 存储: 项目、地图、图层、对话、消息

4. **Redis** (redis 容器)
   - Alpine 版本
   - 会话管理和缓存

5. **MinIO** (minio 容器)
   - S3 兼容对象存储
   - 存储上传的 GIS 文件 (GeoTIFF, Shapefiles 等)

6. **QGIS 处理** (qgis-processing 容器)
   - 用于 QGIS 算法的独立微服务
   - FastAPI 服务器，端口 8817
   - 处理复杂的地理处理任务

## 专利组合架构

### 核心专利
**名称**: 基于时空知识图谱和空间智能协同的水电工程安全智能运维管控系统

**技术逻辑**:
1. **多源数据集成**: 支持Shapefile、GeoTIFF、KML/KMZ、GeoJSON、PostGIS等多种数据格式，接入PostgreSQL空间数据库生成总结文档
2. **空间智能编排**: 根据需求进行空间分析任务的智能编排和优化
3. **QGIS服务调用**: 调用QGIS Processing服务进行专业地理处理
4. **时空知识图谱构建与更新**: 基于Neo4j构建和更新时空知识图谱
5. **协同决策**: 支持多用户实时协作和智能决策支持

### 外围专利1
**名称**: 一种基于空间智能的时空知识图谱动态构建与应用方法

**核心技术**:
- 空间智能驱动的知识图谱构建
- 动态增量更新机制
- 智能应用服务

### 外围专利2
**名称**: 一种基于大语言模型的智能地理场景交互方法

**核心技术**:
- 自然语言理解与解析
- 智能工具调用机制
- 动态场景生成与展示

## 构建和运行

### 启动完整技术栈

```bash
docker compose up
```

### 仅后端 (需要服务运行中)

```bash
uv sync --dev
uv run uvicorn src.wsgi:app --host 0.0.0.0 --port 8000 --reload
```

### 仅前端

```bash
cd frontendts
npm ci --legacy-peer-deps
npm run dev
```

### 运行测试

```bash
# 后端测试
uv run pytest -xvs
uv run pytest src/routes/test_*.py

# 特定标记
uv run pytest -m postgres  # PostgreSQL 测试
uv run pytest -m s3        # S3/MinIO 测试

# 在 Docker 中
docker compose run app pytest -xvs -n auto
```

### 代码检查

```bash
# Python
ruff check .
ruff format .
uv run basedpyright

# 前端
cd frontendts
npm run lint
```

### 数据库迁移

```bash
uv run alembic upgrade head
```

### 初始化 Neo4j 数据

```bash
python src/scripts/init_graph_data.py
```

## 开发约定

### Python 代码风格
- 所有 I/O 操作使用 async/await
- 公共 API 使用显式类型注解
- 请求/响应验证使用 Pydantic 模型
- 使用 OpenTelemetry 进行可观察性
- 结构化错误详情的 HTTPException

### 前端代码风格
- 使用 hooks 的函数式组件
- 所有新代码使用 TypeScript
- 使用 React.memo/useMemo 进行性能优化
- 通过集中化包装器集成 MapLibre
- API 类型定义在 `lib/types.tsx`

### 文件放置约定
- 新路由: `src/routes/`
- 共享工具: `src/dependencies/`
- 数据库模型: `src/database/models.py`
- 前端组件: `frontendts/src/components/`
- 测试: 与源文件并置 (`test_*.py`)

## 关键依赖

### 地理空间技术栈
- **GDAL 3.11.3+**: 栅格/矢量处理
- **PostGIS**: 空间数据库操作
- **QGIS 3.x**: 高级地理处理 (独立容器)
- **Tippecanoe**: 矢量瓦片生成
- **rio-tiler**: 云优化 GeoTIFF 服务
- **LAStools**: 点云处理

### 前端技术栈
- **React 18**: UI 框架
- **MapLibre GL JS**: Web 地图
- **Deck.gl**: 高级可视化
- **Radix UI**: 组件基元
- **TanStack Query**: 数据获取

### 后端技术栈
- **FastAPI**: Web 框架
- **SQLAlchemy**: ORM (异步)
- **Alembic**: 数据库迁移
- **OpenAI client**: LLM 集成
- **Neo4j Python driver**: 图数据库
- **Boto3/aioboto3**: S3 操作

## 环境变量

### 核心变量 (来自 docker-compose.yml)

```bash
# 认证
MUNDI_AUTH_MODE=edit  # "edit" 或 "view_only"

# S3/MinIO
S3_ACCESS_KEY_ID=s3user
S3_SECRET_ACCESS_KEY=backup123
S3_ENDPOINT_URL=http://minio:9000
S3_BUCKET=test-bucket

# PostgreSQL
POSTGRES_HOST=postgresdb
POSTGRES_PORT=5432
POSTGRES_DB=mundidb
POSTGRES_USER=mundiuser
POSTGRES_PASSWORD=gdalpassword

# Neo4j
NEO4J_HOST=neo4j
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=onlywtx.

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# LLM (示例在 docker-compose.yml 中)
OPENAI_API_KEY=$OPENAI_API_KEY
OPENAI_BASE_URL=https://api-inference.modelscope.cn/v1
OPENAI_MODEL=ZhipuAI/GLM-4.6

# 服务
QGIS_PROCESSING_URL=http://qgis-processing:8817
WEBSITE_DOMAIN=http://localhost:8000
```

## API 路由

### 核心路由
- `/api/maps/*` - 地图/项目管理、渲染、上传
- `/api/layers/*` - 图层 CRUD 操作
- `/api/messages/*` - AI 代理消息处理
- `/api/conversations/*` - 对话管理
- `/api/graph/*` - 知识图谱操作 (完整 API)
- `/api/kg/*` - 最小化 KG 同步 API
- `/ws/maps/{map_id}` - 实时更新的 WebSocket

### 认证
- 通过 `@mundi/ee` 包处理 (企业版)
- 会话验证: `verify_session_required`
- 用户上下文: `UserContext` (uuid, email)

## 项目特色

### AI 集成
- LLM 驱动的地理处理工具选择
- 自然语言到空间查询
- 自动图层样式生成
- 基于对话的工作流

### 协作功能
- 通过 WebSocket 实时存在跟踪
- 实时更新的临时操作
- 地图版本控制 (地图状态的 DAG)
- 多用户访问控制

### 知识图谱
- 时空推理
- 实体关系跟踪
- 查询上下文理解
- 配置驱动的数据同步

### 灵活性
- 使用 Docker 可自托管
- 本地 LLM 支持
- 多 LLM 提供商选项
- 可扩展的地理处理管道

*此文档通过探索代码库自动生成。最后更新: 2025-11-11*