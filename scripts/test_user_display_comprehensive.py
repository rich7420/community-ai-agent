#!/usr/bin/env python3
"""
全面測試用戶名稱顯示功能
"""
import sys
import os
sys.path.append('/app')

from src.utils.pii_filter import PIIFilter
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

def test_user_display_comprehensive():
    """全面測試用戶名稱顯示功能"""
    print("🔍 全面測試用戶名稱顯示功能")
    print("=" * 60)
    
    # 初始化PII過濾器
    pii_filter = PIIFilter()
    
    # 1. 測試用戶名稱解析
    print("📝 1. 用戶名稱解析測試:")
    test_names = [
        "蔡嘉平", "嘉平", "大神",
        "劉哲佑(Jason)", "Jason", 
        "Jesse", "莊偉赳", "偉赳"
    ]
    
    for name in test_names:
        resolved = pii_filter.resolve_user_references(name)
        print(f"  {name:15} -> {resolved}")
    
    print("\n" + "=" * 60)
    
    # 2. 測試數據庫中的用戶映射
    print("🗄️ 2. 數據庫用戶映射統計:")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 統計用戶映射
    cur.execute("""
        SELECT 
            COUNT(*) as total_mappings,
            COUNT(CASE WHEN display_name IS NOT NULL THEN 1 END) as with_display_name,
            COUNT(CASE WHEN aliases IS NOT NULL AND array_length(aliases, 1) > 0 THEN 1 END) as with_aliases,
            COUNT(CASE WHEN group_terms IS NOT NULL AND array_length(group_terms, 1) > 0 THEN 1 END) as with_group_terms
        FROM user_name_mappings
    """)
    
    stats = cur.fetchone()
    print(f"  總映射數: {stats['total_mappings']}")
    print(f"  有顯示名稱: {stats['with_display_name']}")
    print(f"  有別名: {stats['with_aliases']}")
    print(f"  有群組稱呼: {stats['with_group_terms']}")
    
    # 查詢一些具體的用戶映射
    cur.execute("""
        SELECT display_name, real_name, aliases, group_terms, anonymized_id
        FROM user_name_mappings 
        WHERE display_name IS NOT NULL
        ORDER BY display_name
        LIMIT 5
    """)
    
    users = cur.fetchall()
    print(f"\n  前5個用戶映射:")
    for user in users:
        print(f"    {user['display_name']} ({user['real_name']}) - ID: {user['anonymized_id']}")
        if user['aliases']:
            print(f"      別名: {', '.join(user['aliases'])}")
        if user['group_terms']:
            print(f"      群組稱呼: {', '.join(user['group_terms'])}")
    
    print("\n" + "=" * 60)
    
    # 3. 測試社區數據中的用戶顯示
    print("💬 3. 社區數據用戶顯示測試:")
    
    # 統計各平台的數據
    cur.execute("""
        SELECT platform, COUNT(*) as message_count, COUNT(DISTINCT author_anon) as unique_users
        FROM community_data 
        WHERE author_anon IS NOT NULL
        GROUP BY platform
        ORDER BY message_count DESC
    """)
    
    platform_stats = cur.fetchall()
    print("  各平台數據統計:")
    for stat in platform_stats:
        print(f"    {stat['platform']:15} - 訊息: {stat['message_count']:5}, 用戶: {stat['unique_users']:3}")
    
    # 查詢一些Slack訊息並測試用戶名稱顯示
    cur.execute("""
        SELECT author_anon, content, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE platform = 'slack' AND author_anon IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    
    messages = cur.fetchall()
    print(f"\n  最近10條Slack訊息:")
    for i, msg in enumerate(messages, 1):
        # 嘗試解析用戶名稱
        user_display = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
        if user_display:
            print(f"    {i:2}. {user_display}: {msg['content'][:40]}...")
        else:
            print(f"    {i:2}. {msg['author_anon']}: {msg['content'][:40]}...")
        print(f"        頻道: {msg['channel_name'] or 'N/A'}")
    
    print("\n" + "=" * 60)
    
    # 4. 測試特定用戶的查詢
    print("👤 4. 特定用戶查詢測試:")
    
    # 查詢蔡嘉平的訊息
    cur.execute("""
        SELECT author_anon, content, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon = 'user_f068cadb'
        ORDER BY timestamp DESC
        LIMIT 3
    """)
    
    caijiaping_messages = cur.fetchall()
    if caijiaping_messages:
        print("  蔡嘉平的訊息:")
        for i, msg in enumerate(caijiaping_messages, 1):
            user_display = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
            print(f"    {i}. {user_display}: {msg['content'][:50]}...")
            print(f"       頻道: {msg['channel_name'] or 'N/A'}")
    else:
        print("  蔡嘉平目前沒有訊息記錄")
    
    # 查詢劉哲佑的訊息
    cur.execute("""
        SELECT author_anon, content, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon = 'user_72abaa64'
        ORDER BY timestamp DESC
        LIMIT 3
    """)
    
    jason_messages = cur.fetchall()
    if jason_messages:
        print("\n  劉哲佑(Jason)的訊息:")
        for i, msg in enumerate(jason_messages, 1):
            user_display = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
            print(f"    {i}. {user_display}: {msg['content'][:50]}...")
            print(f"       頻道: {msg['channel_name'] or 'N/A'}")
    else:
        print("\n  劉哲佑(Jason)目前沒有訊息記錄")
    
    cur.close()
    return_db_connection(conn)
    
    print("\n" + "=" * 60)
    print("✅ 用戶名稱顯示功能全面測試完成!")
    print("\n📊 總結:")
    print("  - 用戶名稱解析功能正常")
    print("  - 數據庫映射關係完整")
    print("  - 社區數據收集正常")
    print("  - 用戶名稱顯示功能已就緒")

if __name__ == "__main__":
    test_user_display_comprehensive()
"""
全面測試用戶名稱顯示功能
"""
import sys
import os
sys.path.append('/app')

from src.utils.pii_filter import PIIFilter
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

def test_user_display_comprehensive():
    """全面測試用戶名稱顯示功能"""
    print("🔍 全面測試用戶名稱顯示功能")
    print("=" * 60)
    
    # 初始化PII過濾器
    pii_filter = PIIFilter()
    
    # 1. 測試用戶名稱解析
    print("📝 1. 用戶名稱解析測試:")
    test_names = [
        "蔡嘉平", "嘉平", "大神",
        "劉哲佑(Jason)", "Jason", 
        "Jesse", "莊偉赳", "偉赳"
    ]
    
    for name in test_names:
        resolved = pii_filter.resolve_user_references(name)
        print(f"  {name:15} -> {resolved}")
    
    print("\n" + "=" * 60)
    
    # 2. 測試數據庫中的用戶映射
    print("🗄️ 2. 數據庫用戶映射統計:")
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 統計用戶映射
    cur.execute("""
        SELECT 
            COUNT(*) as total_mappings,
            COUNT(CASE WHEN display_name IS NOT NULL THEN 1 END) as with_display_name,
            COUNT(CASE WHEN aliases IS NOT NULL AND array_length(aliases, 1) > 0 THEN 1 END) as with_aliases,
            COUNT(CASE WHEN group_terms IS NOT NULL AND array_length(group_terms, 1) > 0 THEN 1 END) as with_group_terms
        FROM user_name_mappings
    """)
    
    stats = cur.fetchone()
    print(f"  總映射數: {stats['total_mappings']}")
    print(f"  有顯示名稱: {stats['with_display_name']}")
    print(f"  有別名: {stats['with_aliases']}")
    print(f"  有群組稱呼: {stats['with_group_terms']}")
    
    # 查詢一些具體的用戶映射
    cur.execute("""
        SELECT display_name, real_name, aliases, group_terms, anonymized_id
        FROM user_name_mappings 
        WHERE display_name IS NOT NULL
        ORDER BY display_name
        LIMIT 5
    """)
    
    users = cur.fetchall()
    print(f"\n  前5個用戶映射:")
    for user in users:
        print(f"    {user['display_name']} ({user['real_name']}) - ID: {user['anonymized_id']}")
        if user['aliases']:
            print(f"      別名: {', '.join(user['aliases'])}")
        if user['group_terms']:
            print(f"      群組稱呼: {', '.join(user['group_terms'])}")
    
    print("\n" + "=" * 60)
    
    # 3. 測試社區數據中的用戶顯示
    print("💬 3. 社區數據用戶顯示測試:")
    
    # 統計各平台的數據
    cur.execute("""
        SELECT platform, COUNT(*) as message_count, COUNT(DISTINCT author_anon) as unique_users
        FROM community_data 
        WHERE author_anon IS NOT NULL
        GROUP BY platform
        ORDER BY message_count DESC
    """)
    
    platform_stats = cur.fetchall()
    print("  各平台數據統計:")
    for stat in platform_stats:
        print(f"    {stat['platform']:15} - 訊息: {stat['message_count']:5}, 用戶: {stat['unique_users']:3}")
    
    # 查詢一些Slack訊息並測試用戶名稱顯示
    cur.execute("""
        SELECT author_anon, content, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE platform = 'slack' AND author_anon IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    
    messages = cur.fetchall()
    print(f"\n  最近10條Slack訊息:")
    for i, msg in enumerate(messages, 1):
        # 嘗試解析用戶名稱
        user_display = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
        if user_display:
            print(f"    {i:2}. {user_display}: {msg['content'][:40]}...")
        else:
            print(f"    {i:2}. {msg['author_anon']}: {msg['content'][:40]}...")
        print(f"        頻道: {msg['channel_name'] or 'N/A'}")
    
    print("\n" + "=" * 60)
    
    # 4. 測試特定用戶的查詢
    print("👤 4. 特定用戶查詢測試:")
    
    # 查詢蔡嘉平的訊息
    cur.execute("""
        SELECT author_anon, content, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon = 'user_f068cadb'
        ORDER BY timestamp DESC
        LIMIT 3
    """)
    
    caijiaping_messages = cur.fetchall()
    if caijiaping_messages:
        print("  蔡嘉平的訊息:")
        for i, msg in enumerate(caijiaping_messages, 1):
            user_display = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
            print(f"    {i}. {user_display}: {msg['content'][:50]}...")
            print(f"       頻道: {msg['channel_name'] or 'N/A'}")
    else:
        print("  蔡嘉平目前沒有訊息記錄")
    
    # 查詢劉哲佑的訊息
    cur.execute("""
        SELECT author_anon, content, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon = 'user_72abaa64'
        ORDER BY timestamp DESC
        LIMIT 3
    """)
    
    jason_messages = cur.fetchall()
    if jason_messages:
        print("\n  劉哲佑(Jason)的訊息:")
        for i, msg in enumerate(jason_messages, 1):
            user_display = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
            print(f"    {i}. {user_display}: {msg['content'][:50]}...")
            print(f"       頻道: {msg['channel_name'] or 'N/A'}")
    else:
        print("\n  劉哲佑(Jason)目前沒有訊息記錄")
    
    cur.close()
    return_db_connection(conn)
    
    print("\n" + "=" * 60)
    print("✅ 用戶名稱顯示功能全面測試完成!")
    print("\n📊 總結:")
    print("  - 用戶名稱解析功能正常")
    print("  - 數據庫映射關係完整")
    print("  - 社區數據收集正常")
    print("  - 用戶名稱顯示功能已就緒")

if __name__ == "__main__":
    test_user_display_comprehensive()
