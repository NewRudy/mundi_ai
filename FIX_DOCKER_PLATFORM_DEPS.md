# 修复：Docker 构建平台依赖完整解决方案

## 问题描述

在 Docker Linux 环境中，Node.js 原生模块需要平台特定的二进制文件。构建时依次遇到：

### 错误 1：Rollup 缺失
```
Error: Cannot find module '@rollup/rollup-linux-x64-gnu'
```

### 错误 2：LightningCSS 缺失
```
Error: Cannot find module '../lightningcss.linux-x64-gnu.node'
```

## 根本原因

Vite/Rollup 和相关依赖使用 Rust 编写的原生模块，需要为特定平台编译：

- **Rollup**：代码打包工具
- **LightningCSS**：CSS 处理和压缩

npm 安装时，会根据当前平台自动下载对应二进制。但：
- Windows 开发时 → 安装 Windows 版本
- macOS 开发时 → 安装 macOS 版本
- **Docker Linux 构建时 → ❌ 缺少 Linux 版本**

## 完整修复方案

### Dockerfile 修改

在 `npm run build` 前，安装所有平台特定依赖：

```dockerfile
# Fix platform-specific dependencies for Linux x64
# Install Rollup and LightningCSS Linux platform binaries
RUN npm install \
    @rollup/rollup-linux-x64-gnu \
    lightningcss-linux-x64-gnu \
    --no-save --force && \
    npm run build
```

### 位置

文件：`E:\work_code\mundi.ai\Dockerfile` 第 130-136 行

### 参数说明

| 参数 | 作用 |
|------|------|
| `@rollup/rollup-linux-x64-gnu` | Rollup 的 Linux x64 二进制 |
| `lightningcss-linux-x64-gnu` | LightningCSS 的 Linux 库 |
| `--no-save` | 不修改 package.json，保持干净 |
| `--force` | 强制安装，即使有冲突 |

## 验证修复

### 重新构建

```bash
docker compose build app
```

### 预期输出

```
=> [frontend-builder 7/7] RUN npm install @rollup/rollup-linux-x64-gnu lightningcss-linux-x64-gnu --no-save --force && npm run build
=> => Installing packages for tooling via npm
=> => added 2 packages in 2s
=> => building for production...
=> => ✓ 1234 modules transformed.
=> => ✓ built in 12.34s
```

## 技术细节

### 平台特定依赖列表

在 Docker Linux 环境下，可能需要以下平台依赖：

**必需（Vite/Rollup 相关）：**
```
@rollup/rollup-linux-x64-gnu        # Rollup 打包器
lightningcss-linux-x64-gnu          # CSS 处理
```

**可选（其他原生模块）：**
```
@esbuild/linux-x64                  # esbuild 打包器
@parcel/watcher-linux-x64-glibc     # 文件监听
@swc/core-linux-x64-gnu             # SWC 转译器
```

### 如何检查需要哪些依赖?

如果在构建时遇到类似错误：
```
Cannot find module 'xxx-linux-x64-gnu'
```

说明需要安装对应的 Linux 版本。

### npm install 在哪里查找?

npm 会尝试下载：
```
https://registry.npmjs.org/@rollup/rollup-linux-x64-gnu
https://registry.npmjs.org/lightningcss-linux-x64-gnu
```

包发布后，会包含多个平台的预编译二进制文件。

## 完整解决方案（最佳实践）

### 方案：Docker 多阶段构建优化

```dockerfile
# 阶段1：安装依赖
FROM node:20-slim AS deps
WORKDIR /app
COPY package*.json ./
# 安装所有依赖，包括平台特定的
RUN npm ci --omit=dev --force

# 阶段2：构建
FROM deps AS builder
WORKDIR /app
COPY . .
ENV NODE_ENV=production
RUN npm run build

# 阶段3：运行
FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
```

**优点**：
- 阶段1缓存依赖层，重建更快
- 平台依赖在阶段1解决
- 最终镜像轻量（只有静态文件）

## 相关链接

- [npm/cli Issue #4828](https://github.com/npm/cli/issues/4828) - npm 平台依赖问题
- [Vite Docker Build Issue](https://github.com/vitejs/vite/issues/11393) - Vite Docker 构建
- [LightningCSS Platform Dependencies](https://github.com/parcel-bundler/lightningcss/issues/464)
- [Rollup Platform-Specific Dependencies](https://github.com/rollup/rollup/issues/4812)

## 其他问题排查

### Q1: 安装后仍然找不到模块?

**检查**：
```bash
docker run -it node:20-slim bash
npm install @rollup/rollup-linux-x64-gnu
ls node_modules/@rollup/rollup-linux-x64-gnu/
# 应该看到 rollup.linux-x64-gnu.node
```

**可能原因**：
- npm 缓存损坏 → `npm cache clean --force`
- node_modules 权限问题 → `chmod -R 755 node_modules`

### Q2: 如何支持多架构（ARM64 + AMD64）?

**方案**：
```dockerfile
# 检测架构并安装对应依赖
RUN arch=$(uname -m) && \
    if [ "$arch" = "x86_64" ]; then \
        npm install @rollup/rollup-linux-x64-gnu lightningcss-linux-x64-gnu --force; \
    elif [ "$arch" = "aarch64" ]; then \
        npm install @rollup/rollup-linux-arm64-gnu lightningcss-linux-arm64-gnu --force; \
    fi && \
    npm run build
```

### Q3: Alpine Linux 特别注意事项

如果使用 Alpine（musl libc）：

```dockerfile
# 使用 glibc 版本
RUN npm install \
    @rollup/rollup-linux-x64-musl \
    lightningcss-linux-x64-musl \
    --force
```

## 总结

**问题**：Docker Linux 构建缺少原生模块的平台特定依赖

**解决方案**：
```dockerfile
RUN npm install \
    @rollup/rollup-linux-x64-gnu \
    lightningcss-linux-x64-gnu \
    --no-save --force && \
    npm run build
```

**状态**：✅ 修复完成，Docker 构建应可成功

**预期构建时间**：3-5 分钟

**触发重新构建**：
```bash
docker compose build app --no-cache
```

---

**修复时间**：2025-11-18T06:15:00Z
**修复版本**：v1.0
**影响范围**：Docker 生产构建
