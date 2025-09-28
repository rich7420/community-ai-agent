#!/bin/bash

echo "🔧 測試 Scheduler 修復..."

# 停止現有的 scheduler 容器
echo "停止現有的 scheduler 容器..."
docker stop community-ai-scheduler-prod 2>/dev/null || true
docker rm community-ai-scheduler-prod 2>/dev/null || true

# 重新啟動 scheduler 服務
echo "重新啟動 scheduler 服務..."
docker-compose -f docker-compose.production.yml up -d scheduler

# 等待服務啟動
echo "等待服務啟動..."
sleep 10

# 檢查 scheduler 容器狀態
echo "檢查 scheduler 容器狀態..."
docker ps | grep scheduler

# 檢查 scheduler 日誌
echo "檢查 scheduler 日誌..."
docker logs community-ai-scheduler-prod --tail=20

# 測試 scheduler 導入
echo "測試 scheduler 導入..."
docker exec community-ai-scheduler-prod python -c "
import sys
sys.path.append('/app/src')
try:
    from scheduler.cron_jobs import CronJobScheduler
    print('✅ Scheduler 導入成功')
except Exception as e:
    print(f'❌ Scheduler 導入失敗: {e}')
"

echo "測試完成！"
