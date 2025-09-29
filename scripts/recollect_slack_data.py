#!/usr/bin/env python3
"""
重新收集Slack數據以修復用戶名稱問題
"""
import os
import sys
sys.path.append('/app')

from src.collectors.slack_collector import SlackCollector
from src.collectors.data_merger import DataMerger
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

def recollect_slack_data():
    """重新收集Slack數據"""
    print("🔄 重新收集Slack數據以修復用戶名稱問題")
    print("=" * 60)
    
    try:
        # 獲取環境變量
        bot_token = os.getenv('SLACK_BOT_TOKEN')
        app_token = os.getenv('SLACK_APP_TOKEN')
        
        if not bot_token or not app_token:
            print("❌ 缺少Slack token環境變量")
            return
        
        # 初始化收集器
        collector = SlackCollector(bot_token, app_token)
        merger = DataMerger()
        
        print("✅ Slack收集器初始化成功")
        
        # 收集最近7天的數據
        print("📊 開始收集最近7天的Slack數據...")
        messages = collector.collect_all_channels(days_back=7)
        
        print(f"✅ 收集到 {len(messages)} 條訊息")
        
        # 轉換為標準格式並保存
        print("💾 開始保存數據...")
        saved_count = 0
        
        for msg in messages:
            try:
                # 轉換為標準格式
                standard_record = merger._convert_slack_to_standard(msg)
                
                if standard_record:
                    # 保存到數據庫
                    merger.save_record(standard_record)
                    saved_count += 1
                    
                    if saved_count % 100 == 0:
                        print(f"  已保存 {saved_count} 條記錄...")
                        
            except Exception as e:
                print(f"  ⚠️  保存記錄失敗: {e}")
                continue
        
        print(f"✅ 成功保存 {saved_count} 條記錄")
        
        # 驗證用戶信息是否正確保存
        print("\n🔍 驗證用戶信息保存情況...")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 檢查最近保存的記錄
        cur.execute("""
            SELECT DISTINCT 
                author_anon,
                metadata->>'real_name' as real_name,
                metadata->>'display_name' as display_name,
                metadata->>'user_name' as user_name,
                metadata->>'name' as name
            FROM community_data 
            WHERE platform = 'slack' 
                AND created_at > NOW() - INTERVAL '1 hour'
                AND author_anon IS NOT NULL
            ORDER BY author_anon
            LIMIT 10
        """)
        
        recent_records = cur.fetchall()
        print(f"  最近1小時內保存的記錄:")
        for record in recent_records:
            real_name = (record['real_name'] or 
                        record['display_name'] or 
                        record['user_name'] or 
                        record['name'])
            print(f"    {record['author_anon']} -> {real_name or 'No name'}")
        
        cur.close()
        return_db_connection(conn)
        
        print("\n" + "=" * 60)
        print("🎯 重新收集完成！")
        
    except Exception as e:
        print(f"❌ 重新收集失敗: {e}")

if __name__ == "__main__":
    recollect_slack_data()
