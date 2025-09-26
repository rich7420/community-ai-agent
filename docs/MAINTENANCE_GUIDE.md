# Community AI Agent 維護指南

## 概述

本指南提供 Community AI Agent 的日常維護、監控和故障排除操作說明。

## 日常維護任務

### 1. 系統監控

#### 檢查服務狀態
```bash
# 查看所有服務狀態
docker-compose -f docker-compose.prod.yml ps

# 查看特定服務日誌
docker-compose -f docker-compose.prod.yml logs -f app

# 檢查資源使用情況
docker stats
```

#### 健康檢查
```bash
# 應用健康檢查
curl http://localhost:8000/health

# 詳細健康狀態
curl http://localhost:8000/health/components

# 指標數據
curl http://localhost:8000/health/metrics
```

### 2. 日誌管理

#### 查看日誌
```bash
# 查看所有服務日誌
docker-compose -f docker-compose.prod.yml logs

# 查看特定服務日誌
docker-compose -f docker-compose.prod.yml logs app
docker-compose -f docker-compose.prod.yml logs postgres
docker-compose -f docker-compose.prod.yml logs redis

# 實時查看日誌
docker-compose -f docker-compose.prod.yml logs -f --tail=100 app
```

#### 日誌輪轉
```bash
# 手動清理舊日誌
./scripts/maintenance.sh cleanup

# 設置自動日誌輪轉
crontab -e
# 添加以下行（每天凌晨3點清理）：
# 0 3 * * * /path/to/community-ai-agent/scripts/maintenance.sh cleanup
```

### 3. 備份與恢復

#### 自動備份
```bash
# 設置每日備份
crontab -e
# 添加以下行（每天凌晨2點備份）：
# 0 2 * * * /path/to/community-ai-agent/scripts/backup.sh
```

#### 手動備份
```bash
# 執行備份
./scripts/backup.sh

# 查看備份文件
ls -la /backups/
```

#### 恢復數據
```bash
# 列出可用備份
./scripts/restore.sh --list

# 恢復特定備份
./scripts/restore.sh --date 20240101_120000
```

### 4. 性能監控

#### 系統資源
```bash
# CPU 使用率
top -p $(pgrep -f "community-ai")

# 內存使用
free -h

# 磁盤使用
df -h

# 網絡連接
netstat -tulpn | grep :8000
```

#### 應用性能
```bash
# 查看 Prometheus 指標
curl http://localhost:9090/api/v1/query?query=up

# 查看 Grafana 儀表板
# 訪問 http://localhost:3000
```

## 故障排除

### 常見問題

#### 1. 服務無法啟動

**症狀**: 服務狀態顯示為 "Exited" 或 "Restarting"

**診斷步驟**:
```bash
# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps

# 查看錯誤日誌
docker-compose -f docker-compose.prod.yml logs service_name

# 檢查端口占用
netstat -tulpn | grep :8000
```

**解決方案**:
```bash
# 重啟服務
docker-compose -f docker-compose.prod.yml restart service_name

# 完全重啟
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

#### 2. 數據庫連接失敗

**症狀**: 應用日誌顯示數據庫連接錯誤

**診斷步驟**:
```bash
# 檢查數據庫狀態
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U community_user

# 檢查數據庫日誌
docker-compose -f docker-compose.prod.yml logs postgres

# 測試數據庫連接
docker-compose -f docker-compose.prod.yml exec postgres psql -U community_user -d community_ai -c "SELECT 1;"
```

**解決方案**:
```bash
# 重啟數據庫
docker-compose -f docker-compose.prod.yml restart postgres

# 檢查數據庫配置
docker-compose -f docker-compose.prod.yml exec postgres cat /var/lib/postgresql/data/postgresql.conf
```

#### 3. 內存不足

**症狀**: 系統響應緩慢，OOM 錯誤

**診斷步驟**:
```bash
# 檢查內存使用
free -h
docker stats

# 檢查系統日誌
dmesg | grep -i "killed process"
```

**解決方案**:
```bash
# 清理未使用的容器和鏡像
docker system prune -a

# 重啟服務
docker-compose -f docker-compose.prod.yml restart

# 調整服務資源限制
# 編輯 docker-compose.prod.yml 添加資源限制
```

#### 4. 磁盤空間不足

**症狀**: 寫入失敗，磁盤使用率接近 100%

**診斷步驟**:
```bash
# 檢查磁盤使用
df -h

