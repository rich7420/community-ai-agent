#!/bin/bash

echo "🔄 強制重新收集數據..."

# 停止主應用容器
echo "停止主應用容器..."
docker stop community-ai-app-prod 2>/dev/null || true

# 重新啟動主應用容器（會觸發初始數據收集）
echo "重新啟動主應用容器..."
docker-compose -f docker-compose.production.yml up -d app

# 等待服務啟動
echo "等待服務啟動..."
sleep 15

# 檢查容器狀態
echo "檢查容器狀態..."
docker ps | grep app

# 檢查日誌
echo "檢查主應用日誌..."
docker logs community-ai-app-prod --tail=30

# 檢查數據庫中的數據
echo "檢查數據庫中的數據..."
docker exec community-ai-postgres-prod psql -U postgres -d community_ai -c "
SELECT 
    'community_data' as table_name, 
    COUNT(*) as record_count 
FROM community_data
UNION ALL
SELECT 
    'user_name_mappings' as table_name, 
    COUNT(*) as record_count 
FROM user_name_mappings
UNION ALL
SELECT 
    'calendar_events' as table_name, 
    COUNT(*) as record_count 
FROM calendar_events;
"

echo ""
echo "強制數據收集完成！"
echo "查看實時日誌: docker logs community-ai-app-prod -f"
