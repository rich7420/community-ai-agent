#!/usr/bin/env python3
"""
資料庫初始化腳本
創建資料庫表、索引和初始數據
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def get_db_connection():
    """獲取資料庫連接"""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', '5432'),
        database=os.getenv('POSTGRES_DB', 'community_ai'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'password')
    )

def create_database():
    """創建資料庫（如果不存在）"""
    try:
        # 連接到預設資料庫
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            database='postgres',
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'password')
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        db_name = os.getenv('POSTGRES_DB', 'community_ai')
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {db_name}")
            print(f"✅ 資料庫 {db_name} 創建成功")
        else:
            print(f"ℹ️  資料庫 {db_name} 已存在")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 創建資料庫失敗: {e}")
        return False

def run_init_sql():
    """執行初始化SQL腳本"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 讀取並執行 init.sql
        init_sql_path = os.path.join(os.path.dirname(__file__), '..', 'docker', 'postgres', 'init.sql')
        with open(init_sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # 分割並執行SQL語句
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for sql in sql_statements:
            if sql:
                cur.execute(sql)
        
        conn.commit()
        print("✅ 初始化SQL腳本執行成功")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 執行初始化SQL失敗: {e}")
        return False

def verify_tables():
    """驗證表是否創建成功"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 檢查主要表是否存在
        tables_to_check = [
            'community_data',
            'opt_out_users', 
            'weekly_reports',
            'collection_logs'
        ]
        
        for table in tables_to_check:
            cur.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            exists = cur.fetchone()[0]
            if exists:
                print(f"✅ 表 {table} 存在")
            else:
                print(f"❌ 表 {table} 不存在")
                return False
        
        # pgvector擴展檢查已移除，現在使用TEXT存儲embedding
        print("ℹ️ 使用TEXT存儲embedding，無需pgvector擴展")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 驗證表失敗: {e}")
        return False

def create_migration_system():
    """創建資料庫migration系統"""
    print("\n🔄 設置資料庫migration系統...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 創建migration表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                description TEXT
            )
        """)
        
        # 插入當前版本
        current_version = "2025-09-25-001"
        cur.execute("""
            INSERT INTO schema_migrations (version, description) 
            VALUES (%s, %s) 
            ON CONFLICT (version) DO NOTHING
        """, (current_version, "Initial schema with community_data, opt_out_users, weekly_reports, collection_logs tables"))
        
        conn.commit()
        print(f"✅ Migration系統設置完成，當前版本: {current_version}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration系統設置失敗: {e}")
        return False

def main():
    """主函數"""
    print("🚀 開始資料庫初始化...")
    
    # 1. 創建資料庫
    if not create_database():
        return 1
    
    # 2. 執行初始化SQL
    if not run_init_sql():
        return 1
    
    # 3. 設置migration系統
    if not create_migration_system():
        return 1
    
    # 4. 驗證表
    if not verify_tables():
        return 1
    
    print("🎉 資料庫初始化完成！")
    return 0

if __name__ == "__main__":
    sys.exit(main())