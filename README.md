# Apache Local Community Taipei AI Agent

一個基於RAG（檢索增強生成）技術的AI助手，專門為Apache Local Community Taipei社群設計，能夠回答關於社群成員、專案和活動的問題。

## 功能特色

- 🤖 **個性化AI助手**：小饅頭，具有獨特的個性和身份
- 📚 **RAG技術**：基於Slack和GitHub數據的智能問答
- 🔍 **語義搜索**：使用Gemini嵌入模型進行精確匹配
- 💬 **自然對話**：支持繁體中文，回答簡潔友好
- 📱 **現代界面**：React前端，響應式設計
- 🚀 **Docker部署**：一鍵部署，易於維護

## 技術架構

- **後端**：Python + FastAPI + PostgreSQL + FAISS
- **前端**：React + TypeScript + Tailwind CSS
- **AI模型**：Grok-4 (OpenRouter) + Gemini Embeddings
- **數據源**：Slack API + GitHub API
- **部署**：Docker Compose + Nginx

## 快速開始

### 1. 克隆專案

```bash
git clone <this-repo-url>
cd community-ai-agent
```

### 2. 設置環境變數

複製環境變數範例文件：

```bash
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
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token

# GitHub Configuration
GITHUB_TOKEN=ghp_your-github-token

# Grok via OpenRouter
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key

# Google AI API (for Gemini embeddings)
GOOGLE_API_KEY=your-google-api-key

# Database Configuration
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=postgresql://postgres:your-secure-password@postgres:5432/community_ai

# MinIO Configuration
MINIO_ACCESS_KEY=your-minio-access-key
MINIO_SECRET_KEY=your-minio-secret-key

# Redis Configuration
REDIS_PASSWORD=your-redis-password
```

### 3. 啟動服務

```bash
docker compose up -d
```

系統會自動執行以下操作：
- 啟動所有服務（PostgreSQL、Redis、MinIO、API、前端）
- 等待依賴服務健康檢查通過
- 自動初始化數據收集（Slack和GitHub數據）
- 生成嵌入向量並建立FAISS索引
- 啟動API服務

### 4. 訪問應用

- **前端界面**：http://localhost:3000
- **API文檔**：http://localhost:8000/docs
- **健康檢查**：http://localhost:8000/health

## API密鑰獲取

### Slack API
1. 訪問 [Slack API](https://api.slack.com/apps)
2. 創建新應用
3. 獲取 Bot Token 和 App Token
4. 設置 OAuth 重定向 URL

### GitHub API
1. 訪問 [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. 生成新的 Personal Access Token
3. 選擇 `repo` 和 `read:org` 權限

### OpenRouter API
1. 訪問 [OpenRouter](https://openrouter.ai/)
2. 註冊帳號
3. 獲取 API Key

### Google AI API
1. 訪問 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 創建新的 API Key

## 專案結構

```
community-ai-agent/
├── src/                    # 後端源代碼
│   ├── ai/                 # AI相關模組
│   ├── api/                # API端點
│   ├── collectors/         # 數據收集器
│   ├── storage/            # 數據存儲
│   └── ...
├── frontend-react/         # 前端源代碼
│   ├── src/               # React組件
│   ├── public/            # 靜態資源
│   └── ...
├── docker-compose.yml     # Docker編排
├── env.example           # 環境變數範例
└── README.md            # 專案說明
```

## 開發指南

### 本地開發

```bash
# 後端開發
cd src
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py

# 前端開發
cd frontend-react
npm install
npm run dev
```

### 測試

```bash
# 運行測試
python -m pytest tests/

# 測試API連接
python tests/test_api_connections.py
```

## 部署

### 本地開發部署

```bash
# 使用啟動腳本（推薦）
./start.sh

# 或使用通用部署腳本
./deploy.sh dev
```

### Debian 部署

```bash
# 本地Debian（Docker已安裝）
./deploy-debian.sh --local

# GCP Debian（完整設置）
./deploy-debian.sh --gcp

# 或使用通用部署腳本
./deploy.sh debian
```

### 生產環境部署

1. 設置生產環境變數
2. 配置SSL證書
3. 設置域名和DNS
4. 運行部署腳本

```bash
./deploy.sh
```

### 監控

- **Prometheus**：http://localhost:9090
- **Grafana**：http://localhost:3001
- **MinIO Console**：http://localhost:9001

## 貢獻指南

1. Fork 專案
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

## 授權

本專案採用 MIT 授權 - 查看 [LICENSE](LICENSE) 文件了解詳情。

## 支援

如有問題或建議，請：

1. 查看 [文檔](docs/)
2. 開啟 [Issue](https://github.com/your-username/community-ai-agent/issues)
3. 聯繫維護者

## 致謝

- Apache Local Community Taipei 社群
- 所有貢獻者和測試用戶
- 開源社群的支持

---

**注意**：請確保不要將包含真實API密鑰的 `.env` 文件提交到版本控制系統中。