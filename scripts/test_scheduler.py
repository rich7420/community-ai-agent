#!/usr/bin/env python3
"""
定時收集資料功能測試腳本
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 添加src目錄到Python路徑
sys.path.append('/app/src')

# 載入環境變數
load_dotenv()

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_environment_variables():
    """測試環境變數配置"""
    print("🔍 檢查環境變數配置...")
    
    required_vars = [
        'SLACK_BOT_TOKEN',
        'SLACK_APP_TOKEN', 
        'GITHUB_TOKEN',
        'DATABASE_URL',
        'GOOGLE_API_KEY',
        'OPENROUTER_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your-'):
            missing_vars.append(var)
        else:
            print(f"✅ {var}: 已配置")
    
    if missing_vars:
        print(f"❌ 缺少環境變數: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ 所有必要的環境變數都已配置")
        return True

def test_collectors():
    """測試收集器初始化"""
    print("\n🔍 測試收集器初始化...")
    
    try:
        from collectors.slack_collector import SlackCollector
        from collectors.github_collector import GitHubCollector
        
        # 測試Slack收集器
        slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
        slack_app_token = os.getenv('SLACK_APP_TOKEN')
        
        if slack_bot_token and slack_app_token and not slack_bot_token.startswith('your-'):
            try:
                slack_collector = SlackCollector(slack_bot_token, slack_app_token)
                print("✅ Slack收集器初始化成功")
            except Exception as e:
                print(f"❌ Slack收集器初始化失敗: {e}")
                return False
        else:
            print("⚠️ Slack收集器未配置或使用預設值")
        
        # 測試GitHub收集器
        github_token = os.getenv('GITHUB_TOKEN')
        
        if github_token and not github_token.startswith('your-'):
            try:
                github_collector = GitHubCollector(github_token)
                print("✅ GitHub收集器初始化成功")
            except Exception as e:
                print(f"❌ GitHub收集器初始化失敗: {e}")
                return False
        else:
            print("⚠️ GitHub收集器未配置或使用預設值")
        
        return True
        
    except Exception as e:
        print(f"❌ 收集器測試失敗: {e}")
        return False

def test_database_connection():
    """測試數據庫連接"""
    print("\n🔍 測試數據庫連接...")
    
    try:
        from storage.postgres_storage import PostgreSQLStorage
        
        postgres_storage = PostgreSQLStorage()
        print("✅ PostgreSQL連接成功")
        return True
        
    except Exception as e:
        print(f"❌ 數據庫連接失敗: {e}")
        return False

def test_embedding_generator():
    """測試嵌入生成器"""
    print("\n🔍 測試嵌入生成器...")
    
    try:
        from ai.gemini_embedding_generator import GeminiEmbeddingGenerator
        
        embedding_generator = GeminiEmbeddingGenerator()
        test_embedding = embedding_generator.generate_embedding("測試文本")
        
        if test_embedding:
            print("✅ 嵌入生成器測試成功")
            return True
        else:
            print("❌ 嵌入生成器返回空結果")
            return False
        
    except Exception as e:
        print(f"❌ 嵌入生成器測試失敗: {e}")
        return False

def test_scheduler():
    """測試調度器"""
    print("\n🔍 測試調度器...")
    
    try:
        from scheduler.cron_jobs import CronJobScheduler
        
        scheduler = CronJobScheduler()
        print("✅ 調度器初始化成功")
        
        # 檢查任務狀態
        print(f"📊 任務狀態: {scheduler.job_status}")
        
        return True
        
    except Exception as e:
        print(f"❌ 調度器測試失敗: {e}")
        return False

def main():
    """主函數"""
    print("🚀 定時收集資料功能測試")
    print("=" * 50)
    
    tests = [
        test_environment_variables,
        test_collectors,
        test_database_connection,
        test_embedding_generator,
        test_scheduler
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 測試執行失敗: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！定時收集資料功能正常")
        return 0
    else:
        print("⚠️ 部分測試失敗，請檢查配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())
