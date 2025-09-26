"""
資料庫連接池管理
提供PostgreSQL和MinIO S3的連接池管理
"""
import os
import psycopg2
from psycopg2 import pool
import boto3
from botocore.config import Config
from dotenv import load_dotenv
import threading
from typing import Optional

# 載入環境變數
load_dotenv()

class DatabaseConnectionPool:
    """PostgreSQL連接池管理"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.pool = None
            self.initialized = True
    
    def get_pool(self):
        """獲取連接池"""
        if self.pool is None:
            try:
                self.pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=20,
                    host=os.getenv('POSTGRES_HOST', 'localhost'),
                    port=os.getenv('POSTGRES_PORT', '5432'),
                    database=os.getenv('POSTGRES_DB', 'community_ai'),
                    user=os.getenv('POSTGRES_USER', 'postgres'),
                    password=os.getenv('POSTGRES_PASSWORD', 'password')
                )
                print("✅ PostgreSQL連接池創建成功")
            except Exception as e:
                print(f"❌ PostgreSQL連接池創建失敗: {e}")
                raise
        return self.pool
    
    def get_connection(self):
        """獲取連接"""
        pool = self.get_pool()
        return pool.getconn()
    
    def return_connection(self, conn):
        """歸還連接"""
        pool = self.get_pool()
        pool.putconn(conn)
    
    def close_all(self):
        """關閉所有連接"""
        if self.pool:
            self.pool.closeall()
            print("✅ PostgreSQL連接池已關閉")

class S3ConnectionPool:
    """MinIO S3連接池管理"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.client = None
            self.initialized = True
    
    def get_client(self):
        """獲取S3客戶端"""
        if self.client is None:
            try:
                config = Config(
                    max_pool_connections=50,
                    retries={'max_attempts': 3}
                )
                
                self.client = boto3.client(
                    's3',
                    endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://localhost:9000'),
                    aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'admin'),
                    aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'admin123'),
                    region_name='us-east-1',
                    config=config
                )
                print("✅ MinIO S3連接池創建成功")
            except Exception as e:
                print(f"❌ MinIO S3連接池創建失敗: {e}")
                raise
        return self.client

# 全局連接池實例
db_pool = DatabaseConnectionPool()
s3_pool = S3ConnectionPool()

def get_db_connection():
    """獲取資料庫連接"""
    return db_pool.get_connection()

def return_db_connection(conn):
    """歸還資料庫連接"""
    db_pool.return_connection(conn)

def get_s3_client():
    """獲取S3客戶端"""
    return s3_pool.get_client()

def close_all_connections():
    """關閉所有連接"""
    db_pool.close_all()
    print("✅ 所有連接池已關閉")
