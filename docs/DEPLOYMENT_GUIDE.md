# 部署指南

## 環境準備

### 系統要求
- Docker 20.10+
- Docker Compose 2.0+
- 至少 4GB RAM
- 至少 20GB 磁盤空間

### 必要服務
- Slack App (用於數據收集)
- GitHub Personal Access Token
- OpenRouter API Key (用於Grok模型)
- Google AI API Key (用於Gemini嵌入)

## 部署步驟

### 1. 準備環境變數

```bash
# 複製環境變數範例
cp env.example .env

# 編輯環境變數文件
nano .env
```

### 2. 配置API密鑰

在 `.env` 文件中設置以下必要變數：

```bash
# Slack配置
SLACK_APP_ID=your-slack-app-id
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_VERIFICATION_TOKEN=your-slack-verification-token
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token

# GitHub配置
GITHUB_TOKEN=ghp_your-github-token

# OpenRouter配置
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key

# Google AI配置
GOOGLE_API_KEY=your-google-api-key

# 數據庫配置
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=postgresql://postgres:your-secure-password@postgres:5432/community_ai

# MinIO配置
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key

# Redis配置
REDIS_PASSWORD=your-redis-password
```

### 3. 啟動服務

```bash
# 啟動所有服務
docker-compose up -d

# 檢查服務狀態
docker-compose ps
```

### 4. 等待服務啟動

```bash
# 等待服務完全啟動（約2-3分鐘）
sleep 180

# 檢查服務健康狀態
curl http://localhost:8000/health
```

### 5. 初始化數據

```bash
# 初始化數據收集
docker-compose exec app python scripts/init_data_collection.py

# 檢查數據收集狀態
docker-compose logs app | tail -20
```

### 6. 驗證部署

```bash
# 測試API
curl -X POST http://localhost:8000/ask_question \
  -H "Content-Type: application/json" \
  -d '{"question": "測試系統"}'

# 測試前端
curl http://localhost:3000/
```

## 生產環境配置

### SSL證書配置

1. 獲取SSL證書
2. 將證書文件放在 `docker/nginx/ssl/` 目錄
3. 更新 `docker/nginx/nginx.conf` 配置

### 域名配置

1. 設置DNS記錄指向服務器
2. 更新 `docker-compose.yml` 中的域名配置
3. 重新啟動服務

### 監控配置

```bash
# 啟動監控服務
docker-compose -f docker-compose.monitoring.yml up -d

# 訪問監控面板
# Prometheus: http://your-domain:9090
# Grafana: http://your-domain:3001
```

## 維護操作

### 備份數據

```bash
# 備份數據庫
docker-compose exec postgres pg_dump -U postgres community_ai > backup.sql

# 備份MinIO數據
docker-compose exec minio mc mirror /data /backup
```

### 更新服務

```bash
# 拉取最新代碼
git pull origin main

# 重新構建並啟動
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 查看日誌

```bash
# 查看所有服務日誌
docker-compose logs -f

# 查看特定服務日誌
docker-compose logs -f app
docker-compose logs -f frontend
```

### 清理資源

```bash
# 清理未使用的Docker資源
docker system prune -f

# 清理日誌文件
docker-compose exec app find /app/logs -name "*.log" -mtime +7 -delete
```

## 故障排除

### 常見問題

1. **服務啟動失敗**
   ```bash
   # 檢查端口占用
   netstat -tulpn | grep :3000
   netstat -tulpn | grep :8000
   
   # 檢查Docker狀態
   docker system df
   ```

2. **API連接失敗**
   ```bash
   # 檢查環境變數
   docker-compose exec app env | grep -E "(SLACK|GITHUB|OPENROUTER)"
   
   # 測試API連接
   docker-compose exec app python tests/test_api_connections.py
   ```

3. **數據庫連接問題**
   ```bash
   # 檢查數據庫狀態
   docker-compose exec postgres psql -U postgres -c "SELECT version();"
   
   # 檢查連接池
   docker-compose exec app python -c "from src.storage.connection_pool import get_db_connection; print('DB OK')"
   ```

### 性能優化

1. **調整資源限制**
   ```yaml
   # 在docker-compose.yml中添加
   deploy:
     resources:
       limits:
         memory: 2G
         cpus: '1.0'
   ```

2. **優化數據庫**
   ```sql
   -- 創建索引
   CREATE INDEX idx_community_data_timestamp ON community_data(timestamp);
   CREATE INDEX idx_community_data_platform ON community_data(platform);
   ```

3. **緩存配置**
   ```bash
   # 啟用Redis緩存
   CACHE_BACKEND=redis
   REDIS_URL=redis://redis:6379/0
   ```

## 安全建議

1. **定期更新密碼**
2. **限制API訪問**
3. **啟用日誌監控**
4. **定期備份數據**
5. **使用HTTPS**

## 支援

如遇到問題，請：

1. 查看日誌文件
2. 檢查環境變數配置
3. 確認API密鑰有效性
4. 聯繫技術支援團隊