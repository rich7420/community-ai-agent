#!/usr/bin/env python3
"""
初始化用戶名稱映射腳本
確保新環境能正確建立完整的用戶名稱列表
"""
import os
import sys
sys.path.append('/app')

from src.collectors.slack_collector import SlackCollector
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_user_mappings():
    """初始化用戶名稱映射"""
    print("🚀 初始化用戶名稱映射")
    print("=" * 60)
    
    try:
        # 獲取環境變量
        bot_token = os.getenv('SLACK_BOT_TOKEN')
        app_token = os.getenv('SLACK_APP_TOKEN')
        
        if not bot_token or not app_token:
            print("❌ 缺少Slack token環境變量")
            return False
        
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
        
        for user_id, user_info in all_users.items():
            try:
                # 獲取用戶名稱
                real_name = user_info.get('real_name') or user_info.get('name', '')
                display_name = user_info.get('display_name') or real_name
                
                if not real_name and not display_name:
                    continue
                
                # 生成匿名化ID
                anon_id = collector.pii_filter.anonymize_user(user_id, real_name)
                
                # 插入用戶映射
                cur.execute("""
                    INSERT INTO user_name_mappings (
                        platform, original_user_id, anonymized_id, display_name, real_name, aliases, is_active
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (platform, original_user_id) DO UPDATE SET
                        anonymized_id = EXCLUDED.anonymized_id,
                        display_name = EXCLUDED.display_name,
                        real_name = EXCLUDED.real_name,
                        aliases = EXCLUDED.aliases,
                        is_active = EXCLUDED.is_active,
                        updated_at = NOW()
                """, (
                    'slack',
                    user_id,
                    anon_id,
                    display_name,
                    real_name,
                    [user_info.get('name', '')] if user_info.get('name') and user_info.get('name') != real_name else [],
                    True
                ))
                
                inserted_count += 1
                
                if inserted_count % 100 == 0:
                    print(f"  已插入 {inserted_count} 個用戶映射...")
                    
            except Exception as e:
                logger.error(f"插入用戶映射失敗 {user_id}: {e}")
                continue
        
        conn.commit()
        print(f"✅ 成功插入 {inserted_count} 個用戶映射")
        
        # 驗證映射
        print("\n🔍 驗證用戶映射...")
        cur.execute("""
            SELECT COUNT(*) as total_count
            FROM user_name_mappings 
            WHERE platform = 'slack' AND is_active = TRUE
        """)
        result = cur.fetchone()
        print(f"✅ 數據庫中共有 {result['total_count']} 個活躍的用戶映射")
        
        # 檢查最活躍的用戶是否有映射
        cur.execute("""
            SELECT author_anon, COUNT(*) as message_count
            FROM community_data 
            WHERE platform = 'slack' 
                AND author_anon IS NOT NULL
            GROUP BY author_anon
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        
        top_users = cur.fetchall()
        print(f"\n📊 檢查前10名最活躍用戶的映射情況:")
        
        for i, user in enumerate(top_users, 1):
            user_id = user['author_anon']
            cur.execute("""
                SELECT display_name, real_name
                FROM user_name_mappings 
                WHERE anonymized_id = %s AND platform = 'slack' AND is_active = TRUE
            """, (user_id,))
            
            mapping = cur.fetchone()
            if mapping:
                print(f"  {i}. {user_id} -> {mapping['display_name']} ✅")
            else:
                print(f"  {i}. {user_id} -> 無映射 ❌")
        
        cur.close()
        return_db_connection(conn)
        
        print("\n" + "=" * 60)
        print("🎯 用戶名稱映射初始化完成！")
        return True
        
    except Exception as e:
        logger.error(f"初始化用戶映射失敗: {e}")
        return False

def collect_recent_data():
    """收集最近的數據以確保用戶信息完整"""
    print("\n🔄 收集最近的Slack數據...")
    
    try:
        # 獲取環境變量
        bot_token = os.getenv('SLACK_BOT_TOKEN')
        app_token = os.getenv('SLACK_APP_TOKEN')
        
        if not bot_token or not app_token:
            print("❌ 缺少Slack token環境變量")
            return False
        
        # 初始化收集器
        collector = SlackCollector(bot_token, app_token)
        
        # 收集最近3天的數據
        print("📊 收集最近3天的Slack數據...")
        messages = collector.collect_all_channels(days_back=3)
        
        print(f"✅ 收集到 {len(messages)} 條訊息")
        
        # 轉換並保存數據
        from src.collectors.data_merger import DataMerger
        merger = DataMerger()
        
        saved_count = 0
        for msg in messages:
            try:
                standard_record = merger._convert_slack_to_standard(msg)
                if standard_record and merger.save_record(standard_record):
                    saved_count += 1
            except Exception as e:
                logger.error(f"保存記錄失敗: {e}")
                continue
        
        print(f"✅ 成功保存 {saved_count} 條記錄")
        return True
        
    except Exception as e:
        logger.error(f"收集最近數據失敗: {e}")
        return False

if __name__ == "__main__":
    print("🎯 開始初始化用戶名稱映射系統")
    print("=" * 60)
    
    # 步驟1: 初始化用戶映射
    if initialize_user_mappings():
        print("✅ 用戶映射初始化成功")
    else:
        print("❌ 用戶映射初始化失敗")
        sys.exit(1)
    
    # 步驟2: 收集最近數據
    if collect_recent_data():
        print("✅ 最近數據收集成功")
    else:
        print("❌ 最近數據收集失敗")
        sys.exit(1)
    
    print("\n🎉 用戶名稱映射系統初始化完成！")
    print("現在可以正確顯示用戶名稱了。")