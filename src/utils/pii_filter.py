"""
PII匿名化處理模組
實現email地址、姓名、電話號碼等敏感資訊的匿名化
"""
import re
import hashlib
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

@dataclass
class AnonymizedUser:
    """匿名化使用者資訊"""
    original_id: str
    anon_id: str
    original_name: str
    anon_name: str

class PIIFilter:
    """PII匿名化過濾器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 敏感詞列表
        self.sensitive_words = [
            'password', 'secret', 'token', 'key', 'api_key',
            'credit_card', 'ssn', 'social_security', 'bank_account',
            'phone', 'email', 'address', 'zip', 'postal'
        ]
        
        # 正則表達式模式
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),
            'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'url': re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+'),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        }
        
        # 使用者匿名化映射
        self.user_mapping = {}
        self.name_mapping = {}
    
    def anonymize_text(self, text: str) -> str:
        """
        匿名化文字中的敏感資訊
        
        Args:
            text: 原始文字
            
        Returns:
            匿名化後的文字
        """
        if not text:
            return text
        
        anon_text = text
        
        # 匿名化email地址
        anon_text = self.patterns['email'].sub('[EMAIL_REDACTED]', anon_text)
        
        # 匿名化電話號碼
        anon_text = self.patterns['phone'].sub('[PHONE_REDACTED]', anon_text)
        
        # 匿名化信用卡號
        anon_text = self.patterns['credit_card'].sub('[CARD_REDACTED]', anon_text)
        
        # 匿名化SSN
        anon_text = self.patterns['ssn'].sub('[SSN_REDACTED]', anon_text)
        
        # 匿名化URL（保留域名）
        anon_text = self.patterns['url'].sub(self._anonymize_url, anon_text)
        
        # 匿名化IP地址
        anon_text = self.patterns['ip_address'].sub('[IP_REDACTED]', anon_text)
        
        # 過濾敏感詞
        anon_text = self._filter_sensitive_words(anon_text)
        
        return anon_text
    
    def _anonymize_url(self, match) -> str:
        """匿名化URL，保留域名"""
        url = match.group(0)
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.netloc:
                return f"https://{parsed.netloc}/[PATH_REDACTED]"
            else:
                return "[URL_REDACTED]"
        except:
            return "[URL_REDACTED]"
    
    def _filter_sensitive_words(self, text: str) -> str:
        """過濾敏感詞"""
        words = text.split()
        filtered_words = []
        
        for word in words:
            if any(sensitive in word.lower() for sensitive in self.sensitive_words):
                filtered_words.append('[SENSITIVE_REDACTED]')
            else:
                filtered_words.append(word)
        
        return ' '.join(filtered_words)
    
    def anonymize_user(self, user_id: str, user_name: str = '') -> str:
        """
        匿名化使用者ID
        
        Args:
            user_id: 原始使用者ID
            user_name: 使用者名稱（可選）
            
        Returns:
            匿名化後的使用者ID
        """
        if not user_id:
            return 'anonymous'
        
        # 如果已經匿名化過，直接返回
        if user_id in self.user_mapping:
            return self.user_mapping[user_id]
        
        # 生成匿名ID
        anon_id = self._generate_anon_id(user_id)
        self.user_mapping[user_id] = anon_id
        
        # 記錄匿名化映射（僅在開發環境）
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"使用者匿名化: {user_id} -> {anon_id}")
        
        return anon_id
    
    def anonymize_name(self, name: str) -> str:
        """
        匿名化姓名
        
        Args:
            name: 原始姓名
            
        Returns:
            匿名化後的姓名
        """
        if not name:
            return 'Anonymous'
        
        # 如果已經匿名化過，直接返回
        if name in self.name_mapping:
            return self.name_mapping[name]
        
        # 生成匿名姓名
        anon_name = self._generate_anon_name(name)
        self.name_mapping[name] = anon_name
        
        return anon_name
    
    def _generate_anon_id(self, user_id: str) -> str:
        """生成匿名使用者ID"""
        # 使用SHA256生成固定長度的匿名ID
        hash_obj = hashlib.sha256(user_id.encode())
        return f"user_{hash_obj.hexdigest()[:8]}"
    
    def _generate_anon_name(self, name: str) -> str:
        """生成匿名姓名"""
        # 使用SHA256生成固定長度的匿名姓名
        hash_obj = hashlib.sha256(name.encode())
        return f"User_{hash_obj.hexdigest()[:6]}"
    
    def get_user_mapping(self) -> Dict[str, str]:
        """獲取使用者匿名化映射"""
        return self.user_mapping.copy()
    
    def get_name_mapping(self) -> Dict[str, str]:
        """獲取姓名匿名化映射"""
        return self.name_mapping.copy()
    
    def is_opt_out_user(self, user_id: str, platform: str) -> bool:
        """
        檢查使用者是否選擇退出
        
        Args:
            user_id: 使用者ID
            platform: 平台名稱
            
        Returns:
            是否選擇退出
        """
        # 這裡應該查詢資料庫中的opt_out_users表
        # 暫時返回False，實際實現時需要連接資料庫
        return False
    
    def should_collect_user_data(self, user_id: str, platform: str) -> bool:
        """
        判斷是否應該收集使用者資料
        
        Args:
            user_id: 使用者ID
            platform: 平台名稱
            
        Returns:
            是否應該收集
        """
        # 檢查是否選擇退出
        if self.is_opt_out_user(user_id, platform):
            return False
        
        # 其他過濾條件
        return True
    
    def anonymize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        匿名化元資料
        
        Args:
            metadata: 原始元資料
            
        Returns:
            匿名化後的元資料
        """
        anon_metadata = {}
        
        for key, value in metadata.items():
            if isinstance(value, str):
                anon_metadata[key] = self.anonymize_text(value)
            elif isinstance(value, dict):
                anon_metadata[key] = self.anonymize_metadata(value)
            elif isinstance(value, list):
                anon_metadata[key] = [
                    self.anonymize_text(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                anon_metadata[key] = value
        
        return anon_metadata
