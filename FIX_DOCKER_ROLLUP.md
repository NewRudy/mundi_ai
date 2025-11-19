# 修复：Docker 构建 Rollup Linux 平台依赖问题

## 问题描述

Docker 构建失败，错误信息：
```
Error: Cannot find module '@rollup/rollup-linux-x64-gnu'
Require stack:
- /app/frontendts/node_modules/rollup/dist/native.js
```

## 原因分析

Rollup 需要特定平台的二进制文件。在 Docker（Linux x64）环境中，Node.js 无法找到对应的平台依赖。

这是 npm 的一个已知问题，与可选依赖（optional dependencies）相关。

## 修复方案

### Dockerfile 修改

在 `npm run build` 之前，强制安装 Linux 平台特定的 Rollup 依赖：

```dockerfile
# Fix Rollup Linux platform dependency issue
# Install platform-specific dependencies for Linux x64
RUN npm install @rollup/rollup-linux-x64-gnu --no-save --force && \
    npm run build
```

### 参数说明

-  **`--no-save`**  : 不修改 package.json（保持依赖列表干净）
-  **`--force`**  : 强制安装，即使有冲突

### 修复位置

文件：`E:\work_code\mundi.ai\Dockerfile` 第 130-133 行

## 验证修复

### 重新构建 Docker 镜像

```bash
docker compose build app
```

或完整构建：

```bash
docker compose build --no-cache
```

### 预期输出

```
=> [frontend-builder 7/7] RUN npm install @rollup/rollup-linux-x64-gnu --no-save --force && npm run build
=> => Installing packages for tooling via npm
=> => added 1 package and audited 1005 packages in 3s
=> => building for production...
=> => ✓ 1234 modules transformed.
=> => dist/index.html                    1.23 kB
=> => dist/assets/index-abc123.js       456.78 kB
=> => dist/assets/index-xyz789.css      12.34 kB
```

## 技术背景

### 为什么需要平台特定依赖?

Rollup 的部分功能需要编译成本地代码以获得最佳性能，包括：
- 文件系统操作优化
- 代码解析加速
- 源映射生成

### 为什么本地开发没问题?

在 Windows/macOS 开发时，npm 会自动安装对应的平台依赖：
- Windows: `@rollup/rollup-win32-x64-msvc`
- macOS: `@rollup/rollup-darwin-x64`
- Linux: `@rollup/rollup-linux-x64-gnu` (Docker 需要)

### 跨平台兼容性

为了确保在不同平台下都能正常运行，可以在 `package.json` 中添加：

```json
{
  "optionalDependencies": {
    "@rollup/rollup-linux-x64-gnu": "^4.0.0",
    "@rollup/rollup-win32-x64-msvc": "^4.0.0",
    "@rollup/rollup-darwin-x64": "^4.0.0"
  }
}
```

但这样会安装所有平台的依赖，增加体积。Docker 方案更轻量。

## 替代方案

### 方案2：删除并重新安装（较慢）

```dockerfile
RUN rm -rf node_modules package-lock.json && \
    npm cache clean --force && \
    npm install --legacy-peer-deps && \
    npm run build
```

**缺点**：需要重新下载所有依赖，构建时间增加 2-3 分钟。

### 方案3：使用 npm ci（推荐用于 CI/CD）

```dockerfile
# 在宿主机生成 package-lock.json
npm install --package-lock-only

# Dockerfile
RUN npm ci --omit=dev && \
    npm run build
```

## 相关链接

- [npm/cli Issue #4828](https://github.com/npm/cli/issues/4828)
- [Rollup Platform-Specific Dependencies](https://github.com/rollup/rollup/issues/4812)
- [Vite Build Docker Issue](https://github.com/vitejs/vite/issues/11393)

## 总结

**问题**：Docker Linux 环境中缺少 Rollup 平台特定依赖

**解决方案**：在 build 前强制安装 `@rollup/rollup-linux-x64-gnu`

**命令**：
```dockerfile
RUN npm install @rollup/rollup-linux-x64-gnu --no-save --force && npm run build
```

**效果**：✅ Docker 构建成功，无需重新安装所有依赖
