"""
Slack Bot功能測試腳本
測試Bot Token的基本功能
"""
import os
import sys
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# 載入環境變數
load_dotenv()

def test_slack_bot_connection():
    """測試Slack Bot連接"""
    print("🤖 測試Slack Bot連接...")
    
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    if not bot_token:
        print("❌ 缺少SLACK_BOT_TOKEN")
        return False
    
    try:
        # 初始化Slack客戶端
        client = WebClient(token=bot_token)
        
        # 測試API連接 - 獲取Bot資訊
        response = client.auth_test()
        
        if response["ok"]:
            print("✅ Slack Bot連接成功")
            print(f"   Bot ID: {response.get('bot_id', 'Unknown')}")
            print(f"   User ID: {response.get('user_id', 'Unknown')}")
            print(f"   Team: {response.get('team', 'Unknown')}")
            return True
        else:
            print(f"❌ Slack Bot連接失敗: {response.get('error', 'Unknown error')}")
            return False
            
    except SlackApiError as e:
        print(f"❌ Slack API錯誤: {e.response['error']}")
        return False
    except Exception as e:
        print(f"❌ 連接錯誤: {str(e)}")
        return False

def test_slack_permissions():
    """測試Slack權限"""
    print("\n🔐 測試Slack權限...")
    
    bot_token = os.getenv('SLACK_BOT_TOKEN')
    if not bot_token:
        print("❌ 缺少SLACK_BOT_TOKEN")
        return False
    
    try:
        client = WebClient(token=bot_token)
        
        # 測試獲取頻道列表
        try:
            channels_response = client.conversations_list(types="public_channel", limit=5)
            if channels_response["ok"]:
                print("✅ 可以讀取公開頻道")
                print(f"   找到 {len(channels_response['channels'])} 個公開頻道")
            else:
                print("❌ 無法讀取公開頻道")
        except SlackApiError as e:
            print(f"❌ 頻道讀取權限不足: {e.response['error']}")
        
        # 測試獲取使用者列表
        try:
            users_response = client.users_list(limit=5)
            if users_response["ok"]:
                print("✅ 可以讀取使用者列表")
                print(f"   找到 {len(users_response['members'])} 個使用者")
            else:
                print("❌ 無法讀取使用者列表")
        except SlackApiError as e:
            print(f"❌ 使用者讀取權限不足: {e.response['error']}")
            
        return True
        
    except Exception as e:
        print(f"❌ 權限測試錯誤: {str(e)}")
        return False

def main():
    """主測試函數"""
    print("🚀 開始Slack Bot測試...\n")
    
    # 測試連接
    connection_ok = test_slack_bot_connection()
    
    if connection_ok:
        # 測試權限
        test_slack_permissions()
        print("\n🎉 Slack Bot基本功能測試完成！")
        return True
    else:
        print("\n❌ Slack Bot連接失敗，請檢查配置")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
