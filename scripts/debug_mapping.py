#!/usr/bin/env python3
"""
調試用戶映射問題的腳本
"""

import os
import sys
import logging

# 添加src目錄到Python路徑
sys.path.append('/app')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        from storage.connection_pool import get_db_connection, return_db_connection
        
        logger.info("開始調試蔡嘉平的用戶映射問題...")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查詢蔡嘉平的正確映射
        cur.execute("""
            SELECT original_user_id, anonymized_id, display_name 
            FROM user_name_mappings 
            WHERE display_name = '蔡嘉平'
        """)
        result = cur.fetchone()
        
        if not result:
            logger.error("找不到蔡嘉平的用戶映射記錄")
            return
        
        logger.info(f"查詢結果: {result}")
        logger.info(f"結果字段數量: {len(result)}")
        
        original_user_id, correct_anonymized_id, display_name = result
        logger.info(f"蔡嘉平的正確映射: {original_user_id} -> {correct_anonymized_id}")
        
        # 查找所有提到"嘉平"的訊息記錄
        logger.info(f"準備查詢，correct_anonymized_id: {correct_anonymized_id}")
        cur.execute("""
            SELECT id, author_anon, content
            FROM community_data 
            WHERE content LIKE '%嘉平%' 
            AND author_anon != %s
            LIMIT 5
        """, (correct_anonymized_id,))
        
        records = cur.fetchall()
        logger.info(f"找到 {len(records)} 條提到'嘉平'的訊息記錄")
        
        for i, record in enumerate(records):
            logger.info(f"記錄 {i+1}: {record}")
            logger.info(f"記錄字段數量: {len(record)}")
        
        cur.close()
        return_db_connection(conn)
        
    except Exception as e:
        logger.error(f"調試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

調試用戶映射問題的腳本
"""

import os
import sys
import logging

# 添加src目錄到Python路徑
sys.path.append('/app')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        from storage.connection_pool import get_db_connection, return_db_connection
        
        logger.info("開始調試蔡嘉平的用戶映射問題...")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查詢蔡嘉平的正確映射
        cur.execute("""
            SELECT original_user_id, anonymized_id, display_name 
            FROM user_name_mappings 
            WHERE display_name = '蔡嘉平'
        """)
        result = cur.fetchone()
        
        if not result:
            logger.error("找不到蔡嘉平的用戶映射記錄")
            return
        
        logger.info(f"查詢結果: {result}")
        logger.info(f"結果字段數量: {len(result)}")
        
        original_user_id, correct_anonymized_id, display_name = result
        logger.info(f"蔡嘉平的正確映射: {original_user_id} -> {correct_anonymized_id}")
        
        # 查找所有提到"嘉平"的訊息記錄
        logger.info(f"準備查詢，correct_anonymized_id: {correct_anonymized_id}")
        cur.execute("""
            SELECT id, author_anon, content
            FROM community_data 
            WHERE content LIKE '%嘉平%' 
            AND author_anon != %s
            LIMIT 5
        """, (correct_anonymized_id,))
        
        records = cur.fetchall()
        logger.info(f"找到 {len(records)} 條提到'嘉平'的訊息記錄")
        
        for i, record in enumerate(records):
            logger.info(f"記錄 {i+1}: {record}")
            logger.info(f"記錄字段數量: {len(record)}")
        
        cur.close()
        return_db_connection(conn)
        
    except Exception as e:
        logger.error(f"調試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
