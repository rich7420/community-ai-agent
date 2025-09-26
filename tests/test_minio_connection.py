#!/usr/bin/env python3
"""
MinIO連接測試腳本
測試S3-compatible API和Parquet文件上傳/下載
"""
import os
import sys
import json
import tempfile
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def test_minio_s3_connection():
    """測試MinIO S3-compatible API連接"""
    print("🔍 測試MinIO S3-compatible API連接...")
    
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
        
        # 測試連接
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"✅ Bucket '{bucket_name}' 存在")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                print(f"⚠️ Bucket '{bucket_name}' 不存在，嘗試創建...")
                s3_client.create_bucket(Bucket=bucket_name)
                print(f"✅ Bucket '{bucket_name}' 創建成功")
            else:
                raise
        
        # 測試上傳
        test_data = "Hello MinIO! This is a test file."
        test_key = f"test/connection_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_data.encode('utf-8'),
            ContentType='text/plain'
        )
        print(f"✅ 測試文件上傳成功: {test_key}")
        
        # 測試下載
        response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
        downloaded_data = response['Body'].read().decode('utf-8')
        
        if downloaded_data == test_data:
            print("✅ 測試文件下載成功，內容正確")
        else:
            print("❌ 下載的內容與上傳的不一致")
            return False
        
        # 清理測試文件
        s3_client.delete_object(Bucket=bucket_name, Key=test_key)
        print("✅ 測試文件清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ MinIO連接測試失敗: {e}")
        return False

def test_parquet_upload():
    """測試Parquet文件上傳"""
    print("🔍 測試Parquet文件上傳...")
    
    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
        import boto3
        from io import BytesIO
        
        # 創建測試數據
        test_data = {
            'id': [1, 2, 3],
            'platform': ['slack', 'github', 'slack'],
            'content': ['Test message 1', 'Test commit', 'Test message 2'],
            'author': ['user1', 'user2', 'user3'],
            'timestamp': [datetime.now()] * 3,
            'metadata': [{'test': True}] * 3
        }
        
        df = pd.DataFrame(test_data)
        
        # 轉換為Parquet
        table = pa.Table.from_pandas(df)
        buffer = BytesIO()
        pq.write_table(table, buffer)
        buffer.seek(0)
        
        # 上傳到MinIO
        s3_client = boto3.client(
            's3',
            endpoint_url=os.getenv('MINIO_ENDPOINT', 'http://localhost:9000'),
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'admin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'admin123'),
            region_name='us-east-1'
        )
        
        bucket_name = os.getenv('MINIO_BUCKET', 'community-data-lake')
        parquet_key = f"test/parquet_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        
        s3_client.upload_fileobj(
            buffer,
            bucket_name,
            parquet_key,
            ExtraArgs={'ContentType': 'application/octet-stream'}
        )
        
        print(f"✅ Parquet文件上傳成功: {parquet_key}")
        
        # 測試下載和讀取
        response = s3_client.get_object(Bucket=bucket_name, Key=parquet_key)
        downloaded_buffer = BytesIO(response['Body'].read())
        downloaded_table = pq.read_table(downloaded_buffer)
        downloaded_df = downloaded_table.to_pandas()
        
        if len(downloaded_df) == len(df):
            print("✅ Parquet文件下載和讀取成功")
        else:
            print("❌ Parquet文件讀取失敗")
            return False
        
        # 清理測試文件
        s3_client.delete_object(Bucket=bucket_name, Key=parquet_key)
        print("✅ Parquet測試文件清理完成")
        
        return True
        
    except Exception as e:
        print(f"❌ Parquet上傳測試失敗: {e}")
        return False

def test_minio_storage_class():
    """測試MinIOStorage類"""
    print("🔍 測試MinIOStorage類...")
    
    try:
        # 添加src目錄到Python路徑
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        
        from storage.minio_storage import MinIOStorage
        from collectors.data_merger import StandardizedRecord
        
        # 創建MinIOStorage實例
        storage = MinIOStorage()
        
        # 創建測試記錄
        test_records = [
            StandardizedRecord(
                id="test_1",
                platform="test",
                content="Test content 1",
                author="test_user",
                timestamp=datetime.now(),
                metadata={"test": True}
            ),
            StandardizedRecord(
                id="test_2",
                platform="test",
                content="Test content 2",
                author="test_user",
                timestamp=datetime.now(),
                metadata={"test": True}
            )
        ]
        
        # 測試存儲
        result = storage.store_records_as_parquet(test_records, "test_platform")
        
        if result['success']:
            print("✅ MinIOStorage類測試成功")
            print(f"   文件鍵: {result['file_key']}")
            print(f"   記錄數: {result['records_count']}")
            print(f"   文件大小: {result['file_size']} bytes")
            
            # 清理測試文件
            storage.delete_file(result['file_key'])
            print("✅ 測試文件清理完成")
            
            return True
        else:
            print(f"❌ MinIOStorage類測試失敗: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ MinIOStorage類測試失敗: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 MinIO連接測試開始")
    print("=" * 50)
    
    tests = [
        ("S3 API連接", test_minio_s3_connection),
        ("Parquet文件上傳", test_parquet_upload),
        ("MinIOStorage類", test_minio_storage_class)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 測試結果總結:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 總計: {passed}/{len(tests)} 個測試通過")
    
    if passed == len(tests):
        print("🎉 所有測試通過！MinIO連接正常")
        return 0
    else:
        print("⚠️ 部分測試失敗，請檢查MinIO配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())

