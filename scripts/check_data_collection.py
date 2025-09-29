#!/usr/bin/env python3
"""
檢查原始用戶數據收集問題
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check_user_data_collection():
    """檢查用戶數據收集問題"""
    print("🔍 檢查用戶數據收集問題")
    print("=" * 60)
    
    # 數據庫連接參數
    db_params = {
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'community_ai'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }
    
    try:
        # 連接數據庫
        conn = psycopg2.connect(**db_params)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 檢查最活躍的用戶的原始數據
        problematic_users = ['user_229289f0', 'user_72abaa64', 'user_f93ed372']
        
        for user_id in problematic_users:
            print(f"\n👤 檢查用戶: {user_id}")
            
            # 檢查原始metadata
            cur.execute("""
                SELECT metadata, timestamp, content
                FROM community_data 
                WHERE author_anon = %s AND platform = 'slack'
                ORDER BY timestamp DESC
                LIMIT 3
            """, (user_id,))
            
            records = cur.fetchall()
            print(f"  📊 找到 {len(records)} 條記錄")
            
            for i, record in enumerate(records):
                print(f"    Record {i+1}:")
                print(f"      timestamp: {record['timestamp']}")
                print(f"      content: {record['content'][:50]}...")
                print(f"      metadata keys: {list(record['metadata'].keys()) if record['metadata'] else 'None'}")
                
                if record['metadata']:
                    # 檢查用戶相關字段
                    user_fields = ['user', 'user_profile', 'real_name', 'display_name', 'user_name', 'name']
                    for field in user_fields:
                        if field in record['metadata']:
                            print(f"      {field}: {record['metadata'][field]}")
        
        # 檢查是否有用戶信息但沒有被正確解析
        print(f"\n🔍 檢查所有用戶的metadata結構:")
        cur.execute("""
            SELECT DISTINCT 
                jsonb_object_keys(metadata) as key_name,
                COUNT(*) as count
            FROM community_data 
            WHERE platform = 'slack' AND metadata IS NOT NULL
            GROUP BY jsonb_object_keys(metadata)
            ORDER BY count DESC
            LIMIT 20
        """)
        
        metadata_keys = cur.fetchall()
        print(f"  📊 metadata字段統計:")
        for key_info in metadata_keys:
            print(f"    {key_info['key_name']}: {key_info['count']} 次")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("🎯 檢查完成！")
        
    except Exception as e:
        print(f"❌ 檢查失敗: {e}")

if __name__ == "__main__":
    check_user_data_collection()
