# 貢獻指南

感謝您對 Apache Local Community Taipei AI Agent 的關注！我們歡迎各種形式的貢獻。

## 如何貢獻

### 報告問題

如果您發現了bug或有功能建議，請：

1. 檢查 [Issues](https://github.com/rich7420/community-ai-agent/issues) 是否已有相關問題
2. 如果沒有，請創建新的 Issue
3. 提供詳細的問題描述和重現步驟

### 提交代碼

1. **Fork 專案**
   ```bash
   git clone https://github.com/rich7420/community-ai-agent.git
   cd community-ai-agent
   ```

2. **創建功能分支**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **設置開發環境**
   ```bash
   # 複製環境變數文件
   cp env.example .env
   
   # 編輯環境變數（使用測試用的API密鑰）
   nano .env
   
   # 啟動開發環境
   docker-compose up -d
   ```

4. **進行開發**
   - 遵循現有的代碼風格
   - 添加必要的測試
   - 更新相關文檔

5. **提交更改**
   ```bash
   git add .
   git commit -m "Add amazing feature"
   git push origin feature/amazing-feature
   ```

6. **創建 Pull Request**
   - 在 GitHub 上創建 Pull Request
   - 提供詳細的更改說明
   - 確保所有測試通過

## 開發規範

### 代碼風格

**Python**
- 使用 Black 進行代碼格式化
- 遵循 PEP 8 規範
- 使用類型提示

```bash
# 安裝開發依賴
pip install black flake8 mypy

# 格式化代碼
black src/

# 檢查代碼風格
flake8 src/

# 類型檢查
mypy src/
```

**TypeScript/React**
- 使用 Prettier 進行代碼格式化
- 遵循 ESLint 規則
- 使用 TypeScript 嚴格模式

```bash
# 安裝依賴
cd frontend-react
npm install

# 格式化代碼
npm run format

# 檢查代碼風格
npm run lint

# 類型檢查
npm run type-check
```

### 提交信息規範

使用 [Conventional Commits](https://www.conventionalcommits.org/) 規範：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

類型包括：
- `feat`: 新功能
- `fix`: 修復bug
- `docs`: 文檔更新
- `style`: 代碼格式調整
- `refactor`: 代碼重構
- `test`: 測試相關
- `chore`: 構建過程或輔助工具的變動

示例：
```
feat(ai): add support for streaming responses
fix(api): resolve timeout issue in question endpoint
docs(readme): update installation instructions
```

### 測試要求

**後端測試**
```bash
# 運行所有測試
pytest tests/

# 運行特定測試
pytest tests/unit/test_qa_system.py

# 運行集成測試
pytest tests/integration/
```

**前端測試**
```bash
cd frontend-react
npm test
npm run test:coverage
```

### 文檔要求

- 新功能需要更新 README.md
- API 變更需要更新文檔
- 複雜邏輯需要添加註釋
- 使用 Markdown 格式

## 專案結構

```
community-ai-agent/
├── src/                    # 後端源代碼
│   ├── ai/                # AI相關模組
│   │   ├── prompts.py     # 提示詞模板
│   │   ├── qa_system.py   # 問答系統
│   │   └── rag_system.py  # RAG系統
│   ├── api/               # API端點
│   ├── collectors/        # 數據收集器
│   ├── storage/           # 數據存儲
│   └── utils/             # 工具函數
├── frontend-react/        # 前端源代碼
│   ├── src/
│   │   ├── components/    # React組件
│   │   ├── hooks/         # 自定義Hooks
│   │   ├── services/      # API服務
│   │   └── store/         # 狀態管理
│   └── public/            # 靜態資源
├── tests/                 # 測試文件
│   ├── unit/             # 單元測試
│   └── integration/      # 集成測試
├── docs/                  # 文檔
├── docker/               # Docker配置
└── scripts/              # 腳本文件
```

## 開發環境設置

### 必要工具

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### 本地開發

1. **後端開發**
   ```bash
   # 創建虛擬環境
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   
   # 安裝依賴
   pip install -r requirements.txt
   
   # 啟動開發服務器
   python src/main.py
   ```

2. **前端開發**
   ```bash
   cd frontend-react
   npm install
   npm run dev
   ```

3. **完整環境**
   ```bash
   # 使用Docker Compose
   docker-compose up -d
   ```

### 測試環境

使用測試用的API密鑰和數據庫：

```bash
# 測試環境變數
cp env.example .env.test
# 編輯 .env.test 使用測試密鑰
```

## 審查流程

### Pull Request 審查

1. **自動檢查**
   - 代碼風格檢查
   - 單元測試
   - 安全掃描

2. **人工審查**
   - 代碼質量
   - 功能正確性
   - 文檔完整性

3. **審查標準**
   - 代碼清晰易懂
   - 測試覆蓋率足夠
   - 無安全漏洞
   - 文檔更新完整

### 審查者指南

- 提供建設性反饋
- 檢查代碼邏輯
- 確認測試覆蓋
- 驗證文檔更新

## 社區準則

### 行為準則

- 保持友善和尊重
- 歡迎不同背景的貢獻者
- 專注於建設性討論
- 尊重不同的觀點和經驗

### 溝通渠道

- GitHub Issues: 問題報告和功能討論
- GitHub Discussions: 一般討論
- Pull Request: 代碼審查和技術討論

## 認可貢獻者

我們會認可所有形式的貢獻：

- 代碼貢獻
- 文檔改進
- 問題報告
- 功能建議
- 社區支持

## 許可證

通過貢獻代碼，您同意您的貢獻將在 MIT 許可證下發布。

## 聯繫方式

如有問題，請：

1. 查看 [文檔](docs/)
2. 開啟 [Issue](https://github.com/your-username/community-ai-agent/issues)
3. 聯繫維護者

感謝您的貢獻！🎉
