# GitHub 發布檢查清單

## 安全檢查 ✅

- [x] 創建 `.gitignore` 文件，隱藏敏感資訊
- [x] 更新 `env.example` 文件，移除真實API密鑰
- [x] 刪除 `.env.backup` 文件
- [x] 確認 `.env` 文件不會被提交到版本控制
- [x] 檢查代碼中沒有硬編碼的敏感資訊

## 文檔準備 ✅

- [x] 更新 `README.md` 文件
- [x] 創建 `CONTRIBUTING.md` 貢獻指南
- [x] 創建 `LICENSE` 許可證文件
- [x] 創建 `docs/DEPLOYMENT_GUIDE.md` 部署指南
- [x] 創建 `.gitattributes` 文件處理

## CI/CD 設置 ✅

- [x] 創建 `.github/workflows/ci-cd.yml` GitHub Actions
- [x] 設置自動測試流程
- [x] 設置安全掃描
- [x] 設置自動構建和部署

## 代碼質量 ✅

- [x] 確認代碼風格一致
- [x] 確認測試覆蓋率足夠
- [x] 確認文檔完整
- [x] 確認無安全漏洞

## 發布前最後檢查

### 1. 環境變數檢查
```bash
# 確認沒有敏感資訊被提交
git status
git diff --cached

# 檢查 .env 文件是否被忽略
git check-ignore .env
```

### 2. 代碼檢查
```bash
# 運行測試
docker-compose exec app python -m pytest tests/
cd frontend-react && npm test

# 檢查代碼風格
black --check src/
cd frontend-react && npm run lint
```

### 3. 安全檢查
```bash
# 檢查是否有硬編碼的密鑰
grep -r "xoxb-\|ghp_\|sk-or-\|AIzaSy" --exclude-dir=node_modules --exclude-dir=venv --exclude-dir=.git .
```

### 4. 文檔檢查
- [ ] README.md 中的安裝說明是否正確
- [ ] API密鑰獲取指南是否完整
- [ ] 部署步驟是否清晰
- [ ] 貢獻指南是否詳細

## GitHub 發布步驟

### 1. 創建 GitHub 倉庫
```bash
# 在 GitHub 上創建新倉庫
# 然後初始化本地倉庫
git init
git add .
git commit -m "Initial commit: Apache Local Community Taipei AI Agent"
git branch -M main
git remote add origin https://github.com/your-username/community-ai-agent.git
git push -u origin main
```

### 2. 設置倉庫設置
- [ ] 設置倉庫描述
- [ ] 添加主題標籤
- [ ] 設置默認分支
- [ ] 啟用 Issues 和 Discussions
- [ ] 設置分支保護規則

### 3. 創建 Release
- [ ] 創建第一個 Release
- [ ] 添加 Release Notes
- [ ] 標記版本號

### 4. 設置 GitHub Pages（可選）
- [ ] 啟用 GitHub Pages
- [ ] 設置文檔站點

## 後續維護

### 定期檢查
- [ ] 更新依賴包
- [ ] 檢查安全漏洞
- [ ] 更新文檔
- [ ] 監控 Issues 和 PR

### 社區管理
- [ ] 回應 Issues
- [ ] 審查 Pull Requests
- [ ] 維護文檔
- [ ] 發布更新

## 注意事項

⚠️ **重要提醒**：
1. 永遠不要將包含真實API密鑰的 `.env` 文件提交到版本控制
2. 定期更新API密鑰
3. 監控倉庫的安全警報
4. 保持依賴包更新
5. 定期備份數據

## 聯繫方式

如有問題，請：
- 開啟 GitHub Issue
- 聯繫維護者
- 查看文檔

---

**最後更新**：2025-09-26
**版本**：1.0.0
