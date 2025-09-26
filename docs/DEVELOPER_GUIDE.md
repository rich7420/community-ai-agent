# Community AI Agent 開發者指南

## 專案架構

```
community-ai-agent/
├── src/
│   ├── collectors/          # 數據收集器
│   │   ├── slack_collector.py
│   │   ├── github_collector.py
│   │   └── data_merger.py
│   ├── storage/             # 存儲層
│   │   ├── postgres_storage.py
│   │   └── minio_storage.py
│   ├── ai/                  # AI 組件
│   │   ├── rag_system.py
│   │   ├── grok_llm.py
│   │   ├── qa_system.py
│   │   └── prompts.py
│   ├── bot/                 # Bot 整合
│   │   └── slack_bot.py
│   ├── frontend/            # 前端
│   │   └── app.py
│   └── utils/               # 工具函數
│       ├── pii_filter.py
│       └── error_handler.py
├── docker/                  # Docker 配置
├── monitoring/              # 監控配置
├── tests/                   # 測試
└── docs/                    # 文檔
```

## 開發環境設置

### 1. 克隆專案
```bash
git clone <repository-url>
cd community-ai-agent
```

### 2. 設置虛擬環境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

### 3. 安裝依賴
```bash
pip install -r requirements.txt
```

### 4. 環境變數設置
```bash
cp env.example .env
# 編輯 .env 文件，填入必要的 API 密鑰
```

### 5. 啟動開發環境
```bash
docker-compose up -d
```

## 核心組件說明

### 數據收集器 (Collectors)

#### Slack Collector
- 收集頻道訊息
- 統計用戶活動
- 處理反應和回覆

```python
from collectors.slack_collector import SlackCollector

collector = SlackCollector()
messages = collector.collect_messages(channel_id)
```

#### GitHub Collector
- 收集 Issues 和 PRs
- 統計提交記錄
- 分析貢獻者活動

```python
from collectors.github_collector import GitHubCollector

collector = GitHubCollector()
issues = collector.collect_issues(repo_name)
```

### AI 組件

#### RAG 系統
- 向量相似度搜索
- 文檔檢索
- 上下文管理

```python
from ai.rag_system import CommunityRAGSystem

rag = CommunityRAGSystem(db_connection_string, collection_name)
results = rag.search_similar(query, top_k=5)
```

#### Q&A 系統
- 問題理解
- 答案生成
- 來源引用

```python
from ai.qa_system import CommunityQASystem

qa = CommunityQASystem(rag_system, llm)
result = qa.ask_question("What are the recent updates?")
```

### 存儲層

#### PostgreSQL
- 結構化數據存儲
- 向量搜索 (pgvector)
- 關係數據管理

#### MinIO Object Storage
- 大數據存儲
- Parquet 格式
- 數據湖架構

## API 文檔

### REST API 端點

#### 問答 API
```
POST /api/ask
Content-Type: application/json

{
  "question": "What are the recent updates?",
  "user_id": "U123456"
}

Response:
{
  "answer": "Based on recent activity...",
  "sources": [...],
  "confidence": 0.85
}
```

#### 週報 API
```
GET /api/weekly-report

Response:
{
  "report": "Weekly Community Report...",
  "stats": {
    "slack": {...},
    "github": {...}
  }
}
```

### Slack Bot API

#### 指令
- `/ask-community [問題]` - 提問
- `/weekly-report` - 生成週報
- `/optout` - 退出數據收集

#### 事件
- `channel_created` - 新頻道創建
- `channel_rename` - 頻道重命名
- `channel_archive` - 頻道封存

## 測試

### 運行測試
```bash
# 所有測試
pytest

# 特定測試
pytest tests/unit/test_qa_system.py

# 覆蓋率報告
pytest --cov=src --cov-report=html
```

### 測試結構
```
tests/
├── unit/              # 單元測試
├── integration/       # 整合測試
├── performance/       # 性能測試
└── security/          # 安全測試
```

## 部署

### 開發環境
```bash
docker-compose up -d
```

### 生產環境
```bash
# 設置生產環境變數
cp env.prod.example .env.prod
# 編輯 .env.prod

# 啟動生產環境
docker-compose -f docker-compose.prod.yml up -d
```

### 監控
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Kibana: http://localhost:5601

## 貢獻指南

### 代碼規範
- 使用 Black 格式化代碼
- 遵循 PEP 8 風格指南
- 添加類型註解
- 編寫文檔字符串

### 提交規範
```
feat: 新功能
fix: 修復問題
docs: 文檔更新
style: 代碼格式
refactor: 重構
test: 測試
chore: 維護
```

### Pull Request 流程
1. Fork 專案
2. 創建功能分支
3. 提交更改
4. 創建 Pull Request
5. 代碼審查
6. 合併

## 故障排除

### 常見問題

**數據庫連接失敗**
```bash
# 檢查 PostgreSQL 狀態
docker-compose ps postgres

# 查看日誌
docker-compose logs postgres
```

**API 密鑰錯誤**
```bash
# 檢查環境變數
echo $SLACK_BOT_TOKEN
echo $GITHUB_TOKEN
```

**性能問題**
```bash
# 查看資源使用
docker stats

# 檢查日誌
docker-compose logs app
```

## 監控與維護

### 日誌查看
```bash
# 應用日誌
docker-compose logs -f app

# 所有服務日誌
docker-compose logs -f
```

### 備份
```bash
# 手動備份
./scripts/backup.sh

# 恢復
./scripts/restore.sh -d 20240101_120000
```

### 更新
```bash
# 拉取最新代碼
git pull origin main

# 重新構建
docker-compose build

# 重啟服務
docker-compose up -d
```

---

**注意**: 本指南會隨著專案發展持續更新，請定期查看最新版本。
