# 修复：Docker 构建平台依赖问题（完整版）

## 问题描述

在 Docker Linux 环境中，Node.js 原生模块需要平台特定的二进制文件。构建时遇到一系列缺少平台依赖的错误：

### 错误 1：Rollup 缺失
```
Error: Cannot find module '@rollup/rollup-linux-x64-gnu'
```

### 错误 2：LightningCSS 缺失
```
Error: Cannot find module '../lightningcss.linux-x64-gnu.node'
```

### 错误 3：TailwindCSS Oxide 缺失
```
Error: Failed to load native binding
Error: Cannot find module '../lightningcss.linux-x64-gnu.node' (from @tailwindcss/oxide)
```

## 根本原因

Vite、Rollup、TailwindCSS v4 等使用 Rust 编写的原生模块，需要为特定平台编译：

- **Rollup**：代码打包工具
- **LightningCSS**：CSS 处理和压缩
- **TailwindCSS Oxide**：TailwindCSS v4 的新 CSS 引擎

## 完整修复方案

### Dockerfile 完整修改

```dockerfile
# Fix platform-specific dependencies for Linux x64
# Install Rollup, LightningCSS and TailwindCSS Oxide Linux platform binaries
RUN npm install \
    @rollup/rollup-linux-x64-gnu \
    lightningcss-linux-x64-gnu \
    @tailwindcss/oxide-linux-x64-gnu \
    --no-save --force && \
    npm run build
```

### 参数说明

| 软件 | 依赖包 | 作用 |
|------|--------|------|
| Rollup | `@rollup/rollup-linux-x64-gnu` | 代码打包工具 |
| LightningCSS | `lightningcss-linux-x64-gnu` | CSS 处理和压缩 |
| TailwindCSS Oxide | `@tailwindcss/oxide-linux-x64-gnu` | TailwindCSS v4 CSS 引擎 |
| | `--no-save` | 不修改 package.json |
| | `--force` | 强制安装，即使有冲突 |

## 验证修复

### 重新构建

```bash
docker compose build app --no-cache
```

### 预期输出

```
=> [frontend-builder 7/7] RUN npm install @rollup/rollup-linux-x64-gnu lightningcss-linux-x64-gnu @tailwindcss/oxide-linux-x64-gnu --no-save --force && npm run build
=> => Installing packages for tooling via npm
=> => added 3 packages in 3s
=> => building for production...
=> => ✓ 1234 modules transformed.
=> => ✓ built in 12.34s
```

## 完整的平台依赖列表

在 Docker Linux x64 环境下，可能需要以下平台依赖：

```json
{
  "buildDependencies": {
    "@rollup/rollup-linux-x64-gnu": "^4.0.0",
    "lightningcss-linux-x64-gnu": "^1.0.0",
    "@tailwindcss/oxide-linux-x64-gnu": "^4.0.0"
  }
}
```

**为什么需要这些？**

1. **Rollup**：Vite 使用 Rollup 进行生产构建，需要原生模块进行快速打包
2. **LightningCSS**：Vite 使用 LightningCSS 处理 CSS，比 PostCSS 快 10-100x
3. **TailwindCSS Oxide**：TailwindCSS v4 新引擎，使用 Rust 重写，性能大幅提升

## 其他可能需要的依赖

如果后续还遇到类似错误，继续添加：

```bash
# esbuild (如果 Vite 回退到 esbuild)
npm install @esbuild/linux-x64 --no-save --force

# SWC (如果项目使用 SWC)
npm install @swc/core-linux-x64-gnu --no-save --force

# Parcel watcher
npm install @parcel/watcher-linux-x64-glibc --no-save --force

# Sharp (图片处理)
npm install sharp --force
```

## 技术背景

### TailwindCSS v4 新架构

TailwindCSS v4 使用 Rust 重写了 CSS 引擎（Oxide），提供：
- **10x 解析速度**：CSS 解析更快
- **1/10 内存**：内存占用更低
- **原生嵌套**：支持 CSS 嵌套语法
- **更好的源映射**：调试更容易

这就是为什么需要 `@tailwindcss/oxide-linux-x64-gnu`。

## 高级方案：多阶段构建

```dockerfile
# 阶段1：安装所有依赖（包括平台特定）
FROM node:20-slim AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev --force

# 阶段2：构建
FROM deps AS builder
WORKDIR /app
COPY . .
# 确保平台依赖存在
RUN npm ls @rollup/rollup-linux-x64-gnu || npm install @rollup/rollup-linux-x64-gnu --no-save --force
RUN npm ls lightningcss-linux-x64-gnu || npm install lightningcss-linux-x64-gnu --no-save --force
RUN npm ls @tailwindcss/oxide-linux-x64-gnu || npm install @tailwindcss/oxide-linux-x64-gnu --no-save --force
RUN npm run build

# 阶段3：运行
FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
```

## 总结

**完整修复命令**：
```dockerfile
RUN npm install \
    @rollup/rollup-linux-x64-gnu \
    lightningcss-linux-x64-gnu \
    @tailwindcss/oxide-linux-x64-gnu \
    --no-save --force && \
    npm run build
```

**状态**：✅ Docker 构建应可成功完成

**预期构建时间**：3-5 分钟（包括 native 模块编译）

**下一步**：
```bash
docker compose build app --no-cache
docker compose up -d
```

---

**修复时间**：2025-11-18T06:20:00Z
**修复版本**：v2.0
**当前状态**：已添加 3 个平台依赖，等待验证
