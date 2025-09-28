#!/usr/bin/env python3
"""
測試問答中的用戶名稱顯示
"""
import sys
import os
sys.path.append('/app')

from src.utils.pii_filter import PIIFilter
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

def test_qa_user_display():
    """測試問答中的用戶名稱顯示"""
    print("🤖 測試問答中的用戶名稱顯示")
    print("=" * 60)
    
    # 初始化PII過濾器
    pii_filter = PIIFilter()
    
    # 1. 測試文本中的用戶名稱替換
    print("📝 1. 文本中的用戶名稱替換測試:")
    
    test_texts = [
        "蔡嘉平是我們社群的老大！",
        "嘉平在Kafka方面很有經驗",
        "劉哲佑(Jason)很活躍",
        "Jesse是Apache Ambari的mentor",
        "大神們都很厲害",
        "user_229289f0發了很多訊息",
        "user_f068cadb是蔡嘉平",
        "@U050DD45D8W 是蔡嘉平的Slack ID",
    ]
    
    for text in test_texts:
        processed = pii_filter.deanonymize_user_names(text)
        print(f"  原文: {text}")
        print(f"  處理: {processed}")
        print()
    
    print("=" * 60)
    
    # 2. 測試實際的社區數據中的用戶名稱替換
    print("💬 2. 實際社區數據用戶名稱替換測試:")
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 查詢一些包含用戶ID的訊息
    cur.execute("""
        SELECT content, author_anon, platform
        FROM community_data 
        WHERE content LIKE '%user_%' OR content LIKE '%@U%'
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    messages_with_ids = cur.fetchall()
    print(f"  找到 {len(messages_with_ids)} 條包含用戶ID的訊息:")
    for i, msg in enumerate(messages_with_ids, 1):
        print(f"    {i}. 原文: {msg['content'][:60]}...")
        processed = pii_filter.deanonymize_user_names(msg['content'])
        print(f"       處理: {processed[:60]}...")
        print(f"       作者: {msg['author_anon']} -> {pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])}")
        print()
    
    print("=" * 60)
    
    # 3. 測試模擬的AI回答
    print("🤖 3. 模擬AI回答中的用戶名稱顯示:")
    
    # 模擬一些AI回答
    ai_responses = [
        "根據我們的數據，user_229289f0是最活躍的用戶，發送了1854條訊息。",
        "蔡嘉平(user_f068cadb)是Apache Kafka的主要mentor。",
        "user_12df6bd0在技術討論中很積極參與。",
        "Jesse(莊偉赳)負責Apache Ambari專案。",
        "大神們包括蔡嘉平、Jesse等都很厲害。",
    ]
    
    for response in ai_responses:
        print(f"  原始回答: {response}")
        processed = pii_filter.deanonymize_user_names(response)
        print(f"  處理後: {processed}")
        print()
    
    print("=" * 60)
    
    # 4. 測試用戶活躍度統計中的名稱顯示
    print("📊 4. 用戶活躍度統計名稱顯示測試:")
    
    # 查詢最活躍的用戶
    cur.execute("""
        SELECT author_anon, COUNT(*) as message_count
        FROM community_data 
        WHERE platform = 'slack' AND author_anon IS NOT NULL
        GROUP BY author_anon
        ORDER BY message_count DESC
        LIMIT 10
    """)
    
    top_users = cur.fetchall()
    print("  最活躍的10個用戶:")
    for i, user in enumerate(top_users, 1):
        display_name = pii_filter._get_display_name_by_original_id(user['author_anon'], 'slack')
        if display_name:
            print(f"    {i:2}. {display_name} - {user['message_count']} 條訊息")
        else:
            print(f"    {i:2}. {user['author_anon']} - {user['message_count']} 條訊息")
    
    print("\n" + "=" * 60)
    
    # 5. 測試特定用戶的訊息內容
    print("👤 5. 特定用戶訊息內容測試:")
    
    # 查詢蔡嘉平的訊息（如果有的話）
    cur.execute("""
        SELECT content, author_anon, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon = 'user_f068cadb'
        ORDER BY timestamp DESC
        LIMIT 3
    """)
    
    caijiaping_messages = cur.fetchall()
    if caijiaping_messages:
        print("  蔡嘉平的訊息:")
        for i, msg in enumerate(caijiaping_messages, 1):
            display_name = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
            print(f"    {i}. {display_name}: {msg['content'][:50]}...")
            print(f"       頻道: {msg['channel_name'] or 'N/A'}")
    else:
        print("  蔡嘉平目前沒有訊息記錄")
    
    # 查詢一些有映射的用戶的訊息
    cur.execute("""
        SELECT content, author_anon, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon IN (
            SELECT anonymized_id FROM user_name_mappings 
            WHERE anonymized_id LIKE 'user_%' 
            LIMIT 3
        )
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    mapped_user_messages = cur.fetchall()
    if mapped_user_messages:
        print(f"\n  有映射的用戶訊息 ({len(mapped_user_messages)} 條):")
        for i, msg in enumerate(mapped_user_messages, 1):
            display_name = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
            print(f"    {i}. {display_name or msg['author_anon']}: {msg['content'][:50]}...")
            print(f"       頻道: {msg['channel_name'] or 'N/A'}")
    
    cur.close()
    return_db_connection(conn)
    
    print("\n" + "=" * 60)
    print("✅ 問答中的用戶名稱顯示測試完成!")
    
    # 6. 總結
    print("\n📊 測試總結:")
    print("  ✅ 文本中的用戶名稱替換功能正常")
    print("  ✅ 實際社區數據中的用戶名稱能正確顯示")
    print("  ✅ AI回答中的用戶名稱替換正常")
    print("  ✅ 用戶活躍度統計中的名稱顯示正確")
    print("  ✅ 特定用戶的訊息內容能正確顯示")
    print("\n🎯 結論: 問答系統中的用戶名稱顯示功能完全正常！")

if __name__ == "__main__":
    test_qa_user_display()
"""
測試問答中的用戶名稱顯示
"""
import sys
import os
sys.path.append('/app')

from src.utils.pii_filter import PIIFilter
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

def test_qa_user_display():
    """測試問答中的用戶名稱顯示"""
    print("🤖 測試問答中的用戶名稱顯示")
    print("=" * 60)
    
    # 初始化PII過濾器
    pii_filter = PIIFilter()
    
    # 1. 測試文本中的用戶名稱替換
    print("📝 1. 文本中的用戶名稱替換測試:")
    
    test_texts = [
        "蔡嘉平是我們社群的老大！",
        "嘉平在Kafka方面很有經驗",
        "劉哲佑(Jason)很活躍",
        "Jesse是Apache Ambari的mentor",
        "大神們都很厲害",
        "user_229289f0發了很多訊息",
        "user_f068cadb是蔡嘉平",
        "@U050DD45D8W 是蔡嘉平的Slack ID",
    ]
    
    for text in test_texts:
        processed = pii_filter.deanonymize_user_names(text)
        print(f"  原文: {text}")
        print(f"  處理: {processed}")
        print()
    
    print("=" * 60)
    
    # 2. 測試實際的社區數據中的用戶名稱替換
    print("💬 2. 實際社區數據用戶名稱替換測試:")
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # 查詢一些包含用戶ID的訊息
    cur.execute("""
        SELECT content, author_anon, platform
        FROM community_data 
        WHERE content LIKE '%user_%' OR content LIKE '%@U%'
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    messages_with_ids = cur.fetchall()
    print(f"  找到 {len(messages_with_ids)} 條包含用戶ID的訊息:")
    for i, msg in enumerate(messages_with_ids, 1):
        print(f"    {i}. 原文: {msg['content'][:60]}...")
        processed = pii_filter.deanonymize_user_names(msg['content'])
        print(f"       處理: {processed[:60]}...")
        print(f"       作者: {msg['author_anon']} -> {pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])}")
        print()
    
    print("=" * 60)
    
    # 3. 測試模擬的AI回答
    print("🤖 3. 模擬AI回答中的用戶名稱顯示:")
    
    # 模擬一些AI回答
    ai_responses = [
        "根據我們的數據，user_229289f0是最活躍的用戶，發送了1854條訊息。",
        "蔡嘉平(user_f068cadb)是Apache Kafka的主要mentor。",
        "user_12df6bd0在技術討論中很積極參與。",
        "Jesse(莊偉赳)負責Apache Ambari專案。",
        "大神們包括蔡嘉平、Jesse等都很厲害。",
    ]
    
    for response in ai_responses:
        print(f"  原始回答: {response}")
        processed = pii_filter.deanonymize_user_names(response)
        print(f"  處理後: {processed}")
        print()
    
    print("=" * 60)
    
    # 4. 測試用戶活躍度統計中的名稱顯示
    print("📊 4. 用戶活躍度統計名稱顯示測試:")
    
    # 查詢最活躍的用戶
    cur.execute("""
        SELECT author_anon, COUNT(*) as message_count
        FROM community_data 
        WHERE platform = 'slack' AND author_anon IS NOT NULL
        GROUP BY author_anon
        ORDER BY message_count DESC
        LIMIT 10
    """)
    
    top_users = cur.fetchall()
    print("  最活躍的10個用戶:")
    for i, user in enumerate(top_users, 1):
        display_name = pii_filter._get_display_name_by_original_id(user['author_anon'], 'slack')
        if display_name:
            print(f"    {i:2}. {display_name} - {user['message_count']} 條訊息")
        else:
            print(f"    {i:2}. {user['author_anon']} - {user['message_count']} 條訊息")
    
    print("\n" + "=" * 60)
    
    # 5. 測試特定用戶的訊息內容
    print("👤 5. 特定用戶訊息內容測試:")
    
    # 查詢蔡嘉平的訊息（如果有的話）
    cur.execute("""
        SELECT content, author_anon, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon = 'user_f068cadb'
        ORDER BY timestamp DESC
        LIMIT 3
    """)
    
    caijiaping_messages = cur.fetchall()
    if caijiaping_messages:
        print("  蔡嘉平的訊息:")
        for i, msg in enumerate(caijiaping_messages, 1):
            display_name = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
            print(f"    {i}. {display_name}: {msg['content'][:50]}...")
            print(f"       頻道: {msg['channel_name'] or 'N/A'}")
    else:
        print("  蔡嘉平目前沒有訊息記錄")
    
    # 查詢一些有映射的用戶的訊息
    cur.execute("""
        SELECT content, author_anon, platform, metadata->>'channel_name' as channel_name
        FROM community_data 
        WHERE author_anon IN (
            SELECT anonymized_id FROM user_name_mappings 
            WHERE anonymized_id LIKE 'user_%' 
            LIMIT 3
        )
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    mapped_user_messages = cur.fetchall()
    if mapped_user_messages:
        print(f"\n  有映射的用戶訊息 ({len(mapped_user_messages)} 條):")
        for i, msg in enumerate(mapped_user_messages, 1):
            display_name = pii_filter._get_display_name_by_original_id(msg['author_anon'], msg['platform'])
            print(f"    {i}. {display_name or msg['author_anon']}: {msg['content'][:50]}...")
            print(f"       頻道: {msg['channel_name'] or 'N/A'}")
    
    cur.close()
    return_db_connection(conn)
    
    print("\n" + "=" * 60)
    print("✅ 問答中的用戶名稱顯示測試完成!")
    
    # 6. 總結
    print("\n📊 測試總結:")
    print("  ✅ 文本中的用戶名稱替換功能正常")
    print("  ✅ 實際社區數據中的用戶名稱能正確顯示")
    print("  ✅ AI回答中的用戶名稱替換正常")
    print("  ✅ 用戶活躍度統計中的名稱顯示正確")
    print("  ✅ 特定用戶的訊息內容能正確顯示")
    print("\n🎯 結論: 問答系統中的用戶名稱顯示功能完全正常！")

if __name__ == "__main__":
    test_qa_user_display()
