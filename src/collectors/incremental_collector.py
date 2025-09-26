"""
增量資料收集模組
實現timestamp-based增量拉取、資料去重、失敗重試等功能
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import json
import hashlib
from utils.logging_config import structured_logger
from storage.connection_pool import get_db_connection, return_db_connection

@dataclass
class CollectionState:
    """收集狀態"""
    platform: str
    last_collection_time: datetime
    last_successful_time: Optional[datetime]
    error_count: int
    last_error: Optional[str]
    total_records: int
    last_record_id: Optional[str]

class IncrementalCollector:
    """增量資料收集器"""
    
    def __init__(self, state_file: str = "collection_state.json"):
        """
        初始化增量收集器
        
        Args:
            state_file: 狀態文件路徑
        """
        self.state_file = state_file
        self.logger = logging.getLogger(__name__)
        self.states = self._load_states()
        
        # 重試配置
        self.max_retries = 3
        self.retry_delay = 60  # 秒
        self.backoff_multiplier = 2
        
        # API限制配置
        self.rate_limits = {
            'slack': {'requests_per_minute': 50, 'burst_limit': 100},
            'github': {'requests_per_hour': 5000, 'burst_limit': 100},
            'facebook': {'requests_per_hour': 200, 'burst_limit': 50}
        }
    
    def _load_states(self) -> Dict[str, CollectionState]:
        """載入收集狀態"""
        states = {}
        
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for platform, state_data in data.items():
                    states[platform] = CollectionState(
                        platform=platform,
                        last_collection_time=datetime.fromisoformat(state_data['last_collection_time']),
                        last_successful_time=datetime.fromisoformat(state_data['last_successful_time']) if state_data.get('last_successful_time') else None,
                        error_count=state_data.get('error_count', 0),
                        last_error=state_data.get('last_error'),
                        total_records=state_data.get('total_records', 0),
                        last_record_id=state_data.get('last_record_id')
                    )
            except Exception as e:
                self.logger.error(f"載入狀態文件失敗: {e}")
        
        return states
    
    def _save_states(self):
        """保存收集狀態"""
        try:
            data = {}
            for platform, state in self.states.items():
                data[platform] = {
                    'last_collection_time': state.last_collection_time.isoformat(),
                    'last_successful_time': state.last_successful_time.isoformat() if state.last_successful_time else None,
                    'error_count': state.error_count,
                    'last_error': state.last_error,
                    'total_records': state.total_records,
                    'last_record_id': state.last_record_id
                }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"保存狀態文件失敗: {e}")
    
    def get_collection_window(self, platform: str, default_hours: int = 24) -> Tuple[datetime, datetime]:
        """
        獲取收集時間窗口
        
        Args:
            platform: 平台名稱
            default_hours: 預設小時數
            
        Returns:
            (開始時間, 結束時間)
        """
        now = datetime.now()
        
        if platform in self.states:
            state = self.states[platform]
            # 從上次收集時間開始，但最多回溯default_hours小時
            start_time = state.last_collection_time
            max_start = now - timedelta(hours=default_hours)
            if start_time < max_start:
                start_time = max_start
        else:
            # 首次收集，使用預設時間窗口
            start_time = now - timedelta(hours=default_hours)
        
        return start_time, now
    
    def update_collection_state(self, platform: str, success: bool, records_count: int = 0, 
                              last_record_id: str = None, error: str = None):
        """
        更新收集狀態
        
        Args:
            platform: 平台名稱
            success: 是否成功
            records_count: 收集的記錄數
            last_record_id: 最後一條記錄ID
            error: 錯誤訊息
        """
        now = datetime.now()
        
        if platform not in self.states:
            self.states[platform] = CollectionState(
                platform=platform,
                last_collection_time=now,
                last_successful_time=None,
                error_count=0,
                last_error=None,
                total_records=0,
                last_record_id=None
            )
        
        state = self.states[platform]
        state.last_collection_time = now
        
        if success:
            state.last_successful_time = now
            state.error_count = 0
            state.last_error = None
            state.total_records += records_count
            if last_record_id:
                state.last_record_id = last_record_id
        else:
            state.error_count += 1
            state.last_error = error
        
        self._save_states()
    
    def should_retry(self, platform: str) -> bool:
        """判斷是否應該重試"""
        if platform not in self.states:
            return True
        
        state = self.states[platform]
        return state.error_count < self.max_retries
    
    def get_retry_delay(self, platform: str) -> int:
        """獲取重試延遲時間"""
        if platform not in self.states:
            return self.retry_delay
        
        state = self.states[platform]
        return self.retry_delay * (self.backoff_multiplier ** state.error_count)
    
    def check_rate_limit(self, platform: str, request_count: int) -> bool:
        """
        檢查API限制
        
        Args:
            platform: 平台名稱
            request_count: 請求數量
            
        Returns:
            是否可以繼續請求
        """
        if platform not in self.rate_limits:
            return True
        
        limits = self.rate_limits[platform]
        
        # 簡單的速率限制檢查
        # 實際實現中應該使用更複雜的令牌桶算法
        if request_count > limits['burst_limit']:
            return False
        
        return True
    
    def deduplicate_records(self, records: List[Dict[str, Any]], platform: str) -> List[Dict[str, Any]]:
        """
        資料去重
        
        Args:
            records: 記錄列表
            platform: 平台名稱
            
        Returns:
            去重後的記錄列表
        """
        seen_hashes = set()
        unique_records = []
        
        for record in records:
            # 生成記錄的唯一標識
            record_hash = self._generate_record_hash(record, platform)
            
            if record_hash not in seen_hashes:
                seen_hashes.add(record_hash)
                unique_records.append(record)
            else:
                self.logger.debug(f"發現重複記錄: {record.get('id', 'unknown')}")
        
        self.logger.info(f"去重完成: {len(records)} -> {len(unique_records)} 條記錄")
        return unique_records
    
    def _generate_record_hash(self, record: Dict[str, Any], platform: str) -> str:
        """生成記錄的唯一標識"""
        # 根據平台和記錄內容生成哈希
        key_fields = self._get_key_fields(platform)
        
        hash_data = {
            'platform': platform,
            'record_id': record.get('id', ''),
            'timestamp': record.get('timestamp', ''),
            'content': record.get('content', '')[:100]  # 只取前100個字符
        }
        
        # 添加平台特定的關鍵字段
        for field in key_fields:
            if field in record:
                hash_data[field] = record[field]
        
        # 生成SHA256哈希
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def _get_key_fields(self, platform: str) -> List[str]:
        """獲取平台特定的關鍵字段"""
        key_fields_map = {
            'slack': ['ts', 'channel', 'user'],
            'github': ['number', 'sha', 'url'],
            'facebook': ['id', 'created_time']
        }
        
        return key_fields_map.get(platform, ['id'])
    
    def collect_with_retry(self, platform: str, collect_func, *args, **kwargs) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        帶重試的收集函數
        
        Args:
            platform: 平台名稱
            collect_func: 收集函數
            *args, **kwargs: 收集函數參數
            
        Returns:
            (是否成功, 收集的記錄列表)
        """
        max_attempts = self.max_retries + 1
        
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"開始收集 {platform} 資料 (嘗試 {attempt + 1}/{max_attempts})")
                
                # 檢查速率限制
                if not self.check_rate_limit(platform, attempt + 1):
                    self.logger.warning(f"達到 {platform} API限制，等待重試")
                    time.sleep(self.get_retry_delay(platform))
                    continue
                
                # 執行收集
                start_time = time.time()
                records = collect_func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 去重
                unique_records = self.deduplicate_records(records, platform)
                
                # 更新狀態
                self.update_collection_state(
                    platform=platform,
                    success=True,
                    records_count=len(unique_records),
                    last_record_id=unique_records[-1].get('id') if unique_records else None
                )
                
                # 記錄統計
                structured_logger.log_data_collection(
                    platform=platform,
                    records_count=len(unique_records),
                    duration=duration,
                    attempt=attempt + 1
                )
                
                self.logger.info(f"{platform} 收集成功，共 {len(unique_records)} 條記錄")
                return True, unique_records
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"{platform} 收集失敗 (嘗試 {attempt + 1}): {error_msg}")
                
                # 更新錯誤狀態
                self.update_collection_state(
                    platform=platform,
                    success=False,
                    error=error_msg
                )
                
                # 如果不是最後一次嘗試，等待後重試
                if attempt < max_attempts - 1:
                    delay = self.get_retry_delay(platform)
                    self.logger.info(f"等待 {delay} 秒後重試")
                    time.sleep(delay)
                else:
                    self.logger.error(f"{platform} 收集最終失敗，已達到最大重試次數")
                    return False, []
        
        return False, []
    
    def get_collection_summary(self) -> Dict[str, Any]:
        """獲取收集摘要"""
        summary = {}
        
        for platform, state in self.states.items():
            summary[platform] = {
                'last_collection': state.last_collection_time.isoformat(),
                'last_successful': state.last_successful_time.isoformat() if state.last_successful_time else None,
                'error_count': state.error_count,
                'total_records': state.total_records,
                'status': 'healthy' if state.error_count == 0 else 'degraded' if state.error_count < self.max_retries else 'failed'
            }
        
        return summary
    
    def reset_platform_state(self, platform: str):
        """重置平台狀態"""
        if platform in self.states:
            del self.states[platform]
            self._save_states()
            self.logger.info(f"已重置 {platform} 的收集狀態")
    
    def cleanup_old_states(self, days: int = 30):
        """清理舊的狀態記錄"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        platforms_to_remove = []
        for platform, state in self.states.items():
            if state.last_collection_time < cutoff_date:
                platforms_to_remove.append(platform)
        
        for platform in platforms_to_remove:
            del self.states[platform]
        
        if platforms_to_remove:
            self._save_states()
            self.logger.info(f"已清理 {len(platforms_to_remove)} 個舊平台狀態")
