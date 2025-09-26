"""
GitHub API功能測試腳本
測試GitHub API的各種功能
"""
import os
import sys
from dotenv import load_dotenv
from github import Github
from github.GithubException import GithubException

# 載入環境變數
load_dotenv()

def test_github_connection():
    """測試GitHub API連接"""
    print("🔍 測試GitHub API連接...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ 缺少GITHUB_TOKEN")
        return False
    
    try:
        # 初始化GitHub客戶端
        g = Github(github_token)
        
        # 測試API連接 - 獲取用戶資訊
        user = g.get_user()
        
        print("✅ GitHub API連接成功")
        print(f"   用戶: {user.login}")
        print(f"   姓名: {user.name or '未設置'}")
        print(f"   公開倉庫數: {user.public_repos}")
        return True
        
    except GithubException as e:
        print(f"❌ GitHub API錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 連接錯誤: {str(e)}")
        return False

def test_github_repo_access():
    """測試GitHub倉庫訪問"""
    print("\n📁 測試GitHub倉庫訪問...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ 缺少GITHUB_TOKEN")
        return False
    
    try:
        g = Github(github_token)
        
        # 測試訪問目標倉庫
        target_repo = "opensource4you/readme"
        repo = g.get_repo(target_repo)
        
        print(f"✅ 成功訪問倉庫: {target_repo}")
        print(f"   描述: {repo.description or '無描述'}")
        print(f"   星標數: {repo.stargazers_count}")
        print(f"   Fork數: {repo.forks_count}")
        
        # 測試獲取最近的issues
        issues = list(repo.get_issues(state='all', sort='created', direction='desc')[:5])
        print(f"   最近5個issues: {len(issues)} 個")
        
        # 測試獲取最近的PRs
        pulls = list(repo.get_pulls(state='all', sort='created', direction='desc')[:5])
        print(f"   最近5個PRs: {len(pulls)} 個")
        
        return True
        
    except GithubException as e:
        print(f"❌ 倉庫訪問錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 倉庫訪問錯誤: {str(e)}")
        return False

def test_github_rate_limit():
    """測試GitHub API速率限制"""
    print("\n⏱️ 測試GitHub API速率限制...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ 缺少GITHUB_TOKEN")
        return False
    
    try:
        g = Github(github_token)
        rate_limit = g.get_rate_limit()
        
        print(f"✅ 速率限制資訊:")
        print(f"   核心API限制: {rate_limit.core.limit}")
        print(f"   核心API剩餘: {rate_limit.core.remaining}")
        print(f"   核心API重置時間: {rate_limit.core.reset}")
        
        if hasattr(rate_limit, 'search'):
            print(f"   搜索API限制: {rate_limit.search.limit}")
            print(f"   搜索API剩餘: {rate_limit.search.remaining}")
        else:
            print("   搜索API: 未啟用")
        
        return True
        
    except Exception as e:
        print(f"❌ 速率限制查詢錯誤: {str(e)}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始GitHub API測試...\n")
    
    # 測試連接
    connection_ok = test_github_connection()
    
    if connection_ok:
        # 測試倉庫訪問
        repo_ok = test_github_repo_access()
        
        # 測試速率限制
        rate_ok = test_github_rate_limit()
        
        if repo_ok and rate_ok:
            print("\n🎉 GitHub API功能測試完成！")
            return True
        else:
            print("\n⚠️ 部分GitHub API功能測試失敗")
            return False
    else:
        print("\n❌ GitHub API連接失敗，請檢查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
