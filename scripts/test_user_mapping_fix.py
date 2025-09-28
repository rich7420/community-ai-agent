#!/usr/bin/env python3
"""
測試用戶映射修復
"""
import sys
import os
sys.path.append('/app')

from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
from src.utils.pii_filter import PIIFilter

def test_user_mapping_fix():
    """測試用戶映射修復"""
    print("🧪 測試用戶映射修復")
    print("=" * 50)
    
    pii_filter = PIIFilter()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. 檢查最活躍的用戶
        print("1. 檢查最活躍的用戶:")
        cur.execute("""
            SELECT author_anon, COUNT(*) as count
            FROM community_data 
            WHERE platform = 'slack' AND author_anon IS NOT NULL
            GROUP BY author_anon
            ORDER BY count DESC
            LIMIT 5
        """)
        
        active_users = cur.fetchall()
        for i, user in enumerate(active_users, 1):
            print(f"  {i}. {user['author_anon']} - {user['count']} 條訊息")
        
        # 2. 檢查這些用戶的映射
        print("\n2. 檢查用戶映射:")
        for user in active_users:
            display_name = pii_filter._get_display_name_by_original_id(user['author_anon'], 'slack')
            if display_name and display_name != user['author_anon']:
                print(f"  ✅ {user['author_anon']} -> {display_name}")
            else:
                print(f"  ❌ {user['author_anon']} -> 沒有正確映射")
        
        # 3. 檢查Slack數據中的用戶信息
        print("\n3. 檢查Slack數據中的用戶信息:")
        for user in active_users[:3]:  # 只檢查前3個
            cur.execute("""
                SELECT 
                    metadata->>'user' as slack_user_id,
                    metadata->>'real_name' as real_name,
                    metadata->>'user_name' as user_name,
                    metadata->>'display_name' as display_name,
                    metadata->>'user_profile' as user_profile
                FROM community_data 
                WHERE platform = 'slack' AND author_anon = %s
                AND metadata->>'user' IS NOT NULL
                LIMIT 1
            """, (user['author_anon'],))
            
            result = cur.fetchone()
            if result:
                print(f"  {user['author_anon']}:")
                print(f"    Slack ID: {result['slack_user_id']}")
                print(f"    Real Name: {result['real_name']}")
                print(f"    User Name: {result['user_name']}")
                print(f"    Display Name: {result['display_name']}")
                if result['user_profile']:
                    print(f"    User Profile: {result['user_profile']}")
            else:
                print(f"  {user['author_anon']}: 沒有找到用戶信息")
        
        # 4. 檢查數據庫中的映射
        print("\n4. 檢查數據庫中的映射:")
        for user in active_users:
            cur.execute("""
                SELECT anonymized_id, display_name, real_name, original_user_id
                FROM user_name_mappings 
                WHERE anonymized_id = %s
            """, (user['author_anon'],))
            
            mapping = cur.fetchone()
            if mapping:
                print(f"  {user['author_anon']}:")
                print(f"    Original ID: {mapping['original_user_id']}")
                print(f"    Display Name: {mapping['display_name']}")
                print(f"    Real Name: {mapping['real_name']}")
            else:
                print(f"  {user['author_anon']}: 沒有映射")
        
        print("\n" + "=" * 50)
        print("🎯 測試完成！")
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {e}")
    finally:
        cur.close()
        return_db_connection(conn)

if __name__ == "__main__":
    test_user_mapping_fix()
