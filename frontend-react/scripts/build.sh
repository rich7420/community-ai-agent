#!/bin/bash

# OpenSource4You AI Agent - React Frontend Build Script

echo "🏗️  構建 OpenSource4You AI Agent React 前端..."

# 檢查 Node.js 版本
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安裝，請先安裝 Node.js 18+"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js 版本過低，需要 18+，當前版本: $(node -v)"
    exit 1
fi

echo "✅ Node.js 版本: $(node -v)"

# 安裝依賴
echo "📦 安裝依賴..."
npm ci --only=production
if [ $? -ne 0 ]; then
    echo "❌ 依賴安裝失敗"
    exit 1
fi

# 類型檢查
echo "🔍 執行類型檢查..."
npm run type-check
if [ $? -ne 0 ]; then
    echo "❌ 類型檢查失敗"
    exit 1
fi

# 代碼檢查
echo "🧹 執行代碼檢查..."
npm run lint
if [ $? -ne 0 ]; then
    echo "⚠️  代碼檢查有警告，但繼續構建..."
fi

# 構建應用
echo "🚀 構建應用..."
npm run build
if [ $? -ne 0 ]; then
    echo "❌ 構建失敗"
    exit 1
fi

# 檢查構建結果
if [ -d "dist" ]; then
    echo "✅ 構建成功！"
    echo "📁 構建文件位於: dist/"
    echo "📊 構建大小:"
    du -sh dist/
    echo ""
    echo "🐳 可以使用以下命令構建 Docker 鏡像:"
    echo "   docker build -t community-ai-frontend ."
    echo ""
    echo "🚀 可以使用以下命令預覽構建結果:"
    echo "   npm run preview"
else
    echo "❌ 構建失敗，未找到 dist/ 目錄"
    exit 1
fi
