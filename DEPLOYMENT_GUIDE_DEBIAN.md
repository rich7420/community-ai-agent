# Debian 部署指南 - 取代現有網頁服務

## 🎯 目標
在Debian服務器上部署Apache Local Community Taipei AI Agent，取代現有的網頁服務，使用域名 `opensource4you.917420.xyz`。

## 📋 部署步驟

### 1. 準備環境變數 (.env)

首先創建 `.env` 文件：

```bash
# 複製範例文件
cp env.example .env
```

編輯 `.env` 文件，填入您的API密鑰：

```bash
# Slack Configuration
SLACK_APP_ID=your-slack-app-id
SLACK_CLIENT_ID=your-slack-client-id
SLACK_CLIENT_SECRET=your-slack-client-secret
SLACK_SIGNING_SECRET=your-slack-signing-secret
SLACK_VERIFICATION_TOKEN=your-slack-verification-token
SLACK_BOT_TOKEN=xoxb-your-actual-slack-bot-token
SLACK_APP_TOKEN=xapp-your-actual-slack-app-token

# GitHub Configuration
GITHUB_TOKEN=ghp_your-actual-github-token

# Grok via OpenRouter
OPENROUTER_API_KEY=sk-or-v1-your-actual-openrouter-api-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=x-ai/grok-4-fast:free

# Google AI API (for Gemini embeddings)
GOOGLE_API_KEY=your-actual-google-api-key

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=community_ai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-secure-database-password
DATABASE_URL=postgresql://postgres:your-secure-database-password@postgres:5432/community_ai

# MinIO Configuration
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key
MINIO_BUCKET=community-data-lake

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# Application Configuration
DEBUG=False
LOG_LEVEL=INFO

# Cache Configuration
CACHE_BACKEND=memory
CACHE_TTL_HOURS=24
CACHE_MAX_SIZE=1000

# LLM Configuration
OPENROUTER_MAX_TOKENS=1024
OPENROUTER_TEMPERATURE=0.7
```

### 2. 停止現有服務

```bash
# 停止現有的nginx服務
sudo systemctl stop nginx

# 停止現有的Docker容器（如果有）
docker-compose down

# 檢查端口占用
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
```

### 3. 配置Nginx

創建新的Nginx配置文件：

```bash
sudo nano /etc/nginx/sites-available/opensource4you.917420.xyz
```

配置內容：

```nginx
server {
    listen 80;
    server_name opensource4you.917420.xyz;
    
    # 重定向HTTP到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name opensource4you.917420.xyz;
    
    # SSL證書配置（使用您現有的證書）
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全標頭
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # 前端靜態文件
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # API代理
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 增加超時時間
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 健康檢查
    location /health {
        proxy_pass http://localhost:8000/health;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 靜態文件緩存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        proxy_pass http://localhost:3000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

啟用新配置：

```bash
# 啟用新站點
sudo ln -sf /etc/nginx/sites-available/opensource4you.917420.xyz /etc/nginx/sites-enabled/

# 禁用舊站點（如果存在）
sudo rm -f /etc/nginx/sites-enabled/default

# 測試Nginx配置
sudo nginx -t

# 重新載入Nginx
sudo systemctl reload nginx
```

### 4. 部署應用

使用Debian部署腳本：

```bash
# 給腳本執行權限
chmod +x deploy-debian.sh

# 執行本地部署
./deploy-debian.sh --local --build
```

### 5. 驗證部署

```bash
# 檢查容器狀態
docker-compose -f docker-compose.debian.yml ps

# 檢查日誌
docker-compose -f docker-compose.debian.yml logs -f

# 測試健康檢查
curl -k https://opensource4you.917420.xyz/health

# 測試API
curl -k https://opensource4you.917420.xyz/api/health/
```

### 6. 設置自動啟動

創建systemd服務文件：

```bash
sudo nano /etc/systemd/system/community-ai-agent.service
```

服務配置：

```ini
[Unit]
Description=Community AI Agent
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/your/community-ai-agent
ExecStart=/usr/bin/docker-compose -f docker-compose.debian.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.debian.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

啟用服務：

```bash
sudo systemctl daemon-reload
sudo systemctl enable community-ai-agent.service
sudo systemctl enable nginx
```

### 7. 監控和維護

```bash
# 查看服務狀態
sudo systemctl status community-ai-agent
sudo systemctl status nginx

# 查看容器日誌
docker-compose -f docker-compose.debian.yml logs -f app
docker-compose -f docker-compose.debian.yml logs -f frontend

# 重啟服務
sudo systemctl restart community-ai-agent
sudo systemctl restart nginx
```

## 🔧 故障排除

### 常見問題

1. **端口衝突**
   ```bash
   # 檢查端口占用
   sudo netstat -tlnp | grep :80
   sudo netstat -tlnp | grep :443
   sudo netstat -tlnp | grep :3000
   sudo netstat -tlnp | grep :8000
   ```

2. **SSL證書問題**
   ```bash
   # 檢查證書
   sudo openssl x509 -in /path/to/certificate.crt -text -noout
   ```

3. **Docker權限問題**
   ```bash
   # 添加用戶到docker組
   sudo usermod -aG docker $USER
   # 重新登錄或執行
   newgrp docker
   ```

4. **數據庫連接問題**
   ```bash
   # 檢查數據庫容器
   docker-compose -f docker-compose.debian.yml logs postgres
   ```

## 📊 性能優化

### 1. 數據庫優化
```bash
# 調整PostgreSQL配置
docker-compose -f docker-compose.debian.yml exec postgres psql -U postgres -c "SHOW shared_buffers;"
```

### 2. 緩存優化
```bash
# 檢查Redis狀態
docker-compose -f docker-compose.debian.yml exec redis redis-cli info memory
```

### 3. 日誌管理
```bash
# 設置日誌輪轉
sudo nano /etc/logrotate.d/community-ai-agent
```

## 🚀 完成部署

部署完成後，您的AI助手將在以下地址可用：

- **主網站**: https://opensource4you.917420.xyz
- **API文檔**: https://opensource4you.917420.xyz/api/docs
- **健康檢查**: https://opensource4you.917420.xyz/health

## 📝 注意事項

1. **備份現有數據**: 在部署前備份現有網站的數據
2. **SSL證書**: 確保SSL證書路徑正確
3. **防火牆**: 確保防火牆允許必要端口
4. **監控**: 設置監控和告警
5. **備份**: 定期備份數據庫和配置文件

---

**部署完成後，您的Apache Local Community Taipei AI Agent將取代現有網頁服務！** 🎉
