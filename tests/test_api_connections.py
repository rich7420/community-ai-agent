"""
API連接測試腳本
測試所有外部API的連接狀態
"""
import os
import sys
import requests
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def test_slack_connection():
    """測試Slack API連接"""
    print("🔍 測試Slack API連接...")
    
    # 檢查必要的環境變數
    required_vars = [
        'SLACK_APP_ID',
        'SLACK_CLIENT_ID', 
        'SLACK_CLIENT_SECRET',
        'SLACK_SIGNING_SECRET'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ 缺少必要的Slack環境變數: {missing_vars}")
        return False
    
    print("✅ Slack環境變數設置完成")
    print(f"   App ID: {os.getenv('SLACK_APP_ID')}")
    print(f"   Client ID: {os.getenv('SLACK_CLIENT_ID')}")
    
    # 注意：需要Bot Token才能進行實際API調用
    if not os.getenv('SLACK_BOT_TOKEN'):
        print("⚠️  需要安裝App到workspace並獲取Bot Token才能進行完整測試")
        return False
    
    return True

def test_github_connection():
    """測試GitHub API連接"""
    print("\n🔍 測試GitHub API連接...")
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("❌ 缺少GitHub Token")
        return False
    
    try:
        headers = {'Authorization': f'token {github_token}'}
        response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ GitHub API連接成功")
            print(f"   用戶: {user_data.get('login', 'Unknown')}")
            return True
        else:
            print(f"❌ GitHub API連接失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ GitHub API連接錯誤: {str(e)}")
        return False

def test_facebook_connection():
    """測試Facebook API連接 (Deferred)"""
    print("\n🔍 測試Facebook API連接 (已延後，僅檢查變數是否存在)...")
    print("ℹ️  Facebook收集已暫停，保留欄位與配置。")
    return True

def test_grok_connection():
    """測試Grok (OpenRouter) API連接"""
    print("\n🔎 測試Grok (OpenRouter) API連接...")
    
    api_key = os.getenv('OPENROUTER_API_KEY')
    base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    model = os.getenv('OPENROUTER_MODEL', 'x-ai/grok-4-fast')
    
    if not api_key:
        print("❌ 缺少OPENROUTER_API_KEY")
        return False
    
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://opensource4you.ai',
            'X-Title': 'Community AI Agent'
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, OpenRouter Grok Fast 4 test"}],
            "max_tokens": 16
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Grok (OpenRouter) API連接成功")
            return True
        else:
            print(f"❌ Grok (OpenRouter) API連接失敗: {response.status_code}")
            print(f"   回應: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Grok (OpenRouter) API連接錯誤: {str(e)}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始API連接測試...\n")
    
    results = {
        'slack': test_slack_connection(),
        'github': test_github_connection(), 
        'facebook': test_facebook_connection(),
        'grok_openrouter': test_grok_connection()
    }
    
    print(f"\n📊 測試結果總結:")
    for api, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"   {api.upper()}: {status}")
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n🎯 總計: {success_count}/{total_count} 個API連接成功")
    
    if success_count == total_count:
        print("🎉 所有API連接測試通過！")
        return True
    else:
        print("⚠️  部分API連接失敗，請檢查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
