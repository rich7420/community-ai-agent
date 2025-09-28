#!/usr/bin/env python3
"""
測試用戶名稱顯示功能
"""
import sys
import os
sys.path.append('/app')

from src.utils.pii_filter import PIIFilter
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

def test_user_display():
    """測試用戶名稱顯示功能"""
    print("🔍 測試用戶名稱顯示功能")
    print("=" * 50)
    
    # 初始化PII過濾器
    pii_filter = PIIFilter()
    
    # 測試用戶名稱解析
    test_names = [
        "蔡嘉平",
        "嘉平", 
        "劉哲佑(Jason)",
        "Jason",
        "Jesse",
        "莊偉赳",
        "偉赳"
    ]
    
    print("📝 用戶名稱解析測試:")
    for name in test_names:
        resolved = pii_filter.resolve_user_references(name)
        print(f"  {name} -> {resolved}")
    
    print("\n" + "=" * 50)
    
    # 測試數據庫中的用戶映射
    print("🗄️ 數據庫用戶映射測試:")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 查詢一些用戶映射
    cur.execute("""
        SELECT display_name, real_name, aliases, group_terms, anonymized_id
        FROM user_name_mappings 
        WHERE display_name IS NOT NULL
        ORDER BY display_name
        LIMIT 10
    """)
    
    users = cur.fetchall()
    print(f"找到 {len(users)} 個用戶映射:")
    for user in users:
        print(f"  {user['display_name']} ({user['real_name']}) - ID: {user['anonymized_id']}")
        if user['aliases']:
            print(f"    別名: {', '.join(user['aliases'])}")
        if user['group_terms']:
            print(f"    群組稱呼: {', '.join(user['group_terms'])}")
    
    cur.close()
    return_db_connection(conn)
    
    print("\n" + "=" * 50)
    
    # 測試社區數據中的用戶顯示
    print("💬 社區數據用戶顯示測試:")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 查詢一些社區數據
    cur.execute("""
        SELECT author_anon, content, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    messages = cur.fetchall()
    print(f"找到 {len(messages)} 條最近訊息:")
    for msg in messages:
        # 嘗試解析用戶名稱
        user_display = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
        print(f"  {user_display}: {msg['content'][:50]}...")
        print(f"    平台: {msg['platform']}, 頻道: {msg['channel_name']}")
    
    cur.close()
    return_db_connection(conn)
    
    print("\n✅ 用戶名稱顯示功能測試完成!")

if __name__ == "__main__":
    test_user_display()

測試用戶名稱顯示功能
"""
import sys
import os
sys.path.append('/app')

from src.utils.pii_filter import PIIFilter
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

def test_user_display():
    """測試用戶名稱顯示功能"""
    print("🔍 測試用戶名稱顯示功能")
    print("=" * 50)
    
    # 初始化PII過濾器
    pii_filter = PIIFilter()
    
    # 測試用戶名稱解析
    test_names = [
        "蔡嘉平",
        "嘉平", 
        "劉哲佑(Jason)",
        "Jason",
        "Jesse",
        "莊偉赳",
        "偉赳"
    ]
    
    print("📝 用戶名稱解析測試:")
    for name in test_names:
        resolved = pii_filter.resolve_user_references(name)
        print(f"  {name} -> {resolved}")
    
    print("\n" + "=" * 50)
    
    # 測試數據庫中的用戶映射
    print("🗄️ 數據庫用戶映射測試:")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 查詢一些用戶映射
    cur.execute("""
        SELECT display_name, real_name, aliases, group_terms, anonymized_id
        FROM user_name_mappings 
        WHERE display_name IS NOT NULL
        ORDER BY display_name
        LIMIT 10
    """)
    
    users = cur.fetchall()
    print(f"找到 {len(users)} 個用戶映射:")
    for user in users:
        print(f"  {user['display_name']} ({user['real_name']}) - ID: {user['anonymized_id']}")
        if user['aliases']:
            print(f"    別名: {', '.join(user['aliases'])}")
        if user['group_terms']:
            print(f"    群組稱呼: {', '.join(user['group_terms'])}")
    
    cur.close()
    return_db_connection(conn)
    
    print("\n" + "=" * 50)
    
    # 測試社區數據中的用戶顯示
    print("💬 社區數據用戶顯示測試:")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 查詢一些社區數據
    cur.execute("""
        SELECT author_anon, content, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    messages = cur.fetchall()
    print(f"找到 {len(messages)} 條最近訊息:")
    for msg in messages:
        # 嘗試解析用戶名稱
        user_display = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
        print(f"  {user_display}: {msg['content'][:50]}...")
        print(f"    平台: {msg['platform']}, 頻道: {msg['channel_name']}")
    
    cur.close()
    return_db_connection(conn)
    
    print("\n✅ 用戶名稱顯示功能測試完成!")

if __name__ == "__main__":
    test_user_display()
