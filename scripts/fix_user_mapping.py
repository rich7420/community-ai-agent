#!/usr/bin/env python3
"""
修復用戶映射問題的腳本
"""

import os
import sys
import logging
from datetime import datetime

# 添加src目錄到Python路徑
sys.path.append('/app')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        from storage.connection_pool import get_db_connection, return_db_connection
        
        logger.info("開始修復蔡嘉平的用戶映射問題...")
        
        # 獲取蔡嘉平的正確映射信息
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
        
        original_user_id, correct_anonymized_id, display_name = result
        logger.info(f"蔡嘉平的正確映射: {original_user_id} -> {correct_anonymized_id}")
        
        # 查找所有提到"嘉平"的訊息記錄
        cur.execute("""
            SELECT id, author_anon, content
            FROM community_data 
            WHERE content LIKE '%嘉平%' 
            AND author_anon != %s
        """, (correct_anonymized_id,))
        
        records = cur.fetchall()
        logger.info(f"找到 {len(records)} 條提到'嘉平'的訊息記錄")
        
        if records:
            logger.info(f"第一條記錄的結構: {records[0]}")
            logger.info(f"記錄字段數量: {len(records[0])}")
        
        # 更新這些記錄的author_anon為正確的ID
        updated_count = 0
        for record in records:
            logger.info(f"處理記錄: {record}")
            record_id, old_anonymized_id, content = record
            try:
                # 更新author_anon
                cur.execute("""
                    UPDATE community_data 
                    SET author_anon = %s, updated_at = NOW()
                    WHERE id = %s
                """, (correct_anonymized_id, record_id))
                
                updated_count += 1
                logger.info(f"更新記錄 {record_id}: {old_anonymized_id} -> {correct_anonymized_id}")
                
            except Exception as e:
                logger.error(f"更新記錄 {record_id} 失敗: {e}")
        
        # 提交更改
        conn.commit()
        logger.info(f"成功更新 {updated_count} 條記錄")
        
        # 驗證更新結果
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM community_data 
            WHERE author_anon = %s
        """, (correct_anonymized_id,))
        
        result = cur.fetchone()
        total_messages = result[0] if result else 0
        logger.info(f"蔡嘉平現在總共有 {total_messages} 條訊息")
        
        cur.close()
        return_db_connection(conn)
        
        logger.info("用戶映射修復完成！")
        
    except Exception as e:
        logger.error(f"修復用戶映射失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

修復用戶映射問題的腳本
"""

import os
import sys
import logging
from datetime import datetime

# 添加src目錄到Python路徑
sys.path.append('/app')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        from storage.connection_pool import get_db_connection, return_db_connection
        
        logger.info("開始修復蔡嘉平的用戶映射問題...")
        
        # 獲取蔡嘉平的正確映射信息
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
        
        original_user_id, correct_anonymized_id, display_name = result
        logger.info(f"蔡嘉平的正確映射: {original_user_id} -> {correct_anonymized_id}")
        
        # 查找所有提到"嘉平"的訊息記錄
        cur.execute("""
            SELECT id, author_anon, content
            FROM community_data 
            WHERE content LIKE '%嘉平%' 
            AND author_anon != %s
        """, (correct_anonymized_id,))
        
        records = cur.fetchall()
        logger.info(f"找到 {len(records)} 條提到'嘉平'的訊息記錄")
        
        if records:
            logger.info(f"第一條記錄的結構: {records[0]}")
            logger.info(f"記錄字段數量: {len(records[0])}")
        
        # 更新這些記錄的author_anon為正確的ID
        updated_count = 0
        for record in records:
            logger.info(f"處理記錄: {record}")
            record_id, old_anonymized_id, content = record
            try:
                # 更新author_anon
                cur.execute("""
                    UPDATE community_data 
                    SET author_anon = %s, updated_at = NOW()
                    WHERE id = %s
                """, (correct_anonymized_id, record_id))
                
                updated_count += 1
                logger.info(f"更新記錄 {record_id}: {old_anonymized_id} -> {correct_anonymized_id}")
                
            except Exception as e:
                logger.error(f"更新記錄 {record_id} 失敗: {e}")
        
        # 提交更改
        conn.commit()
        logger.info(f"成功更新 {updated_count} 條記錄")
        
        # 驗證更新結果
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM community_data 
            WHERE author_anon = %s
        """, (correct_anonymized_id,))
        
        result = cur.fetchone()
        total_messages = result[0] if result else 0
        logger.info(f"蔡嘉平現在總共有 {total_messages} 條訊息")
        
        cur.close()
        return_db_connection(conn)
        
        logger.info("用戶映射修復完成！")
        
    except Exception as e:
        logger.error(f"修復用戶映射失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
