#!/bin/bash

# Apache Local Community Taipei AI Agent 啟動腳本
# 這個腳本會自動啟動所有服務並進行初始化

set -e

echo "🚀 Apache Local Community Taipei AI Agent 啟動中..."
echo "=================================================="

# 檢查是否存在 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 找不到 .env 文件！"
    echo "請先複製 env.example 並填入您的API密鑰："
    echo "  cp env.example .env"
    echo "  nano .env"
    exit 1
fi

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未運行！請先啟動 Docker。"
    exit 1
fi

# 檢查 Docker Compose 是否可用
if ! command -v docker-compose > /dev/null 2>&1 && ! docker compose version > /dev/null 2>&1; then
    echo "❌ Docker Compose 未安裝！"
    exit 1
fi

# 使用 docker compose 或 docker-compose
if docker compose version > /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo "📦 構建 Docker 映像..."
$COMPOSE_CMD build

echo "🚀 啟動服務..."
$COMPOSE_CMD up -d

echo "⏳ 等待服務啟動完成..."
echo "這可能需要幾分鐘時間，請耐心等待..."

# 等待服務健康檢查
echo "🔍 檢查服務狀態..."
sleep 30

# 檢查服務狀態
$COMPOSE_CMD ps

echo ""
echo "🎉 服務啟動完成！"
echo "=================================================="
echo "📱 前端界面: http://localhost:3000"
echo "🔧 API 文檔: http://localhost:8000/docs"
echo "❤️  健康檢查: http://localhost:8000/health"
echo ""
echo "📊 監控面板:"
echo "  - Prometheus: http://localhost:9090"
echo "  - Grafana: http://localhost:3001"
echo "  - MinIO Console: http://localhost:9001"
echo ""
echo "📝 查看日誌:"
echo "  $COMPOSE_CMD logs -f app"
echo ""
echo "🛑 停止服務:"
echo "  $COMPOSE_CMD down"
echo ""
echo "✨ 享受使用小饅頭 AI 助手！"
