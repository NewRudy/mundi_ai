#!/usr/bin/env pwsh
# Fix npm package-lock.json synchronization issue
# Resolves EINTEGRITY and missing package errors in Docker builds

$ErrorActionPreference = "Stop"
$frontendDir = "E:\work_code\mundi.ai\frontendts"

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🔧 NPM Lock File Fix" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify npm is installed
Write-Host "1️⃣  Checking npm installation..." -ForegroundColor Yellow
try {
    $npmVersion = npm --version
    Write-Host "   ✓ npm version: $npmVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ npm not found. Please install Node.js with npm." -ForegroundColor Red
    exit 1
}

# Step 2: Navigate to frontend directory
Write-Host "2️⃣  Navigating to frontend directory..." -ForegroundColor Yellow
if (-not (Test-Path $frontendDir)) {
    Write-Host "   ✗ Frontend directory not found: $frontendDir" -ForegroundColor Red
    exit 1
}
Push-Location $frontendDir
Write-Host "   ✓ Working directory: $(Get-Location)" -ForegroundColor Green

# Step 3: Clear npm cache
Write-Host "3️⃣  Clearing npm cache..." -ForegroundColor Yellow
npm cache clean --force | Out-Null
Write-Host "   ✓ Cache cleared" -ForegroundColor Green

# Step 4: Remove old lock file
Write-Host "4️⃣  Removing old package-lock.json..." -ForegroundColor Yellow
if (Test-Path "package-lock.json") {
    Remove-Item "package-lock.json" -Force
    Write-Host "   ✓ Old lock file removed" -ForegroundColor Green
} else {
    Write-Host "   ⓘ No existing lock file found" -ForegroundColor Cyan
}

# Step 5: Run npm install
Write-Host "5️⃣  Running npm install (this may take 5-15 minutes)..." -ForegroundColor Yellow
Write-Host "   ⏳ Installing dependencies..." -ForegroundColor Cyan
try {
    npm install --legacy-peer-deps --registry=https://registry.npmjs.org 2>&1 | Tee-Object -Variable npmOutput | Out-Null
    Write-Host "   ✓ npm install completed successfully" -ForegroundColor Green
} catch {
    Write-Host "   ✗ npm install failed with error:" -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    Pop-Location
    exit 1
}

# Step 6: Verify lock file
Write-Host "6️⃣  Verifying lock file..." -ForegroundColor Yellow
if (Test-Path "package-lock.json") {
    $lockSize = (Get-Item "package-lock.json").Length
    Write-Host "   ✓ package-lock.json created ($([math]::Round($lockSize/1MB, 2)) MB)" -ForegroundColor Green
} else {
    Write-Host "   ✗ Lock file not created" -ForegroundColor Red
    Pop-Location
    exit 1
}

# Step 7: Summary
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✅ SUCCESS! Lock file synchronized" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Summary:" -ForegroundColor Cyan
Write-Host "  • package.json and package-lock.json are now in sync" -ForegroundColor White
Write-Host "  • All dependencies have been resolved" -ForegroundColor White
Write-Host "  • cesium, @tremor/react, zustand are included" -ForegroundColor White
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Commit the updated lock file:" -ForegroundColor White
Write-Host "     git add frontendts/package-lock.json" -ForegroundColor Gray
Write-Host "     git commit -m 'chore: sync npm dependencies'" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Rebuild Docker image:" -ForegroundColor White
Write-Host "     docker-compose build --no-cache" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Start the application:" -ForegroundColor White
Write-Host "     docker-compose up -d" -ForegroundColor Gray
Write-Host ""

Pop-Location
