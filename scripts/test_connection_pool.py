#!/usr/bin/env python3
"""
測試連接池修復
"""
import sys
import os
sys.path.append('/app')

from src.utils.pii_filter import PIIFilter
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
import time
from concurrent.futures import ThreadPoolExecutor

def test_connection_pool():
    """測試連接池修復"""
    print("🔧 測試連接池修復")
    print("=" * 50)
    
    # 初始化PII過濾器
    pii_filter = PIIFilter()
    
    def simulate_db_query(query_id):
        """模擬數據庫查詢"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT anonymized_id, display_name, real_name
                FROM user_name_mappings 
                WHERE anonymized_id LIKE 'user_%'
                LIMIT 1
            """)
            
            result = cur.fetchone()
            if result:
                display_name = pii_filter._get_display_name_by_original_id(result['anonymized_id'], 'slack')
            
            cur.close()
            return_db_connection(conn)
            
            return {"query_id": query_id, "success": True}
        except Exception as e:
            return {"query_id": query_id, "success": False, "error": str(e)}
    
    # 測試50個並發查詢
    print("  測試50個並發查詢...")
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(simulate_db_query, i) for i in range(50)]
        results = [future.result() for future in futures]
    end_time = time.time()
    
    success_count = sum(1 for result in results if result["success"])
    error_count = len(results) - success_count
    
    print(f"  50個並發查詢完成: {(end_time - start_time)*1000:.2f}ms")
    print(f"  成功查詢: {success_count}")
    print(f"  失敗查詢: {error_count}")
    print(f"  成功率: {success_count/len(results)*100:.1f}%")
    
    if success_count == 50:
        print("  ✅ 連接池修復成功！")
    else:
        print("  ❌ 連接池仍有問題")
        for result in results:
            if not result["success"]:
                print(f"    查詢 {result['query_id']} 失敗: {result['error']}")
    
    print("\n" + "=" * 50)
    print("🎉 連接池測試完成！")

if __name__ == "__main__":
    test_connection_pool()
"""
測試連接池修復
"""
import sys
import os
sys.path.append('/app')

from src.utils.pii_filter import PIIFilter
from src.storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor
import time
from concurrent.futures import ThreadPoolExecutor

def test_connection_pool():
    """測試連接池修復"""
    print("🔧 測試連接池修復")
    print("=" * 50)
    
    # 初始化PII過濾器
    pii_filter = PIIFilter()
    
    def simulate_db_query(query_id):
        """模擬數據庫查詢"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT anonymized_id, display_name, real_name
                FROM user_name_mappings 
                WHERE anonymized_id LIKE 'user_%'
                LIMIT 1
            """)
            
            result = cur.fetchone()
            if result:
                display_name = pii_filter._get_display_name_by_original_id(result['anonymized_id'], 'slack')
            
            cur.close()
            return_db_connection(conn)
            
            return {"query_id": query_id, "success": True}
        except Exception as e:
            return {"query_id": query_id, "success": False, "error": str(e)}
    
    # 測試50個並發查詢
    print("  測試50個並發查詢...")
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(simulate_db_query, i) for i in range(50)]
        results = [future.result() for future in futures]
    end_time = time.time()
    
    success_count = sum(1 for result in results if result["success"])
    error_count = len(results) - success_count
    
    print(f"  50個並發查詢完成: {(end_time - start_time)*1000:.2f}ms")
    print(f"  成功查詢: {success_count}")
    print(f"  失敗查詢: {error_count}")
    print(f"  成功率: {success_count/len(results)*100:.1f}%")
    
    if success_count == 50:
        print("  ✅ 連接池修復成功！")
    else:
        print("  ❌ 連接池仍有問題")
        for result in results:
            if not result["success"]:
                print(f"    查詢 {result['query_id']} 失敗: {result['error']}")
    
    print("\n" + "=" * 50)
    print("🎉 連接池測試完成！")

if __name__ == "__main__":
    test_connection_pool()
