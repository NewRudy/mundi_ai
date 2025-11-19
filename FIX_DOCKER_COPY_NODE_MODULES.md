# 修复：Docker COPY 覆盖 node_modules 导致依赖丢失

## 问题描述

Docker 构建成功后，前端页面仍然报错：
```
Uncaught TypeError: Failed to resolve module specifier "@deck.gl/react".
Relative references must start with either "/", "./", or "../".
```

明明 Dockerfile 中已经安装了 `@deck.gl/react`，但在浏览器中运行时却找不到该模块。

## 根本原因分析

### Dockerfile 流程问题

**原来的错误流程**：

```dockerfile
WORKDIR /app/frontendts
COPY frontendts/package*.json ./
RUN npm install --legacy-peer-deps  # 步骤1：在 Docker 中安装依赖（包括 @deck.gl/react）

COPY frontendts/ ./                  # 步骤2：❌ 覆盖整个目录，包括 node_modules！
# 如果本地的 node_modules 缺少依赖，就会覆盖 Docker 中刚安装的依赖

RUN npm run build                    # 步骤3：使用被覆盖的 node_modules 构建
```

**问题点**：
- 本地的 `node_modules`（开发环境）可能没有 `@deck.gl/react`
- 或者本地 npm 安装的平台依赖（Windows/macOS）与 Docker Linux 不兼容
- `COPY frontendts/ ./` 会复制整个目录，包括 `node_modules`
- 覆盖了 Docker 容器内刚刚正确安装的依赖

### 为什么本地 node_modules 会缺少依赖？

可能的原因：
1. 开发时只在 Windows/macOS 安装了部分依赖
2. 使用了 `--legacy-peer-deps` 导致依赖树不一致
3. 平台特定依赖（如 `@rollup/rollup-darwin-arm64`）在 Docker Linux 中不需要

## 解决方案

### 方案：使用 `.dockerignore` 排除 node_modules

**步骤 1：创建 `.dockerignore` 文件**

```bash
# E:\work_code\mundi.ai\frontendts\.dockerignore
node_modules/
dist/
build/
.env
.DS_Store
.vscode/
.idea/
```

效果：告诉 Docker 在 `COPY` 时忽略这些目录和文件。

**步骤 2：恢复 Dockerfile 的 COPY 命令**

```dockerfile
WORKDIR /app/frontendts
COPY frontendts/package*.json ./
RUN npm install --legacy-peer-deps  # 安装所有依赖

COPY frontendts/ ./                  # ✅ .dockerignore 会排除 node_modules
# 不会覆盖 node_modules，保留了 Docker 中安装的依赖

RUN npm run build                    # 使用正确的依赖构建
```

### 工作原理

```
Docker 构建过程：
1. COPY package.json
2. RUN npm install              → 创建 node_modules（包含 @deck.gl/react）
3. COPY ./*                    → .dockerignore 排除 node_modules/
   ✅ 复制：src/, public/, vite.config.ts, index.html, etc.
   ❌ 不复制：node_modules/（保留步骤2安装的）
4. RUN npm run build           → 使用步骤2的 node_modules
```

## 验证修复

### 1. 确认 .dockerignore 已创建

```bash
ls -la frontendts/.dockerignore
# 应该看到文件存在，包含 node_modules/
```

### 2. 重新构建 Docker 镜像

```bash
docker compose build app --no-cache

# 或使用你的构建命令
docker buildx build --network host \
  --build-arg APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian \
  --build-arg VITE_WEBSITE_DOMAIN=http://localhost:8000 \
  -t mundi-public:local \
  -f Dockerfile .
```

### 3. 检查构建日志

```bash
# 应该看到 COPY 步骤没有复制 node_modules
 => [frontend-builder 7/8] COPY frontendts/ ./
 => => 1.23MB           # 大小很小，说明没有复制 node_modules

# 对比：如果错误地复制了 node_modules
 => [frontend-builder 7/8] COPY frontendts/ ./
 => => 456.78MB         # 大小很大，说明复制了 node_modules
```

### 4. 运行容器并验证

```bash
docker compose up -d
```

打开浏览器，检查：
- ✅ 控制台没有 `@deck.gl/react` 未找到错误
- ✅ 3D 场景（HydroSceneView）正常显示
- ✅ Deck.gl 图层正确渲染

## 其他解决方案

### 方案 2：在 Docker 中删除并重新安装 node_modules

```dockerfile
COPY frontendts/ ./
# 删除可能从本地复制的 node_modules
RUN rm -rf node_modules && \
    npm install --legacy-peer-deps && \
    npm run build
```

