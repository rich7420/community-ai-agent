#!/usr/bin/env python3
"""
修復用戶映射問題
"""
import sys
import os
sys.path.append('/app')

from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
from src.utils.pii_filter import PIIFilter

def fix_user_mappings():
    """修復用戶映射問題"""
    print("🔧 修復用戶映射問題")
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
            LIMIT 10
        """)
        
        active_users = cur.fetchall()
        for i, user in enumerate(active_users, 1):
            print(f"  {i}. {user['author_anon']} - {user['count']} 條訊息")
        
        # 2. 檢查這些用戶是否有映射
        print("\n2. 檢查用戶映射:")
        for user in active_users[:5]:  # 只檢查前5個
            cur.execute("""
                SELECT anonymized_id, display_name, real_name
                FROM user_name_mappings 
                WHERE anonymized_id = %s
            """, (user['author_anon'],))
            
            mapping = cur.fetchone()
            if mapping:
                print(f"  ✅ {user['author_anon']} -> {mapping['display_name']}")
            else:
                print(f"  ❌ {user['author_anon']} -> 沒有映射")
        
        # 3. 嘗試從Slack數據中提取用戶信息
        print("\n3. 嘗試從Slack數據中提取用戶信息:")
        for user in active_users[:5]:
            cur.execute("""
                SELECT metadata
                FROM community_data 
                WHERE platform = 'slack' AND author_anon = %s
                AND metadata->>'user_profile' IS NOT NULL
                AND metadata->>'user_profile' != '{}'
                LIMIT 1
            """, (user['author_anon'],))
            
            result = cur.fetchone()
            if result and result['metadata']:
                user_profile = result['metadata'].get('user_profile', {})
                if user_profile:
                    real_name = user_profile.get('real_name', '')
                    display_name = user_profile.get('display_name', '')
                    name = user_profile.get('name', '')
                    
                    print(f"  {user['author_anon']}:")
                    print(f"    real_name: {real_name}")
                    print(f"    display_name: {display_name}")
                    print(f"    name: {name}")
                    
                    # 創建映射
                    if real_name or display_name or name:
                        final_name = real_name or display_name or name
                        try:
                            pii_filter.add_user_mapping(
                                'slack',
                                user['author_anon'],
                                user['author_anon'],
                                final_name,
                                real_name,
                                [display_name, name] if display_name != name else [display_name],
                                []
                            )
                            print(f"    ✅ 已創建映射: {user['author_anon']} -> {final_name}")
                        except Exception as e:
                            print(f"    ❌ 創建映射失敗: {e}")
                else:
                    print(f"  {user['author_anon']}: 沒有用戶資料")
            else:
                print(f"  {user['author_anon']}: 沒有找到用戶資料")
        
        # 4. 檢查修復後的映射
        print("\n4. 檢查修復後的映射:")
        for user in active_users[:5]:
            display_name = pii_filter._get_display_name_by_original_id(user['author_anon'], 'slack')
            if display_name:
                print(f"  ✅ {user['author_anon']} -> {display_name}")
            else:
                print(f"  ❌ {user['author_anon']} -> 仍然沒有映射")
        
        # 5. 為沒有映射的用戶創建通用映射
        print("\n5. 為沒有映射的用戶創建通用映射:")
        for user in active_users[:5]:
            display_name = pii_filter._get_display_name_by_original_id(user['author_anon'], 'slack')
            if not display_name:
                # 創建通用映射
                generic_name = f"用戶_{user['author_anon'][-8:]}"
                try:
                    pii_filter.add_user_mapping(
                        'slack',
                        user['author_anon'],
                        user['author_anon'],
                        generic_name,
                        generic_name,
                        [generic_name],
                        []
                    )
                    print(f"  ✅ 已創建通用映射: {user['author_anon']} -> {generic_name}")
                except Exception as e:
                    print(f"  ❌ 創建通用映射失敗: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 用戶映射修復完成！")
        
    except Exception as e:
        print(f"❌ 修復過程中發生錯誤: {e}")
    finally:
        cur.close()
        return_db_connection(conn)

if __name__ == "__main__":
    fix_user_mappings()

修復用戶映射問題
"""
import sys
import os
sys.path.append('/app')

