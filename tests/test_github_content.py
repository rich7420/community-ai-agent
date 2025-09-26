"""
GitHub內容讀取測試腳本
展示GitHub API可以讀取的具體內容
"""
import os
import sys
from dotenv import load_dotenv
from github import Github
from github.GithubException import GithubException

# 載入環境變數
load_dotenv()

def test_github_repo_content():
    """測試GitHub倉庫內容讀取"""
    print("📁 測試GitHub倉庫內容讀取...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ 缺少GITHUB_TOKEN")
        return False
    
    try:
        g = Github(github_token)
        repo = g.get_repo("opensource4you/readme")
        
        print(f"✅ 成功訪問倉庫: {repo.full_name}")
        print(f"   描述: {repo.description}")
        print(f"   語言: {repo.language}")
        print(f"   星標數: {repo.stargazers_count}")
        print(f"   Fork數: {repo.forks_count}")
        print(f"   觀看數: {repo.watchers_count}")
        print(f"   最後更新: {repo.updated_at}")
        
        # 讀取README內容
        try:
            readme = repo.get_readme()
            readme_content = readme.decoded_content.decode('utf-8')
            print(f"\n📄 README內容預覽 (前500字):")
            print("-" * 50)
            print(readme_content[:500] + "..." if len(readme_content) > 500 else readme_content)
            print("-" * 50)
        except Exception as e:
            print(f"⚠️ 無法讀取README: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 倉庫內容讀取錯誤: {str(e)}")
        return False

def test_github_issues():
    """測試GitHub Issues讀取"""
    print("\n🐛 測試GitHub Issues讀取...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ 缺少GITHUB_TOKEN")
        return False
    
    try:
        g = Github(github_token)
        repo = g.get_repo("opensource4you/readme")
        
        # 獲取最近的5個issues
        issues = list(repo.get_issues(state='all', sort='created', direction='desc')[:5])
        
        print(f"✅ 找到 {len(issues)} 個issues:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. #{issue.number}: {issue.title}")
            print(f"      狀態: {'開啟' if issue.state == 'open' else '關閉'}")
            print(f"      作者: {issue.user.login}")
            print(f"      創建時間: {issue.created_at}")
            print(f"      標籤: {[label.name for label in issue.labels]}")
            if issue.body:
                body_preview = issue.body[:100] + "..." if len(issue.body) > 100 else issue.body
                print(f"      內容預覽: {body_preview}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Issues讀取錯誤: {str(e)}")
        return False

def test_github_pull_requests():
    """測試GitHub Pull Requests讀取"""
    print("\n🔄 測試GitHub Pull Requests讀取...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ 缺少GITHUB_TOKEN")
        return False
    
    try:
        g = Github(github_token)
        repo = g.get_repo("opensource4you/readme")
        
        # 獲取最近的5個PRs
        pulls = list(repo.get_pulls(state='all', sort='created', direction='desc')[:5])
        
        print(f"✅ 找到 {len(pulls)} 個Pull Requests:")
        for i, pr in enumerate(pulls, 1):
            print(f"   {i}. #{pr.number}: {pr.title}")
            print(f"      狀態: {pr.state}")
            print(f"      作者: {pr.user.login}")
            print(f"      創建時間: {pr.created_at}")
            print(f"      合併時間: {pr.merged_at or '未合併'}")
            if pr.body:
                body_preview = pr.body[:100] + "..." if len(pr.body) > 100 else pr.body
                print(f"      內容預覽: {body_preview}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Pull Requests讀取錯誤: {str(e)}")
        return False

def test_github_commits():
    """測試GitHub Commits讀取"""
    print("\n💾 測試GitHub Commits讀取...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ 缺少GITHUB_TOKEN")
        return False
    
    try:
        g = Github(github_token)
        repo = g.get_repo("opensource4you/readme")
        
        # 獲取最近的5個commits
        commits = list(repo.get_commits()[:5])
        
        print(f"✅ 找到 {len(commits)} 個最近的commits:")
        for i, commit in enumerate(commits, 1):
            print(f"   {i}. {commit.sha[:8]}: {commit.commit.message.split(chr(10))[0]}")
            print(f"      作者: {commit.commit.author.name}")
            print(f"      時間: {commit.commit.author.date}")
            print(f"      修改檔案數: {len(list(commit.files))}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Commits讀取錯誤: {str(e)}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始GitHub內容讀取測試...\n")
    
    # 測試倉庫內容
    repo_ok = test_github_repo_content()
    
    # 測試Issues
    issues_ok = test_github_issues()
    
    # 測試Pull Requests
    prs_ok = test_github_pull_requests()
    
    # 測試Commits
    commits_ok = test_github_commits()
    
    if repo_ok and issues_ok and prs_ok and commits_ok:
        print("🎉 GitHub內容讀取測試完成！")
        print("✅ 可以讀取:")
        print("   - 倉庫基本資訊")
        print("   - README內容")
        print("   - Issues (標題、內容、狀態、標籤)")
        print("   - Pull Requests (標題、內容、狀態)")
        print("   - Commits (提交訊息、作者、時間)")
        return True
    else:
        print("⚠️ 部分GitHub內容讀取測試失敗")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
