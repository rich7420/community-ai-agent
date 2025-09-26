"""
日誌配置模組
設置結構化日誌記錄和監控
"""
import os
import logging
import json
from datetime import datetime
from typing import Dict, Any

def setup_logging():
    """設置日誌配置"""
    
    # 創建logs目錄
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 設置日誌格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 配置根日誌器
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # 控制台輸出
            logging.StreamHandler(),
            # 文件輸出
            logging.FileHandler(f"{log_dir}/app.log"),
            # 錯誤日誌文件
            logging.FileHandler(f"{log_dir}/error.log")
        ]
    )
    
    # 設置錯誤日誌過濾器
    error_handler = logging.FileHandler(f"{log_dir}/error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    
    # 添加錯誤日誌過濾器
    logging.getLogger().addHandler(error_handler)
    
    # 設置特定模組的日誌級別
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

class StructuredLogger:
    """結構化日誌記錄器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, extra: Dict[str, Any] = None):
        """記錄信息日誌"""
        if extra:
            log_data = {
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                **extra
            }
            self.logger.info(json.dumps(log_data))
        else:
            self.logger.info(message)
    
    def error(self, message: str, extra: Dict[str, Any] = None):
        """記錄錯誤日誌"""
        if extra:
            log_data = {
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                **extra
            }
            self.logger.error(json.dumps(log_data))
        else:
            self.logger.error(message)
    
    def warning(self, message: str, extra: Dict[str, Any] = None):
        """記錄警告日誌"""
        if extra:
            log_data = {
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                **extra
            }
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.warning(message)
    
    def debug(self, message: str, extra: Dict[str, Any] = None):
        """記錄調試日誌"""
        if extra:
            log_data = {
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                **extra
            }
            self.logger.debug(json.dumps(log_data))
        else:
            self.logger.debug(message)
    
    def log_api_call(self, api_name: str, endpoint: str, status_code: int, 
                    duration: float, **kwargs):
        """記錄API調用"""
        log_data = {
            "event_type": "api_call",
            "api_name": api_name,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": duration * 1000,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.logger.info(json.dumps(log_data))
    
    def log_data_collection(self, platform: str, records_count: int, 
                          duration: float, **kwargs):
        """記錄資料收集"""
        log_data = {
            "event_type": "data_collection",
            "platform": platform,
            "records_count": records_count,
            "duration_ms": duration * 1000,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.logger.info(json.dumps(log_data))
    
    def log_error(self, error_type: str, error_message: str, 
                 context: Dict[str, Any] = None):
        """記錄錯誤"""
        log_data = {
            "event_type": "error",
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        self.logger.error(json.dumps(log_data))
    
    def log_performance(self, operation: str, duration: float, 
                       metrics: Dict[str, Any] = None):
        """記錄性能指標"""
        log_data = {
            "event_type": "performance",
            "operation": operation,
            "duration_ms": duration * 1000,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics or {}
        }
        self.logger.info(json.dumps(log_data))

# 初始化日誌
logger = setup_logging()
structured_logger = StructuredLogger("community_ai_agent")
