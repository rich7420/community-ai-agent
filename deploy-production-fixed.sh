#!/bin/bash

# OpenSource4You AI Agent - Production Deployment Script (Fixed)
# 修復後的生產環境部署腳本

set -e

echo "🚀 開始部署 OpenSource4You AI Agent 到生產環境..."

# 檢查必要文件
echo "📋 檢查必要文件..."
if [ ! -f "docker-compose.production.yml" ]; then
    echo "❌ 找不到 docker-compose.production.yml"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "❌ 找不到 .env 文件，請先創建並配置環境變量"
    exit 1
fi

# 檢查必要的環境變量
echo "🔍 檢查環境變量..."
required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "MINIO_ACCESS_KEY" "MINIO_SECRET_KEY" "DOMAIN" "API_URL" "FRONTEND_URL")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ 缺少必要的環境變量: $var"
        exit 1
    fi
done

echo "✅ 環境變量檢查通過"

# 停止現有服務
echo "🛑 停止現有服務..."
docker compose -f docker-compose.production.yml down || true

# 清理舊的鏡像（可選）
echo "🧹 清理舊的鏡像..."
docker system prune -f || true

# 構建並啟動服務
echo "🏗️ 構建並啟動服務..."
docker compose -f docker-compose.production.yml build --no-cache

echo "🚀 啟動服務..."
docker compose -f docker-compose.production.yml up -d

# 等待服務啟動
echo "⏳ 等待服務啟動..."
sleep 30

# 檢查服務狀態
echo "🔍 檢查服務狀態..."
docker compose -f docker-compose.production.yml ps

# 檢查健康狀態
echo "🏥 檢查健康狀態..."
for service in postgres redis minio app frontend nginx scheduler; do
    echo "檢查 $service 服務..."
    if docker compose -f docker-compose.production.yml ps | grep -q "$service.*healthy\|$service.*Up"; then
        echo "✅ $service 服務正常"
    else
        echo "⚠️ $service 服務可能有問題"
    fi
done

# 顯示訪問信息
echo ""
echo "🎉 部署完成！"
echo "📊 服務狀態："
docker compose -f docker-compose.production.yml ps
echo ""
echo "🌐 訪問地址："
echo "   - 前端: http://$DOMAIN"
echo "   - API: http://$DOMAIN/api"
echo "   - 健康檢查: http://$DOMAIN/health"
echo ""
echo "📝 查看日誌："
echo "   docker compose -f docker-compose.production.yml logs -f"
echo ""
echo "🛠️ 管理命令："
echo "   停止服務: docker compose -f docker-compose.production.yml down"
echo "   重啟服務: docker compose -f docker-compose.production.yml restart"
echo "   查看狀態: docker compose -f docker-compose.production.yml ps"
