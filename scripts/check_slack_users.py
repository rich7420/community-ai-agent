#!/usr/bin/env python3
"""
檢查Slack用戶快取和映射問題
"""
import sys
import os
sys.path.append('/app')

from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
from src.utils.pii_filter import PIIFilter

def check_slack_users():
    """檢查Slack用戶問題"""
    print("🔍 檢查Slack用戶問題")
    print("=" * 50)
    
    pii_filter = PIIFilter()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. 檢查最活躍的用戶
        print("1. 最活躍的用戶:")
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
        
        # 2. 檢查這些用戶的原始Slack ID
        print("\n2. 檢查原始Slack ID:")
        for user in active_users:
            cur.execute("""
                SELECT DISTINCT metadata->>'user' as slack_user_id
                FROM community_data 
                WHERE platform = 'slack' AND author_anon = %s
                AND metadata->>'user' IS NOT NULL
                LIMIT 1
            """, (user['author_anon'],))
            
            result = cur.fetchone()
            if result and result['slack_user_id']:
                print(f"  {user['author_anon']} -> Slack ID: {result['slack_user_id']}")
            else:
                print(f"  {user['author_anon']} -> 沒有找到Slack ID")
        
        # 3. 檢查數據庫中的映射
        print("\n3. 檢查數據庫映射:")
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
        
        # 4. 檢查是否有正確的Slack ID映射
        print("\n4. 檢查Slack ID映射:")
        for user in active_users:
            # 先找到對應的Slack ID
            cur.execute("""
                SELECT DISTINCT metadata->>'user' as slack_user_id
                FROM community_data 
                WHERE platform = 'slack' AND author_anon = %s
                AND metadata->>'user' IS NOT NULL
                LIMIT 1
            """, (user['author_anon'],))
            
            slack_result = cur.fetchone()
            if slack_result and slack_result['slack_user_id']:
                slack_id = slack_result['slack_user_id']
                # 檢查這個Slack ID是否有正確的映射
                cur.execute("""
                    SELECT anonymized_id, display_name, real_name
                    FROM user_name_mappings 
                    WHERE original_user_id = %s
                """, (slack_id,))
                
                slack_mapping = cur.fetchone()
                if slack_mapping:
                    print(f"  {user['author_anon']} (Slack: {slack_id}):")
                    print(f"    Mapped to: {slack_mapping['anonymized_id']}")
                    print(f"    Display Name: {slack_mapping['display_name']}")
                    print(f"    Real Name: {slack_mapping['real_name']}")
                else:
                    print(f"  {user['author_anon']} (Slack: {slack_id}): 沒有正確的Slack ID映射")
            else:
                print(f"  {user['author_anon']}: 沒有找到Slack ID")
        
        print("\n" + "=" * 50)
        print("🎯 問題分析完成！")
        
    except Exception as e:
        print(f"❌ 檢查過程中發生錯誤: {e}")
    finally:
        cur.close()
        return_db_connection(conn)

if __name__ == "__main__":
    check_slack_users()
"""
檢查Slack用戶快取和映射問題
"""
import sys
import os
sys.path.append('/app')

from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
from src.utils.pii_filter import PIIFilter

def check_slack_users():
    """檢查Slack用戶問題"""
    print("🔍 檢查Slack用戶問題")
    print("=" * 50)
    
    pii_filter = PIIFilter()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. 檢查最活躍的用戶
        print("1. 最活躍的用戶:")
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
        
        # 2. 檢查這些用戶的原始Slack ID
        print("\n2. 檢查原始Slack ID:")
        for user in active_users:
            cur.execute("""
                SELECT DISTINCT metadata->>'user' as slack_user_id
                FROM community_data 
                WHERE platform = 'slack' AND author_anon = %s
                AND metadata->>'user' IS NOT NULL
                LIMIT 1
            """, (user['author_anon'],))
            
            result = cur.fetchone()
            if result and result['slack_user_id']:
                print(f"  {user['author_anon']} -> Slack ID: {result['slack_user_id']}")
            else:
                print(f"  {user['author_anon']} -> 沒有找到Slack ID")
        
        # 3. 檢查數據庫中的映射
        print("\n3. 檢查數據庫映射:")
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
        
        # 4. 檢查是否有正確的Slack ID映射
        print("\n4. 檢查Slack ID映射:")
        for user in active_users:
            # 先找到對應的Slack ID
            cur.execute("""
                SELECT DISTINCT metadata->>'user' as slack_user_id
                FROM community_data 
                WHERE platform = 'slack' AND author_anon = %s
                AND metadata->>'user' IS NOT NULL
                LIMIT 1
            """, (user['author_anon'],))
            
            slack_result = cur.fetchone()
            if slack_result and slack_result['slack_user_id']:
                slack_id = slack_result['slack_user_id']
                # 檢查這個Slack ID是否有正確的映射
                cur.execute("""
                    SELECT anonymized_id, display_name, real_name
                    FROM user_name_mappings 
                    WHERE original_user_id = %s
                """, (slack_id,))
                
                slack_mapping = cur.fetchone()
                if slack_mapping:
                    print(f"  {user['author_anon']} (Slack: {slack_id}):")
                    print(f"    Mapped to: {slack_mapping['anonymized_id']}")
                    print(f"    Display Name: {slack_mapping['display_name']}")
                    print(f"    Real Name: {slack_mapping['real_name']}")
                else:
                    print(f"  {user['author_anon']} (Slack: {slack_id}): 沒有正確的Slack ID映射")
            else:
                print(f"  {user['author_anon']}: 沒有找到Slack ID")
        
        print("\n" + "=" * 50)
        print("🎯 問題分析完成！")
        
    except Exception as e:
        print(f"❌ 檢查過程中發生錯誤: {e}")
    finally:
        cur.close()
        return_db_connection(conn)

if __name__ == "__main__":
    check_slack_users()
