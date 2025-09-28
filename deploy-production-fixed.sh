#!/bin/bash

# 修復後的生產環境部署腳本
# 解決了模組導入路徑和 nginx 配置問題

set -e

echo "🚀 開始部署 Community AI Agent 到生產環境..."

# 檢查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "❌ 錯誤: .env 文件不存在"
    echo "請確保 .env 文件存在並包含所有必要的環境變數"
    exit 1
fi

# 檢查必要的環境變數
echo "🔍 檢查環境變數..."
required_vars=(
    "SLACK_BOT_TOKEN"
    "SLACK_APP_TOKEN" 
    "GITHUB_TOKEN"
    "OPENROUTER_API_KEY"
    "GOOGLE_API_KEY"
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "MINIO_ACCESS_KEY"
    "MINIO_SECRET_KEY"
    "DOMAIN"
    "FRONTEND_URL"
    "API_URL"
)

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=your-" .env || grep -q "^${var}=$" .env; then
        echo "⚠️  警告: ${var} 未正確配置"
    fi
done

# 停止現有容器
echo "🛑 停止現有容器..."
docker-compose -f docker-compose.production.yml down || true

# 清理舊的鏡像（可選）
echo "🧹 清理舊的鏡像..."
docker system prune -f || true

# 構建並啟動服務
echo "🔨 構建並啟動服務..."
docker-compose -f docker-compose.production.yml up -d --build

# 等待服務啟動
echo "⏳ 等待服務啟動..."
sleep 30

# 檢查容器狀態
echo "📊 檢查容器狀態..."
docker-compose -f docker-compose.production.yml ps

# 檢查關鍵服務的健康狀態
echo "🏥 檢查服務健康狀態..."

# 檢查 PostgreSQL
echo "檢查 PostgreSQL..."
if docker exec community-ai-postgres-prod pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ PostgreSQL 運行正常"
else
    echo "❌ PostgreSQL 未正常運行"
fi

# 檢查 Redis
echo "檢查 Redis..."
if docker exec community-ai-redis-prod redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis 運行正常"
else
    echo "❌ Redis 未正常運行"
fi

# 檢查 MinIO
echo "檢查 MinIO..."
if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    echo "✅ MinIO 運行正常"
else
    echo "❌ MinIO 未正常運行"
fi

# 檢查主應用
echo "檢查主應用..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 主應用運行正常"
else
    echo "❌ 主應用未正常運行"
fi

# 檢查 Scheduler
echo "檢查 Scheduler..."
if docker exec community-ai-scheduler-prod python -c "import sys; sys.path.append('/app/src'); from scheduler.cron_jobs import CronJobScheduler; print('Scheduler OK')" > /dev/null 2>&1; then
    echo "✅ Scheduler 運行正常"
else
    echo "❌ Scheduler 未正常運行"
    echo "Scheduler 日誌:"
    docker logs community-ai-scheduler-prod --tail=20
    echo ""
    echo "🔧 嘗試修復 Scheduler..."
    echo "重新啟動 Scheduler 服務..."
    docker-compose -f docker-compose.production.yml restart scheduler
    sleep 10
    echo "再次檢查 Scheduler..."
    docker logs community-ai-scheduler-prod --tail=10
fi

# 檢查 Nginx
echo "檢查 Nginx..."
if docker exec community-ai-nginx-prod nginx -t > /dev/null 2>&1; then
    echo "✅ Nginx 配置正確"
else
    echo "❌ Nginx 配置有問題"
    echo "Nginx 日誌:"
    docker logs community-ai-nginx-prod --tail=20
fi

echo ""
echo "🎉 部署完成！"
echo ""
echo "📋 服務狀態:"
echo "  - API: http://localhost:8000"
echo "  - 前端: http://localhost (通過 Nginx)"
echo "  - 健康檢查: http://localhost:8000/health"
echo ""
echo "📝 查看日誌:"
echo "  docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "🛑 停止服務:"
echo "  docker-compose -f docker-compose.production.yml down"
echo ""