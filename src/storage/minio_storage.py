"""
MinIO儲存模組
實現Parquet文件生成、S3-compatible上傳、資料分區策略
"""
import os
import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from io import BytesIO
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from utils.logging_config import structured_logger
from storage.connection_pool import get_s3_client
from collectors.data_merger import StandardizedRecord

class MinIOStorage:
    """MinIO儲存器"""
    
    def __init__(self, bucket_name: str = None):
        """
        初始化MinIO儲存器
        
        Args:
            bucket_name: 儲存桶名稱
        """
        self.bucket_name = bucket_name or os.getenv('MINIO_BUCKET', 'community-data-lake')
        self.logger = logging.getLogger(__name__)
        
        # 獲取S3客戶端
        self.s3_client = get_s3_client()
        
        # 分區策略配置
        self.partition_strategy = {
            'by_date': True,
            'by_platform': True,
            'date_format': '%Y/%m/%d'
        }
        
        # 統計信息
        self.stats = {
            'files_uploaded': 0,
            'records_stored': 0,
            'bytes_uploaded': 0,
            'errors': 0
        }
    
    def store_records_as_parquet(self, records: List[StandardizedRecord], 
                                platform: str, 
                                partition_date: datetime = None) -> Dict[str, Any]:
        """
        將記錄存儲為Parquet格式
        
        Args:
            records: 標準化記錄列表
            platform: 平台名稱
            partition_date: 分區日期
            
        Returns:
            存儲結果字典
        """
        if not records:
            return {'success': False, 'message': 'No records to store'}
        
        try:
            # 準備數據
            df = self._prepare_dataframe(records)
            
            # 生成分區路徑
            partition_path = self._generate_partition_path(platform, partition_date)
            
            # 創建Parquet文件
            parquet_buffer = self._create_parquet_buffer(df)
            
            # 上傳到MinIO
            file_key = f"{partition_path}/data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
            upload_result = self._upload_to_minio(parquet_buffer, file_key)
            
            # 更新統計
            self._update_stats(len(records), len(parquet_buffer.getvalue()))
            
            # 記錄日誌
            structured_logger.log_data_collection(
                platform=platform,
                records_count=len(records),
                duration=0.0,
                file_key=file_key,
                bucket=self.bucket_name
            )
            
            return {
                'success': True,
                'file_key': file_key,
                'records_count': len(records),
                'file_size': len(parquet_buffer.getvalue()),
                'bucket': self.bucket_name
            }
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Failed to store records: {e}")
            return {'success': False, 'error': str(e)}
    
    def _prepare_dataframe(self, records: List[StandardizedRecord]) -> pd.DataFrame:
        """準備DataFrame"""
        data = []
        for record in records:
            data.append({
                'id': record.id,
                'platform': record.platform,
                'content': record.content,
                'author': record.author,
                'timestamp': record.timestamp,
                'metadata': record.metadata,
                'created_at': datetime.now()
            })
        return pd.DataFrame(data)
    
    def _generate_partition_path(self, platform: str, partition_date: datetime = None) -> str:
        """生成分區路徑"""
        if partition_date is None:
            partition_date = datetime.now()
        
        date_str = partition_date.strftime(self.partition_strategy['date_format'])
        return f"platform={platform}/date={date_str}"
    
    def _create_parquet_buffer(self, df: pd.DataFrame) -> BytesIO:
        """創建Parquet緩衝區"""
        buffer = BytesIO()
        
        # 轉換為PyArrow表
        table = pa.Table.from_pandas(df)
        
        # 寫入Parquet格式
        pq.write_table(table, buffer)
        buffer.seek(0)
        
        return buffer
    
    def _upload_to_minio(self, buffer: BytesIO, file_key: str) -> Dict[str, Any]:
        """上傳到MinIO"""
        try:
            # 確保bucket存在
            self._ensure_bucket_exists()
            
            # 上傳文件
            buffer.seek(0)
            self.s3_client.upload_fileobj(
                buffer,
                self.bucket_name,
                file_key,
                ExtraArgs={
                    'ContentType': 'application/octet-stream',
                    'Metadata': {
                        'uploaded_at': datetime.now().isoformat(),
                        'file_type': 'parquet'
                    }
                }
            )
            
            self.stats['files_uploaded'] += 1
            return {'success': True, 'file_key': file_key}
            
        except ClientError as e:
            self.logger.error(f"S3 upload error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Upload error: {e}")
            raise
    
    def _ensure_bucket_exists(self):
        """確保bucket存在"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Bucket不存在，創建它
                self.s3_client.create_bucket(Bucket=self.bucket_name)
                self.logger.info(f"Created bucket: {self.bucket_name}")
            else:
                raise
    
    def _update_stats(self, records_count: int, bytes_count: int):
        """更新統計信息"""
        self.stats['records_stored'] += records_count
        self.stats['bytes_uploaded'] += bytes_count
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        return self.stats.copy()
    
    def list_files(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """列出文件"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })
            
            return files
            
        except ClientError as e:
            self.logger.error(f"Error listing files: {e}")
            return []
    
    def delete_file(self, file_key: str) -> bool:
        """刪除文件"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            self.logger.error(f"Error deleting file {file_key}: {e}")
            return False
    
    def download_file(self, file_key: str) -> Optional[BytesIO]:
        """下載文件"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            buffer = BytesIO(response['Body'].read())
            return buffer
        except ClientError as e:
            self.logger.error(f"Error downloading file {file_key}: {e}")
            return None