# 查找大文件
find / -type f -size +1G 2>/dev/null | head -10

# 檢查 Docker 使用情況
docker system df
```

**解決方案**:
```bash
# 清理 Docker 資源
docker system prune -a --volumes

# 清理舊日誌
./scripts/maintenance.sh cleanup

# 清理舊備份
find /backups -name "*.gz" -mtime +30 -delete
```

### 性能優化

#### 1. 數據庫優化

```sql
-- 檢查慢查詢
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- 重建索引
REINDEX DATABASE community_ai;

-- 更新統計信息
ANALYZE;
```

#### 2. 應用優化

```bash
# 調整工作進程數
export MAX_WORKERS=8

# 啟用緩存
export CACHE_TTL=3600

# 調整日誌級別
export LOG_LEVEL=WARNING
```

#### 3. 系統優化

```bash
# 調整系統參數
echo 'vm.swappiness=10' >> /etc/sysctl.conf
echo 'net.core.somaxconn=65535' >> /etc/sysctl.conf
sysctl -p
```

## 更新與升級

### 1. 應用更新

```bash
# 備份當前版本
./scripts/backup.sh

# 拉取最新代碼
git pull origin main

# 更新依賴
pip install -r requirements.txt

# 重新構建和部署
./scripts/deploy.sh production
```

### 2. 數據庫遷移

```bash
# 運行遷移腳本
docker-compose -f docker-compose.prod.yml exec app python scripts/init_db.py

# 檢查遷移狀態
docker-compose -f docker-compose.prod.yml exec postgres psql -U community_user -d community_ai -c "SELECT * FROM schema_migrations;"
```

### 3. 配置更新

```bash
# 更新環境變數
cp env.prod.example .env.prod
# 編輯 .env.prod

# 重啟服務
docker-compose -f docker-compose.prod.yml restart
```

## 監控與告警

### 1. 設置監控

```bash
# 啟動監控服務
docker-compose -f docker-compose.prod.yml up -d prometheus grafana

# 訪問監控面板
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
```

### 2. 配置告警

```bash
# 編輯告警規則
vim monitoring/alert_rules.yml

# 重載 Prometheus 配置
curl -X POST http://localhost:9090/-/reload
```

### 3. 日誌聚合

```bash
# 啟動 ELK Stack
docker-compose -f docker-compose.prod.yml up -d elasticsearch logstash kibana

# 訪問 Kibana
# http://localhost:5601
```

## 安全維護

### 1. 定期更新

```bash
# 更新系統包
sudo apt update && sudo apt upgrade -y

# 更新 Docker 鏡像
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 安全掃描

```bash
# 掃描容器漏洞
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image community-ai-agent_app:latest
```

### 3. 訪問控制

```bash
# 檢查開放端口
nmap -sT -O localhost

# 檢查防火牆規則
sudo ufw status
```

## 緊急響應

### 1. 服務完全宕機

```bash
# 1. 檢查系統狀態
./scripts/maintenance.sh status

# 2. 重啟所有服務
./scripts/maintenance.sh restart

# 3. 如果仍然失敗，從備份恢復
./scripts/restore.sh --date latest
```

### 2. 數據丟失

```bash
# 1. 停止寫入操作
docker-compose -f docker-compose.prod.yml stop app

# 2. 從備份恢復
./scripts/restore.sh --date 20240101_120000

# 3. 驗證數據完整性
docker-compose -f docker-compose.prod.yml exec postgres psql -U community_user -d community_ai -c "SELECT COUNT(*) FROM community_data;"
```

### 3. 安全事件

```bash
# 1. 立即停止服務
docker-compose -f docker-compose.prod.yml down

# 2. 檢查日誌
docker-compose -f docker-compose.prod.yml logs | grep -i "error\|unauthorized\|failed"

# 3. 更新密鑰和證書
# 4. 重新部署
./scripts/deploy.sh production
```

## 聯繫支持

### 內部支持
- **技術問題**: 查看日誌和監控面板
- **緊急問題**: 聯繫系統管理員
- **功能請求**: 提交 Issue 到專案倉庫

### 外部支持
- **Docker 問題**: Docker 官方文檔
- **PostgreSQL 問題**: PostgreSQL 官方文檔
- **監控問題**: Prometheus/Grafana 官方文檔

---

**注意**: 本指南會隨著系統更新持續改進，請定期查看最新版本。在進行任何維護操作前，請務必先備份重要數據。