from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
from src.utils.pii_filter import PIIFilter

def fix_user_mappings():
    """修復用戶映射問題"""
    print("🔧 修復用戶映射問題")
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
            LIMIT 10
        """)
        
        active_users = cur.fetchall()
        for i, user in enumerate(active_users, 1):
            print(f"  {i}. {user['author_anon']} - {user['count']} 條訊息")
        
        # 2. 檢查這些用戶是否有映射
        print("\n2. 檢查用戶映射:")
        for user in active_users[:5]:  # 只檢查前5個
            cur.execute("""
                SELECT anonymized_id, display_name, real_name
                FROM user_name_mappings 
                WHERE anonymized_id = %s
            """, (user['author_anon'],))
            
            mapping = cur.fetchone()
            if mapping:
                print(f"  ✅ {user['author_anon']} -> {mapping['display_name']}")
            else:
                print(f"  ❌ {user['author_anon']} -> 沒有映射")
        
        # 3. 嘗試從Slack數據中提取用戶信息
        print("\n3. 嘗試從Slack數據中提取用戶信息:")
        for user in active_users[:5]:
            cur.execute("""
                SELECT metadata
                FROM community_data 
                WHERE platform = 'slack' AND author_anon = %s
                AND metadata->>'user_profile' IS NOT NULL
                AND metadata->>'user_profile' != '{}'
                LIMIT 1
            """, (user['author_anon'],))
            
            result = cur.fetchone()
            if result and result['metadata']:
                user_profile = result['metadata'].get('user_profile', {})
                if user_profile:
                    real_name = user_profile.get('real_name', '')
                    display_name = user_profile.get('display_name', '')
                    name = user_profile.get('name', '')
                    
                    print(f"  {user['author_anon']}:")
                    print(f"    real_name: {real_name}")
                    print(f"    display_name: {display_name}")
                    print(f"    name: {name}")
                    
                    # 創建映射
                    if real_name or display_name or name:
                        final_name = real_name or display_name or name
                        try:
                            pii_filter.add_user_mapping(
                                'slack',
                                user['author_anon'],
                                user['author_anon'],
                                final_name,
                                real_name,
                                [display_name, name] if display_name != name else [display_name],
                                []
                            )
                            print(f"    ✅ 已創建映射: {user['author_anon']} -> {final_name}")
                        except Exception as e:
                            print(f"    ❌ 創建映射失敗: {e}")
                else:
                    print(f"  {user['author_anon']}: 沒有用戶資料")
            else:
                print(f"  {user['author_anon']}: 沒有找到用戶資料")
        
        # 4. 檢查修復後的映射
        print("\n4. 檢查修復後的映射:")
        for user in active_users[:5]:
            display_name = pii_filter._get_display_name_by_original_id(user['author_anon'], 'slack')
            if display_name:
                print(f"  ✅ {user['author_anon']} -> {display_name}")
            else:
                print(f"  ❌ {user['author_anon']} -> 仍然沒有映射")
        
        # 5. 為沒有映射的用戶創建通用映射
        print("\n5. 為沒有映射的用戶創建通用映射:")
        for user in active_users[:5]:
            display_name = pii_filter._get_display_name_by_original_id(user['author_anon'], 'slack')
            if not display_name:
                # 創建通用映射
                generic_name = f"用戶_{user['author_anon'][-8:]}"
                try:
                    pii_filter.add_user_mapping(
                        'slack',
                        user['author_anon'],
                        user['author_anon'],
                        generic_name,
                        generic_name,
                        [generic_name],
                        []
                    )
                    print(f"  ✅ 已創建通用映射: {user['author_anon']} -> {generic_name}")
                except Exception as e:
                    print(f"  ❌ 創建通用映射失敗: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 用戶映射修復完成！")
        
    except Exception as e:
        print(f"❌ 修復過程中發生錯誤: {e}")
    finally:
        cur.close()
        return_db_connection(conn)

if __name__ == "__main__":
    fix_user_mappings()
