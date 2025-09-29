#!/usr/bin/env python3
"""
修復缺失的用戶名稱映射
從社區數據中提取用戶信息並創建映射
"""
import os
import sys
sys.path.append('/app')

from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
import logging

# 配置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_missing_user_mappings():
    """修復缺失的用戶名稱映射"""
    print("🔧 修復缺失的用戶名稱映射")
    print("=" * 60)
    
    try:
        # 連接到數據庫
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 查找有真實名稱但沒有映射的用戶
        print("🔍 查找有真實名稱但沒有映射的用戶...")
        cur.execute("""
            SELECT DISTINCT 
                author_anon,
                metadata->>'real_name' as real_name,
                metadata->>'display_name' as display_name,
                metadata->>'user_name' as user_name,
                metadata->>'name' as name,
                metadata->'user_profile'->>'real_name' as profile_real_name,
                metadata->'user_profile'->>'display_name' as profile_display_name,
                metadata->'user_profile'->>'name' as profile_name
            FROM community_data 
            WHERE platform = 'slack' 
                AND author_anon IS NOT NULL
                AND author_anon NOT IN (
                    SELECT anonymized_id 
                    FROM user_name_mappings 
                    WHERE platform = 'slack' AND is_active = TRUE
                )
                AND (
                    metadata->>'real_name' IS NOT NULL 
                    OR metadata->>'display_name' IS NOT NULL 
                    OR metadata->>'user_name' IS NOT NULL
                    OR metadata->>'name' IS NOT NULL
                    OR metadata->'user_profile'->>'real_name' IS NOT NULL
                    OR metadata->'user_profile'->>'display_name' IS NOT NULL
                    OR metadata->'user_profile'->>'name' IS NOT NULL
                )
            ORDER BY author_anon
        """)
        
        missing_users = cur.fetchall()
        print(f"✅ 找到 {len(missing_users)} 個需要修復的用戶")
        
        if not missing_users:
            print("🎉 所有用戶都有正確的映射！")
            return True
        
        # 修復每個用戶的映射
        fixed_count = 0
        for user in missing_users:
            try:
                # 確定最佳顯示名稱
                display_name = (
                    user['real_name'] or 
                    user['profile_real_name'] or
                    user['display_name'] or 
                    user['profile_display_name'] or
                    user['user_name'] or 
                    user['profile_name'] or
                    user['name']
                )
                
                if not display_name:
                    continue
                
                # 生成一個假的原始用戶ID（因為我們沒有真實的Slack ID）
                # 我們使用匿名化ID作為原始ID，這樣可以建立映射
                original_user_id = f"unknown_{user['author_anon']}"
                
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
                    original_user_id,
                    user['author_anon'],
                    display_name,
                    user['real_name'] or user['profile_real_name'],
                    [user['user_name']] if user['user_name'] and user['user_name'] != display_name else [],
                    True
                ))
                
                fixed_count += 1
                print(f"  ✅ 修復用戶: {user['author_anon']} -> {display_name}")
                
            except Exception as e:
                logger.error(f"修復用戶映射失敗 {user['author_anon']}: {e}")
                continue
        
        conn.commit()
        print(f"\n✅ 成功修復 {fixed_count} 個用戶映射")
        
        # 驗證修復結果
        print("\n🔍 驗證修復結果...")
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
        print("🎯 用戶映射修復完成！")
        return True
        
    except Exception as e:
        logger.error(f"修復用戶映射失敗: {e}")
        return False

if __name__ == "__main__":
    print("🎯 開始修復缺失的用戶名稱映射")
    print("=" * 60)
    
    if fix_missing_user_mappings():
        print("✅ 用戶映射修復成功")
    else:
        print("❌ 用戶映射修復失敗")
        sys.exit(1)
    
    print("\n🎉 現在可以正確顯示用戶名稱了！")
