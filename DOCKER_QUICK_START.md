# Docker 快速启动指南

## 📋 一键启动

### Windows PowerShell

```powershell
# 1. 进入项目目录
cd E:\work_code\mundi.ai

# 2. 启动所有Docker服务 (后台运行)
docker-compose up -d

# 3. 查看启动进度
docker-compose logs -f app

# 等待看到类似信息:
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Linux/Mac

```bash
cd /path/to/mundi.ai
docker-compose up -d
docker-compose logs -f app
```

---

## ✅ 启动检查清单

### 1. 前置条件检查

```powershell
# 检查Docker是否运行
docker --version
# 预期输出: Docker version 24.x.x 或更高

# 检查Docker Compose
docker-compose --version
# 预期输出: Docker Compose version 2.x.x 或更高

# 检查可用端口
netstat -ano | findstr :8000
# 如果有输出，说明8000端口被占用，需要释放
```

### 2. 服务启动验证 (约2-5分钟)

```powershell
# 查看所有容器状态
docker-compose ps

# 预期输出:
# NAME                  STATUS              PORTS
# mundi-app            Up (healthy)        0.0.0.0:8000->8000/tcp
# neo4j                Up (healthy)        0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
# postgresdb           Up (healthy)        5432/tcp
# redis                Up (healthy)        6379/tcp
# minio                Up (healthy)        9000/tcp
# qgis-processing      Up (healthy)        8817/tcp
```

### 3. 应用健康检查

```powershell
# 检查FastAPI应用
curl http://localhost:8000/health
# 预期: 200 OK 响应

# 检查API端点
curl -X POST http://localhost:8000/api/hydropower/sites `
  -H "Content-Type: application/json" `
  -d '{\"region\": \"us\"}'
```

### 4. 数据库初始化

```powershell
# 进入应用容器
docker-compose exec app bash

# 检查数据库迁移状态
alembic current

# 应用所有迁移
alembic upgrade head

# 退出容器
exit
```

---

## 🌐 访问各服务

| 服务 | URL | 用途 |
|------|-----|------|
| **Web应用** | http://localhost:8000 | 主应用 + API |
| **API文档** | http://localhost:8000/docs | Swagger文档 |
| **Neo4j浏览器** | http://localhost:7474 | 知识图谱管理 |
| **MinIO控制台** | http://localhost:9000 | 文件存储管理 |

---

## 🔑 登录凭证

### Neo4j
```
URL: http://localhost:7474
用户名: neo4j
密码: onlywtx.
```

### MinIO
```
URL: http://localhost:9000
Access Key: s3user
Secret Key: backup123
```

### PostgreSQL (使用psql连接)
```
Host: localhost
Port: 5432
Database: mundidb
User: mundiuser
Password: gdalpassword
```

### Redis
```
Host: localhost
Port: 6379
(无认证)
```

---

## 🧪 快速测试API

### 获取USGS水文站点

```powershell
$body = @{
    "region" = "us"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/hydropower/sites" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

### 获取实时水文数据

```powershell
$body = @{
    "sites" = @("09404000")
    "time_range" = "P1D"
    "parameters" = @("00065", "00060", "00010")
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8000/api/hydropower/data" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body

$response | ConvertTo-Json -Depth 10 | Write-Host
```

### 洪水演进模拟

```powershell
$body = @{
    "river_length" = 100
    "upstream_flow" = @(@(0, 1000), @(3600, 1200))
    "downstream_level" = @(@(0, 50), @(3600, 52))
    "simulation_hours" = 24
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/mcp/flood/simulate" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

### 水库调度模拟

```powershell
$body = @{
    "reservoir_name" = "Three Gorges"
    "operation_mode" = "flood_control"
    "inflow" = 1000
    "current_level" = 175
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/mcp/reservoir/simulate" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

---

## 📊 查看日志

### 查看主应用日志
```powershell
# 实时日志
docker-compose logs -f app

# 最后100行
docker-compose logs --tail=100 app

# 搜索ERROR
docker-compose logs app | grep ERROR
```

### 查看具体服务日志
```powershell
# PostgreSQL日志
docker-compose logs postgresdb

# Neo4j日志
docker-compose logs neo4j

# Redis日志
docker-compose logs redis

# MinIO日志
docker-compose logs minio

# QGIS处理服务日志
docker-compose logs qgis-processing
```

---

## 🛑 停止和清理

### 停止服务 (保留数据)
```powershell
docker-compose stop
```

### 停止并移除容器 (保留数据)
```powershell
docker-compose down
```

### 完全清理 (删除所有数据和卷)
```powershell
docker-compose down -v
```

### 重启单个服务
```powershell
docker-compose restart app
```

---

## 🔧 常见问题

### Q1: 容器启动失败，提示"端口已被占用"

```powershell
# 查看占用端口的进程
netstat -ano | findstr :8000

# 杀死进程 (替换PID)
taskkill /PID <PID> /F

# 或修改docker-compose.yml中的端口映射
# 将 "8000:8000" 改为 "8001:8000"
```

### Q2: 数据库连接超时

```powershell
# 检查PostgreSQL容器
docker-compose logs postgresdb

# 重新启动PostgreSQL
docker-compose restart postgresdb

# 等待容器恢复 (通常20-30秒)
Start-Sleep -Seconds 30
docker-compose exec postgresdb pg_isready
```

### Q3: Neo4j认证失败

```powershell
# 检查Neo4j日志
docker-compose logs neo4j

# 查看密码是否正确 (在docker-compose.yml中)
# NEO4J_AUTH=neo4j/onlywtx.

# 重置Neo4j
docker-compose down -v neo4j
docker-compose up -d neo4j
```

### Q4: 内存不足

```powershell
# 检查Docker内存限制
docker stats

# 增加Docker Desktop内存 (在设置中)
# 或减少容器数量，注释掉不需要的服务
```

### Q5: 前端无法加载

```powershell
# 查看前端构建日志
docker-compose logs app | grep frontend

# 检查dist目录是否存在
docker-compose exec app ls -la frontendts/dist

# 重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📈 性能监控

### 实时资源使用

```powershell
# 查看容器资源使用
docker stats

# 查看磁盘使用
docker system df

# 查看网络流量
docker stats --no-stream
```

### 数据库性能检查

```powershell
# 进入PostgreSQL
docker-compose exec postgresdb psql -U mundiuser -d mundidb

# 查看活跃连接
SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;

# 查看表大小
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# 退出
\q
```

### 缓存命中率

```powershell
# 进入Redis
docker-compose exec redis redis-cli

# 查看统计信息
INFO stats

# 查看内存使用
INFO memory

# 退出
EXIT
```

---

## 🚀 性能优化建议

### 1. 增加数据库连接池

编辑 `src/core/config.py`:
```python
# 调整连接池大小
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 40
```

### 2. 启用查询缓存

在 `docker-compose.yml` 中设置Redis过期时间:
```yaml
environment:
  - REDIS_CACHE_TTL=300  # 5分钟
  - REDIS_MAX_CONNECTIONS=50
```

### 3. 启用Nginx反向代理

如果需要多实例，可以在 `docker-compose.yml` 中添加:
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
  depends_on:
    - app
```

---

## 📚 更多信息

- 详细项目文档: `PROJECT_OVERVIEW.md`
- 技术规格说明: `TECHNICAL_SPEC.md`
- 可视化设计: `VISUALIZATION_IMPLEMENTATION.md`
- AI开发指南: `CLAUDE.md`

---

**最后更新**: 2025-11-18
