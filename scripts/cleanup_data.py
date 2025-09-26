#!/usr/bin/env python3
"""
資料清理腳本
定期清理過期資料和優化資料庫
"""
import os
import sys
import psycopg2
from datetime import datetime, timedelta
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

def cleanup_old_data():
    """清理過期資料"""
    print("🧹 開始清理過期資料...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 清理超過90天的資料
        cutoff_date = datetime.now() - timedelta(days=90)
        
        # 清理community_data表中的過期資料
        cur.execute("""
            DELETE FROM community_data 
            WHERE created_at < %s
        """, (cutoff_date,))
        
        deleted_count = cur.rowcount
        print(f"✅ 清理了 {deleted_count} 條過期資料")
        
        # 清理collection_logs表中的過期日誌
        cur.execute("""
            DELETE FROM collection_logs 
            WHERE created_at < %s
        """, (cutoff_date,))
        
        deleted_logs = cur.rowcount
        print(f"✅ 清理了 {deleted_logs} 條過期日誌")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 清理過期資料失敗: {e}")
        return False

def optimize_database():
    """優化資料庫"""
    print("\n⚡ 開始優化資料庫...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 更新表統計信息
        cur.execute("ANALYZE community_data")
        cur.execute("ANALYZE opt_out_users")
        cur.execute("ANALYZE weekly_reports")
        cur.execute("ANALYZE collection_logs")
        
        print("✅ 更新表統計信息完成")
        
        # 重建索引（如果需要）
        cur.execute("REINDEX TABLE community_data")
        cur.execute("REINDEX TABLE weekly_reports")
        
        print("✅ 重建索引完成")
        
        # 清理未使用的空間
        cur.execute("VACUUM ANALYZE")
        
        print("✅ 清理未使用空間完成")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ 資料庫優化失敗: {e}")
        return False

def cleanup_minio_data():
    """清理MinIO中的過期資料"""
    print("\n🗂️  開始清理MinIO過期資料...")
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # 創建S3客戶端
        s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://localhost:9000'),
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'admin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'admin123'),
            region_name='us-east-1'
        )
        
        bucket_name = os.getenv('MINIO_BUCKET', 'community-data-lake')
        cutoff_date = datetime.now() - timedelta(days=90)
        
        # 列出所有對象
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        
        deleted_count = 0
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    # 檢查對象的修改時間
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        try:
                            s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
                            deleted_count += 1
                        except ClientError as e:
                            print(f"⚠️  刪除對象失敗 {obj['Key']}: {e}")
        
        print(f"✅ 清理了 {deleted_count} 個過期MinIO對象")
        return True
        
    except ImportError:
        print("⚠️  boto3未安裝，跳過MinIO清理")
        return True
    except Exception as e:
        print(f"❌ MinIO清理失敗: {e}")
        return False

def main():
    """主函數"""
    print("🚀 開始資料清理和優化...\n")
    
    # 1. 清理過期資料
    if not cleanup_old_data():
        return 1
    
    # 2. 優化資料庫
    if not optimize_database():
        return 1
    
    # 3. 清理MinIO資料
    if not cleanup_minio_data():
        return 1
    
    print("\n🎉 資料清理和優化完成！")
    return 0

if __name__ == "__main__":
    sys.exit(main())
