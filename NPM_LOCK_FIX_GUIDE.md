# 🔧 NPM Lock文件同步快速修复指南

## 问题概述

Docker构建失败，错误信息：
```
npm error code EUSAGE
npm error `npm ci` can only install packages when your package.json 
and package-lock.json or npm-shrinkwrap.json are in sync.
```

**原因**: `package.json` 中新增了3个依赖，但 `package-lock.json` 还没有更新：
- `cesium@^1.122.0`
- `@tremor/react@^3.18.7`
- `zustand@^4.5.2`

---

## ✅ 快速修复步骤

### 第1步：打开PowerShell

在项目根目录（`E:\work_code\mundi.ai`）打开PowerShell：

```powershell
cd E:\work_code\mundi.ai
```

### 第2步：运行更新脚本

```powershell
.\UPDATE_NPM_LOCK.ps1
```

**脚本会自动：**
1. ✅ 检查npm是否安装
2. ✅ 验证package.json存在
3. ✅ 运行 `npm install` 更新lock文件
4. ✅ 显示成功或失败信息

### 第3步：等待完成

脚本会花费 **5-15分钟** 下载和安装所有依赖（取决于网络速度）。

**进度指示:**
- 🔍 Checking npm installation...
- 📂 Changing to frontendts directory...
- 🔄 Running: npm install
- ✅ SUCCESS! Lock file updated

---

## 🐛 如果遇到问题

### 问题1：PowerShell执行策略限制

**错误**: `Cannot be loaded because running scripts is disabled...`

**解决:**
```powershell
# 为当前用户允许运行脚本
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 然后再运行脚本
.\UPDATE_NPM_LOCK.ps1
```

### 问题2：npm命令找不到

**错误**: `npm : 无法将"npm"项识别为 cmdlet、函数、脚本文件或可运行程序的名称`

**解决:**
1. 检查Node.js是否安装：`node --version`
2. 如果没安装，从 https://nodejs.org 下载安装
3. 重启PowerShell
4. 再试一次

### 问题3：网络超时

**错误**: `ERR! connection timed out` 或 `ERR! code ETIMEDOUT`

**解决:**
```powershell
# 方法1：清除npm缓存
npm cache clean --force

# 方法2：增加超时时间
npm config set fetch-timeout 600000

# 方法3：使用NPM镜像（如果在中国）
npm config set registry https://registry.npmmirror.com

# 然后重试
npm install
```

### 问题4：权限问题

**错误**: `ERR! code EACCES` 或 `permission denied`

**解决:**
```powershell
# 删除node_modules和lock文件，重新安装
Remove-Item -Path frontendts\node_modules -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path frontendts\package-lock.json -ErrorAction SilentlyContinue

# 重新运行脚本
.\UPDATE_NPM_LOCK.ps1
```

---

## 📋 手动方式（如果脚本不工作）

如果脚本无法运行，也可以手动执行：

```powershell
# 1. 进入frontendts目录
cd E:\work_code\mundi.ai\frontendts

# 2. 安装依赖
npm install

# 3. 返回项目根目录
cd E:\work_code\mundi.ai
```

---

## ✨ 成功后的下一步

### 步骤1：提交git（可选但推荐）

```powershell
git add frontendts/package-lock.json
git commit -m "chore: sync npm dependencies (cesium, @tremor/react, zustand)"
```

### 步骤2：重建Docker镜像

```powershell
docker-compose build --no-cache
```

### 步骤3：启动容器

```powershell
docker-compose up -d
```

### 步骤4：验证运行

```powershell
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 访问应用
Start-Process "http://localhost:8000"
```

---

## 📊 预期输出

成功时，你会看到类似：

```
========================================
📦 npm Lock File Update Script
========================================

🔍 Checking npm installation...
✅ npm version: 10.x.x

📂 Changing to frontendts directory...
✅ Current directory: E:\work_code\mundi.ai\frontendts

🔍 Checking files...
✅ package.json found

========================================
🔄 Running: npm install
========================================

added 1500 packages in 8m45s

========================================
✅ SUCCESS! Lock file updated
========================================

📊 Summary:
  • package.json and package-lock.json are now in sync
  • All new dependencies (cesium, @tremor/react, zustand) have been added
  • You can now run Docker build successfully

🚀 Next steps:
  1. Commit the updated package-lock.json to git
  2. Run docker-compose build to rebuild the image
  3. Run docker-compose up -d to start the services
```

---

## ⏱️ 时间预估

| 步骤 | 时间 | 说明 |
|------|------|------|
| 检查npm | 5秒 | 快速检查 |
| npm install | 5-15分钟 | 取决于网络速度 |
| Docker build | 10-30分钟 | 第一次构建较慢 |
| Docker启动 | 2-5分钟 | 容器启动和初始化 |
| **总计** | **20-50分钟** | 首次完整部署 |

---

## 🆘 需要进一步帮助？

如果问题仍未解决，请提供以下信息：

1. 完整的错误信息（复制粘贴所有错误内容）
2. npm版本：`npm --version`
3. Node版本：`node --version`
4. 你的网络环境信息

然后我可以帮你深入调试。

---

**最后更新**: 2025-11-18  
**状态**: ✅ 生产就绪