**缺点**：
- 浪费时间（重复安装依赖）
- 缓存失效，构建变慢

### 方案 3：只复制需要的文件

```dockerfile
WORKDIR /app/frontendts
COPY frontendts/package*.json ./
RUN npm install --legacy-peer-deps

# 逐个复制文件/目录，不复制 node_modules
COPY frontendts/src ./src/
COPY frontendts/public ./public/
COPY frontendts/index.html ./
COPY frontendts/vite.config.ts ./
COPY frontendts/tsconfig*.json ./

RUN npm run build
```

**缺点**：
- Dockerfile 冗长
- 容易遗漏文件
- 新增文件需要修改 Dockerfile

### 方案 4：两阶段 COPY

```dockerfile
WORKDIR /app/frontendts
COPY frontendts/package*.json ./
RUN npm install --legacy-peer-deps

# 第一阶段：复制除 node_modules 外的所有文件
RUN mkdir -p /tmp/src
cp -r frontendts/* /tmp/src/
rm -rf /tmp/src/node_modules
cp -r /tmp/src/* ./

RUN npm run build
```

**缺点**：
- 复杂且难以理解
- 构建时间增加（额外复制操作）

## 为什么选择 .dockerignore 方案？

| 方案 | 优点 | 缺点 |
|------|------|------|
| `.dockerignore` | ✅ 简单、标准做法<br>✅ 自动排除<br>✅ 构建缓存友好 | ❌ 需要额外文件 |
| 删除重装 | ✅ 确保依赖正确 | ❌ 构建慢<br>❌ 浪费资源 |
| 逐个复制 | ✅ 精确控制 | ❌ Dockerfile 冗长<br>❌ 易遗漏 |
| 两阶段 | ✅ 灵活 | ❌ 复杂难懂 |

`.dockerignore` 是 **Docker 官方推荐的做法**，简单、可靠、易于维护。

## 最佳实践

### 1. 前端 .dockerignore 模板

```bash
# Dependencies
node_modules/
.pnp
.pnp.js

# Testing
coverage/

# Production
dist/
build/

# Misc
.DS_Store
.env.local
.env.development.local
.env.test.local
.env.production.local

# Logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Dependency directories
jspm_packages/

# Optional npm cache directory
.npm

# Optional eslint cache
.eslintcache

# Microbundle cache
.rpt2_cache/
.rts2_cache_cjs/
.rts2_cache_es/
.rts2_cache_umd/

# Optional REPL history
.node_repl_history

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity

# dotenv environment variables file
.env
.env.test

# parcel-bundler cache (https://parceljs.org/)
.cache
.parcel-cache

# Next.js build output
.next
out

# Nuxt.js build / generate output
.nuxt
dist

# Gatsby files
.cache/
public

# Storybook build outputs
.out
.storybook-out

# Temporary folders
tmp/
temp/

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~
```

### 2. 后端 .dockerignore

```bash
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# pipenv
Pipfile.lock

# PEP 582
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/
```

### 3. CI/CD 集成

**GitHub Actions**：

```yaml
name: Build and Deploy

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Build Docker image
        run: |
          docker buildx build \
            --network host \
            --build-arg APT_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/debian \
            --build-arg VITE_WEBSITE_DOMAIN=http://localhost:8000 \
            -t mundi-public:local \
            -f Dockerfile \
            . \
            --cache-from=type=gha \
            --cache-to=type=gha,mode=max

      - name: Test image
        run: |
          docker run -d -p 8000:8000 mundi-public:local
          sleep 10
          curl -f http://localhost:8000 || exit 1
```

## 总结

**问题**：Docker COPY 命令覆盖了本地 `node_modules`，导致依赖丢失

**根本原因**：
1. 本地 `node_modules` 缺少 `@deck.gl/react`
2. `COPY frontendts/ ./` 复制了本地不完整的 `node_modules`
3. 覆盖了 Docker 中正确安装的依赖

**解决方案**：
1. 创建 `.dockerignore` 文件，排除 `node_modules/`
2. 保持 Dockerfile 简单：`COPY frontendts/ ./`
3. Docker 会自动忽略 `node_modules/`，保留容器内安装的依赖

**效果**：
- ✅ 构建更快（不需要重新安装依赖）
- ✅ 构建可靠（总是使用正确的依赖）
- ✅ 维护简单（添加文件自动处理）

**命令验证**：
```bash
docker compose build app --no-cache
docker compose up -d
```

打开浏览器，控制台应不再报错！🎉
