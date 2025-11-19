# npm Lock File Update Script
# 更新package-lock.json以匹配最新的package.json依赖

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "📦 npm Lock File Update Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查npm是否已安装
Write-Host "🔍 Checking npm installation..." -ForegroundColor Yellow
$npmVersion = npm --version
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ npm version: $npmVersion" -ForegroundColor Green
} else {
    Write-Host "❌ npm not found! Please install Node.js" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📂 Changing to frontendts directory..." -ForegroundColor Yellow
cd E:\work_code\mundi.ai\frontendts

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to change directory" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Current directory: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# 检查package.json和package-lock.json是否存在
Write-Host "🔍 Checking files..." -ForegroundColor Yellow
if (!(Test-Path "package.json")) {
    Write-Host "❌ package.json not found" -ForegroundColor Red
    exit 1
}
Write-Host "✅ package.json found" -ForegroundColor Green

if (!(Test-Path "package-lock.json")) {
    Write-Host "⚠️  package-lock.json not found (will be created)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔄 Running: npm install" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 运行npm install来更新lock文件
npm install

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "✅ SUCCESS! Lock file updated" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📊 Summary:" -ForegroundColor Yellow
    Write-Host "  • package.json and package-lock.json are now in sync" -ForegroundColor Green
    Write-Host "  • All new dependencies (cesium, @tremor/react, zustand) have been added" -ForegroundColor Green
    Write-Host "  • You can now run Docker build successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Commit the updated package-lock.json to git" -ForegroundColor White
    Write-Host "  2. Run docker-compose build to rebuild the image" -ForegroundColor White
    Write-Host "  3. Run docker-compose up -d to start the services" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "❌ FAILED! npm install encountered an error" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "⚠️  Possible solutions:" -ForegroundColor Yellow
    Write-Host "  1. Check your internet connection" -ForegroundColor White
    Write-Host "  2. Try clearing npm cache: npm cache clean --force" -ForegroundColor White
    Write-Host "  3. Delete node_modules folder: Remove-Item -Path node_modules -Recurse -Force" -ForegroundColor White
    Write-Host "  4. Try again: npm install" -ForegroundColor White
    Write-Host ""
    exit 1
}
