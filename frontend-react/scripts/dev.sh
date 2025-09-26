#!/bin/bash

# OpenSource4You AI Agent - React Frontend Development Script

echo "🚀 啟動 OpenSource4You AI Agent React 前端開發環境..."

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

# 檢查是否存在 node_modules
if [ ! -d "node_modules" ]; then
    echo "📦 安裝依賴..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 依賴安裝失敗"
        exit 1
    fi
fi

# 檢查環境變數文件
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        echo "📝 創建環境變數文件..."
        cp env.example .env
        echo "✅ 已創建 .env 文件，請根據需要修改配置"
    else
        echo "⚠️  未找到 env.example 文件"
    fi
fi

# 啟動開發服務器
echo "🎯 啟動開發服務器..."
echo "📍 前端地址: http://localhost:3000"
echo "🔗 API 地址: http://localhost:8000"
echo "📚 API 文檔: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服務器"
echo ""

npm run dev
