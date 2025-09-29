#!/usr/bin/env python3
"""
完整部署初始化腳本
確保新環境能自動完成所有必要的設置，包括用戶名稱映射
"""
import os
import sys
sys.path.append('/app')

from src.collectors.slack_collector import SlackCollector
from src.collectors.data_merger import DataMerger
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """檢查環境變量是否完整"""
    print("🔍 檢查環境變量...")
    
    required_vars = [
        'SLACK_BOT_TOKEN',
        'SLACK_APP_TOKEN', 
        'POSTGRES_HOST',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 缺少必要的環境變量: {', '.join(missing_vars)}")
        return False
    
    print("✅ 環境變量檢查通過")
    return True

def initialize_database():
    """初始化數據庫連接"""
    print("🗄️ 初始化數據庫連接...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 檢查必要的表是否存在
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('community_data', 'user_name_mappings')
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        if 'community_data' not in tables:
            print("❌ community_data 表不存在，請先運行數據庫初始化")
            return False
        
        if 'user_name_mappings' not in tables:
            print("❌ user_name_mappings 表不存在，請先運行數據庫初始化")
            return False
        
        cur.close()
        return_db_connection(conn)
        print("✅ 數據庫連接和表結構檢查通過")
        return True
        
    except Exception as e:
        print(f"❌ 數據庫連接失敗: {e}")
        return False

def initialize_user_mappings():
    """初始化用戶名稱映射"""
    print("👥 初始化用戶名稱映射...")
    
    try:
        # 獲取環境變量
        bot_token = os.getenv('SLACK_BOT_TOKEN')
        app_token = os.getenv('SLACK_APP_TOKEN')
        
        # 初始化Slack收集器
        collector = SlackCollector(bot_token, app_token)
        print("✅ Slack收集器初始化成功")
        
        # 獲取所有用戶信息
        print("📊 獲取所有用戶信息...")
        all_users = collector.user_cache
        print(f"✅ 獲取到 {len(all_users)} 個用戶信息")
        
        # 連接到數據庫
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 清理現有用戶映射
        print("🧹 清理現有用戶映射...")
        cur.execute("DELETE FROM user_name_mappings WHERE platform = 'slack'")
        conn.commit()
        print("✅ 現有用戶映射已清理")
        
        # 插入新的用戶映射
        print("💾 插入新的用戶映射...")
        inserted_count = 0
        
        # 創建DataMerger實例來使用PIIFilter
        merger = DataMerger()
        
        for user_id, user_info in all_users.items():
            real_name = user_info.get('real_name') or user_info.get('name') or 'Unknown User'
            display_name = user_info.get('real_name') or user_info.get('name', 'Unknown User')
            
            # 使用PIIFilter獲取一致的匿名化ID
            anonymized_id = merger.pii_filter.anonymize_user(user_id, real_name)
            
            cur.execute("""
                INSERT INTO user_name_mappings (platform, original_user_id, anonymized_id, display_name, real_name, aliases)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (platform, original_user_id) DO UPDATE SET
                    anonymized_id = EXCLUDED.anonymized_id,
                    display_name = EXCLUDED.display_name,
                    real_name = EXCLUDED.real_name,
                    aliases = EXCLUDED.aliases,
                    updated_at = NOW();
            """, ('slack', user_id, anonymized_id, display_name, display_name, []))
            inserted_count += 1
            
            if inserted_count % 100 == 0:
                print(f"  已插入 {inserted_count} 個用戶映射...")
        
        conn.commit()
        print(f"✅ 成功插入 {inserted_count} 個用戶映射")
        
        # 驗證用戶映射
        print("\n🔍 驗證用戶映射...")
        cur.execute("""
            SELECT COUNT(*) as total_count
            FROM user_name_mappings
            WHERE platform = 'slack' AND is_active = TRUE
        """)
        result = cur.fetchone()
        print(f"✅ 數據庫中共有 {result['total_count']} 個活躍的用戶映射")
        
        cur.close()
        return_db_connection(conn)
        return True
        
    except Exception as e:
        logger.error(f"初始化用戶映射失敗: {e}")
        return False

def collect_initial_data():
    """收集初始數據"""
    print("📊 收集初始Slack數據...")
    
    try:
        bot_token = os.getenv('SLACK_BOT_TOKEN')
        app_token = os.getenv('SLACK_APP_TOKEN')
        
        collector = SlackCollector(bot_token, app_token)
        merger = DataMerger()
        
        print("📊 收集最近7天的Slack數據...")
        slack_messages = collector.collect_all_channels(days_back=7)
        print(f"✅ 收集到 {len(slack_messages)} 條訊息")
        
        print("💾 開始保存數據...")
        standardized_records = merger.merge_slack_data(slack_messages)
        
        saved_count = 0
        for i, record in enumerate(standardized_records):
            if merger.save_record(record):
                saved_count += 1
            if (i + 1) % 100 == 0:
                print(f"  已保存 {i + 1} 條記錄...")
        
        print(f"✅ 成功保存 {saved_count} 條記錄")
        return True
        
    except Exception as e:
        logger.error(f"收集初始數據失敗: {e}")
        return False

def verify_system():
    """驗證系統是否正常工作"""
    print("🔍 驗證系統功能...")
    
    try:
        from src.mcp.user_stats_mcp import UserStatsMCP
        
        # 測試UserStatsMCP
        user_stats_mcp = UserStatsMCP()
        report = user_stats_mcp.get_formatted_user_activity_report(platform='slack', days_back=30, limit=3)
        
        # 檢查報告中是否包含真實名稱而不是匿名化ID
        has_real_names = any(name in report for name in ['蔡嘉平', '周呈陽', 'frankvicky', 'Wei Lee', '劉哲佑'])
        has_anon_ids = 'user_' in report
        
        if has_real_names and not has_anon_ids:
            print("✅ 用戶名稱顯示功能正常")
            return True
        else:
            print("❌ 用戶名稱顯示功能異常")
            return False
            
    except Exception as e:
        logger.error(f"系統驗證失敗: {e}")
        return False

def main():
    """主函數"""
    print("🚀 開始完整部署初始化")
    print("=" * 60)
    
    # 1. 檢查環境
    if not check_environment():
        print("❌ 環境檢查失敗，請檢查環境變量設置")
        return False
    
    # 2. 初始化數據庫
    if not initialize_database():
        print("❌ 數據庫初始化失敗")
        return False
    
    # 3. 初始化用戶映射
    if not initialize_user_mappings():
        print("❌ 用戶映射初始化失敗")
        return False
    
    # 4. 收集初始數據
    if not collect_initial_data():
        print("❌ 初始數據收集失敗")
        return False
    
    # 5. 驗證系統
    if not verify_system():
        print("❌ 系統驗證失敗")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 完整部署初始化成功！")
    print("✅ 系統已準備就緒，用戶名稱顯示功能正常")
    return True

if __name__ == "__main__":
    if main():
        print("\n🎯 現在可以正常使用QA系統了！")
    else:
        print("\n❌ 部署初始化失敗，請檢查錯誤信息")
