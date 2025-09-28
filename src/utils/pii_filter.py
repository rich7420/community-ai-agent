"""
PII匿名化處理模組
實現email地址、姓名、電話號碼等敏感資訊的匿名化
支持用戶名稱的反匿名化顯示
"""
import re
import hashlib
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from .user_name_mapper import UserNameMapper

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
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'anonymized_user': re.compile(r'user_[a-f0-9]{8}'),  # 匿名化用戶ID模式
            'slack_user': re.compile(r'<@([A-Z0-9]{9,11})>')  # Slack用戶ID模式
        }
        
        # 使用者匿名化映射
        self.user_mapping = {}
        self.name_mapping = {}
        
        # 用戶名稱映射器
        self.user_name_mapper = UserNameMapper()
    
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
        
        # 匿名化URL(保留域名)
        anon_text = self.patterns['url'].sub(self._anonymize_url, anon_text)
        
        # 匿名化IP地址
        anon_text = self.patterns['ip_address'].sub('[IP_REDACTED]', anon_text)
        
        # 過濾敏感詞
        anon_text = self._filter_sensitive_words(anon_text)
        
        return anon_text
    
    def _anonymize_url(self, match) -> str:
        """匿名化URL,保留域名"""
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
            user_name: 使用者名稱(可選)
            
        Returns:
            匿名化後的使用者ID
        """
        if not user_id:
            return 'anonymous'
        
        # 如果已經匿名化過,直接返回
        if user_id in self.user_mapping:
            return self.user_mapping[user_id]
        
        # 先檢查數據庫中是否已經存在該用戶的映射
        existing_mapping = self.user_name_mapper.get_display_name_by_original_id(user_id, 'slack')
        if existing_mapping:
            # 從數據庫中獲取現有的匿名化ID
            all_mappings = self.user_name_mapper.get_all_mappings('slack')
            for mapping in all_mappings:
                if mapping.original_user_id == user_id:
                    anon_id = mapping.anonymized_id
                    self.user_mapping[user_id] = anon_id
                    return anon_id
        
        # 生成新的匿名ID
        anon_id = self._generate_anon_id(user_id)
        self.user_mapping[user_id] = anon_id
        
        # 記錄匿名化映射(僅在開發環境)
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
        
        # 如果已經匿名化過,直接返回
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
        # 暫時返回False,實際實現時需要連接資料庫
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
    
    def deanonymize_user_names(self, text: str, platform: str = None) -> str:
        """
        反匿名化文本中的用戶名稱,將匿名化ID替換為顯示名稱
        
        Args:
            text: 包含匿名化ID的文本
            platform: 平台名稱(可選)
            
        Returns:
            替換後的文本
        """
        if not text:
            return text
        
        try:
            resolved_text = text
            
            # 處理匿名化用戶ID (user_xxxxxxxx)
            anonymized_ids = self.patterns['anonymized_user'].findall(text)
            for anonymized_id in anonymized_ids:
                display_name = self.user_name_mapper.get_display_name(anonymized_id, platform)
                if display_name:
                    resolved_text = resolved_text.replace(anonymized_id, display_name)
                    self.logger.debug(f"反匿名化: {anonymized_id} -> {display_name}")
            
            # 處理Slack用戶ID (<@U092MM3QVRA>)
            slack_users = self.patterns['slack_user'].findall(text)
            for slack_id in slack_users:
                # 直接通過original_user_id查找顯示名稱
                display_name = self._get_display_name_by_original_id(slack_id, 'slack')
                if display_name:
                    resolved_text = resolved_text.replace(f'<@{slack_id}>', display_name)
                    self.logger.debug(f"反匿名化Slack用戶: <@{slack_id}> -> {display_name}")
                else:
                    # 如果找不到映射,至少移除@符號
                    resolved_text = resolved_text.replace(f'<@{slack_id}>', f'用戶{slack_id[:8]}...')
                    self.logger.debug(f"未找到Slack用戶映射: <@{slack_id}>")
            
            return resolved_text
            
        except Exception as e:
            self.logger.error(f"反匿名化用戶名稱失敗: {e}")
            return text
    
    def _get_display_name_by_original_id(self, anonymized_id: str, platform: str) -> Optional[str]:
        """
        根據匿名化ID獲取顯示名稱
        
        Args:
            anonymized_id: 匿名化ID
            platform: 平台名稱
            
        Returns:
            顯示名稱,如果找不到則返回None
        """
        try:
            # 直接查詢數據庫獲取顯示名稱
            from storage.connection_pool import get_db_connection, return_db_connection
            from psycopg2.extras import RealDictCursor
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT display_name, real_name
                FROM user_name_mappings 
                WHERE anonymized_id = %s
                LIMIT 1
            """, (anonymized_id,))
            
            result = cur.fetchone()
            cur.close()
            return_db_connection(conn)
            
            if result:
                return result['display_name'] or result['real_name']
            
            return None
            
        except Exception as e:
            self.logger.error(f"根據匿名化ID獲取顯示名稱失敗: {e}")
            return None
    
    def add_user_mapping(
        self,
        platform: str,
        original_user_id: str,
        anonymized_id: str,
        display_name: str,
        real_name: Optional[str] = None,
        aliases: List[str] = None,
        group_terms: List[str] = None
    ) -> bool:
        """
        添加用戶映射到映射表
        
        Args:
            platform: 平台名稱
            original_user_id: 原始用戶ID
            anonymized_id: 匿名化ID
            display_name: 顯示名稱
            real_name: 真實姓名
            aliases: 別名列表
            group_terms: 群體稱呼列表
            
        Returns:
            是否成功添加
        """
        try:
            return self.user_name_mapper.add_user_mapping(
                platform=platform,
                original_user_id=original_user_id,
                anonymized_id=anonymized_id,
                display_name=display_name,
                real_name=real_name,
                aliases=aliases,
                group_terms=group_terms
            )
        except Exception as e:
            self.logger.error(f"添加用戶映射失敗: {e}")
            return False
    
    def get_user_display_name(self, anonymized_id: str, platform: str = None) -> Optional[str]:
        """
        獲取用戶的顯示名稱
        
        Args:
            anonymized_id: 匿名化ID
            platform: 平台名稱(可選)
            
        Returns:
            顯示名稱,如果找不到則返回None
        """
        try:
            return self.user_name_mapper.get_display_name(anonymized_id, platform)
        except Exception as e:
            self.logger.error(f"獲取用戶顯示名稱失敗: {e}")
            return None
    
    def resolve_user_references(self, text: str, platform: str = None) -> str:
        """
        解析文本中的用戶引用,包括別名和群體稱呼
        
        Args:
            text: 包含用戶引用的文本
            platform: 平台名稱(可選)
            
        Returns:
            解析後的文本
        """
        if not text:
            return text
        
        try:
            # 首先反匿名化匿名化ID
            resolved_text = self.deanonymize_user_names(text, platform)
            
            # 統一處理所有用戶引用,避免重複替換
            resolved_text = self._resolve_all_user_references(resolved_text, platform)
            
            return resolved_text
            
        except Exception as e:
            self.logger.error(f"解析用戶引用失敗: {e}")
            return text
    
    def _resolve_all_user_references(self, text: str, platform: str = None) -> str:
        """統一解析所有用戶引用,避免重複替換"""
        try:
            # 獲取所有用戶映射
            all_mappings = self.user_name_mapper.get_all_mappings(platform)
            
            # 創建替換映射表,避免衝突
            replacements = {}
            group_term_users = {}  # 追蹤群體稱呼對應的用戶
            
            for mapping in all_mappings:
                # 收集別名
                for alias in mapping.aliases:
                    if alias and alias != mapping.display_name:
                        if alias not in replacements:
                            replacements[alias] = mapping.display_name
                
                # 收集群體稱呼,處理衝突
                for group_term in mapping.group_terms:
                    if group_term and group_term != mapping.display_name:
                        if group_term not in group_term_users:
                            group_term_users[group_term] = [mapping.display_name]
                        else:
                            group_term_users[group_term].append(mapping.display_name)
            
            # 處理群體稱呼衝突
            for group_term, users in group_term_users.items():
                if len(users) == 1:
                    # 只有一個用戶,直接替換
                    replacements[group_term] = users[0]
                else:
                    # 多個用戶,根據群體稱呼選擇最合適的用戶
                    if group_term == 'mentor':
                        # mentor優先選擇蔡嘉平
                        if '蔡嘉平' in users:
                            replacements[group_term] = '蔡嘉平'
                        else:
                            replacements[group_term] = users[0]
                    elif group_term == 'leader':
                        # leader優先選擇蔡嘉平
                        if '蔡嘉平' in users:
                            replacements[group_term] = '蔡嘉平'
                        else:
                            replacements[group_term] = users[0]
                    elif group_term == '社群老大':
                        # 社群老大優先選擇蔡嘉平
                        if '蔡嘉平' in users:
                            replacements[group_term] = '蔡嘉平'
                        else:
                            replacements[group_term] = users[0]
                    else:
                        # 其他群體稱呼,優先選擇蔡嘉平(因為他是主要mentor)
                        if '蔡嘉平' in users:
                            replacements[group_term] = '蔡嘉平'
                        else:
                            replacements[group_term] = users[0]
            
            # 按替換目標長度排序,先替換長的名稱
            sorted_replacements = sorted(replacements.items(), key=lambda x: len(x[1]), reverse=True)
            
            # 執行替換,避免重複
            for old_text, new_text in sorted_replacements:
                if old_text in text and new_text not in text:
                    # 直接替換,因為中文不需要詞邊界
                    text = text.replace(old_text, new_text)
                    self.logger.debug(f"替換: {old_text} -> {new_text}")
            
            return text
            
        except Exception as e:
            self.logger.error(f"統一解析用戶引用失敗: {e}")
            return text
    
    def _resolve_group_terms(self, text: str, platform: str = None) -> str:
        """解析群體稱呼"""
        try:
            # 常見的群體稱呼
            group_terms = ['大神', '大佬', '專家', '前輩', '老師', 'mentor', 'leader']
            
            for term in group_terms:
                if term in text:
                    # 查找這個群體稱呼對應的用戶
                    users = self.user_name_mapper.get_user_by_group_term(term, platform)
                    if users:
                        # 如果只有一個用戶,直接替換
                        if len(users) == 1:
                            user = users[0]
                            text = text.replace(term, user.display_name)
                        # 如果有多個用戶,根據上下文選擇最合適的
                        else:
                            # 這裡可以實現更複雜的上下文匹配邏輯
                            # 暫時使用第一個用戶
                            user = users[0]
                            text = text.replace(term, f"{user.display_name}({term})")
            
            return text
            
        except Exception as e:
            self.logger.error(f"解析群體稱呼失敗: {e}")
            return text
    
    def _resolve_aliases(self, text: str, platform: str = None) -> str:
        """解析別名"""
        try:
            # 獲取所有用戶映射
            all_mappings = self.user_name_mapper.get_all_mappings(platform)
            
            # 創建替換映射表,避免重複替換
            replacements = {}
            
            for mapping in all_mappings:
                # 收集所有需要替換的別名和群體稱呼
                for alias in mapping.aliases:
                    if alias and alias != mapping.display_name:
                        replacements[alias] = mapping.display_name
                
                for group_term in mapping.group_terms:
                    if group_term and group_term != mapping.display_name:
                        replacements[group_term] = mapping.display_name
            
            # 按替換目標長度排序,先替換長的名稱
            sorted_replacements = sorted(replacements.items(), key=lambda x: len(x[1]), reverse=True)
            
            # 執行替換
            for old_text, new_text in sorted_replacements:
                if old_text in text:
                    # 使用正則表達式確保只替換完整的詞
                    import re
                    pattern = r'\b' + re.escape(old_text) + r'\b'
                    text = re.sub(pattern, new_text, text)
            
            return text
            
        except Exception as e:
            self.logger.error(f"解析別名失敗: {e}")
            return text

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
    
    def deanonymize_user_names(self, text: str, platform: str = None) -> str:
        """
        反匿名化文本中的用戶名稱,將匿名化ID替換為顯示名稱
        
        Args:
            text: 包含匿名化ID的文本
            platform: 平台名稱(可選)
            
        Returns:
            替換後的文本
        """
        if not text:
            return text
        
        try:
            resolved_text = text
            
            # 處理匿名化用戶ID (user_xxxxxxxx)
            anonymized_ids = self.patterns['anonymized_user'].findall(text)
            for anonymized_id in anonymized_ids:
                display_name = self.user_name_mapper.get_display_name(anonymized_id, platform)
                if display_name:
                    resolved_text = resolved_text.replace(anonymized_id, display_name)
                    self.logger.debug(f"反匿名化: {anonymized_id} -> {display_name}")
            
            # 處理Slack用戶ID (<@U092MM3QVRA>)
            slack_users = self.patterns['slack_user'].findall(text)
            for slack_id in slack_users:
                # 直接通過original_user_id查找顯示名稱
                display_name = self._get_display_name_by_original_id(slack_id, 'slack')
                if display_name:
                    resolved_text = resolved_text.replace(f'<@{slack_id}>', display_name)
                    self.logger.debug(f"反匿名化Slack用戶: <@{slack_id}> -> {display_name}")
                else:
                    # 如果找不到映射,至少移除@符號
                    resolved_text = resolved_text.replace(f'<@{slack_id}>', f'用戶{slack_id[:8]}...')
                    self.logger.debug(f"未找到Slack用戶映射: <@{slack_id}>")
            
            return resolved_text
            
        except Exception as e:
            self.logger.error(f"反匿名化用戶名稱失敗: {e}")
            return text
    
    def _get_display_name_by_original_id(self, anonymized_id: str, platform: str) -> Optional[str]:
        """
        根據匿名化ID獲取顯示名稱
        
        Args:
            anonymized_id: 匿名化ID
            platform: 平台名稱
            
        Returns:
            顯示名稱,如果找不到則返回None
        """
        try:
            # 直接查詢數據庫獲取顯示名稱
            from storage.connection_pool import get_db_connection, return_db_connection
            from psycopg2.extras import RealDictCursor
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT display_name, real_name
                FROM user_name_mappings 
                WHERE anonymized_id = %s
                LIMIT 1
            """, (anonymized_id,))
            
            result = cur.fetchone()
            cur.close()
            return_db_connection(conn)
            
            if result:
                return result['display_name'] or result['real_name']
            
            return None
            
        except Exception as e:
            self.logger.error(f"根據匿名化ID獲取顯示名稱失敗: {e}")
            return None
    
    def add_user_mapping(
        self,
        platform: str,
        original_user_id: str,
        anonymized_id: str,
        display_name: str,
        real_name: Optional[str] = None,
        aliases: List[str] = None,
        group_terms: List[str] = None
    ) -> bool:
        """
        添加用戶映射到映射表
        
        Args:
            platform: 平台名稱
            original_user_id: 原始用戶ID
            anonymized_id: 匿名化ID
            display_name: 顯示名稱
            real_name: 真實姓名
            aliases: 別名列表
            group_terms: 群體稱呼列表
            
        Returns:
            是否成功添加
        """
        try:
            return self.user_name_mapper.add_user_mapping(
                platform=platform,
                original_user_id=original_user_id,
                anonymized_id=anonymized_id,
                display_name=display_name,
                real_name=real_name,
                aliases=aliases,
                group_terms=group_terms
            )
        except Exception as e:
            self.logger.error(f"添加用戶映射失敗: {e}")
            return False
    
    def get_user_display_name(self, anonymized_id: str, platform: str = None) -> Optional[str]:
        """
        獲取用戶的顯示名稱
        
        Args:
            anonymized_id: 匿名化ID
            platform: 平台名稱(可選)
            
        Returns:
            顯示名稱,如果找不到則返回None
        """
        try:
            return self.user_name_mapper.get_display_name(anonymized_id, platform)
        except Exception as e:
            self.logger.error(f"獲取用戶顯示名稱失敗: {e}")
            return None
    
    def resolve_user_references(self, text: str, platform: str = None) -> str:
        """
        解析文本中的用戶引用,包括別名和群體稱呼
        
        Args:
            text: 包含用戶引用的文本
            platform: 平台名稱(可選)
            
        Returns:
            解析後的文本
        """
        if not text:
            return text
        
        try:
            # 首先反匿名化匿名化ID
            resolved_text = self.deanonymize_user_names(text, platform)
            
            # 統一處理所有用戶引用,避免重複替換
            resolved_text = self._resolve_all_user_references(resolved_text, platform)
            
            return resolved_text
            
        except Exception as e:
            self.logger.error(f"解析用戶引用失敗: {e}")
            return text
    
    def _resolve_all_user_references(self, text: str, platform: str = None) -> str:
        """統一解析所有用戶引用,避免重複替換"""
        try:
            # 獲取所有用戶映射
            all_mappings = self.user_name_mapper.get_all_mappings(platform)
            
            # 創建替換映射表,避免衝突
            replacements = {}
            group_term_users = {}  # 追蹤群體稱呼對應的用戶
            
            for mapping in all_mappings:
                # 收集別名
                for alias in mapping.aliases:
                    if alias and alias != mapping.display_name:
                        if alias not in replacements:
                            replacements[alias] = mapping.display_name
                
                # 收集群體稱呼,處理衝突
                for group_term in mapping.group_terms:
                    if group_term and group_term != mapping.display_name:
                        if group_term not in group_term_users:
                            group_term_users[group_term] = [mapping.display_name]
                        else:
                            group_term_users[group_term].append(mapping.display_name)
            
            # 處理群體稱呼衝突
            for group_term, users in group_term_users.items():
                if len(users) == 1:
                    # 只有一個用戶,直接替換
                    replacements[group_term] = users[0]
                else:
                    # 多個用戶,根據群體稱呼選擇最合適的用戶
                    if group_term == 'mentor':
                        # mentor優先選擇蔡嘉平
                        if '蔡嘉平' in users:
                            replacements[group_term] = '蔡嘉平'
                        else:
                            replacements[group_term] = users[0]
                    elif group_term == 'leader':
                        # leader優先選擇蔡嘉平
                        if '蔡嘉平' in users:
                            replacements[group_term] = '蔡嘉平'
                        else:
                            replacements[group_term] = users[0]
                    elif group_term == '社群老大':
                        # 社群老大優先選擇蔡嘉平
                        if '蔡嘉平' in users:
                            replacements[group_term] = '蔡嘉平'
                        else:
                            replacements[group_term] = users[0]
                    else:
                        # 其他群體稱呼,優先選擇蔡嘉平(因為他是主要mentor)
                        if '蔡嘉平' in users:
                            replacements[group_term] = '蔡嘉平'
                        else:
                            replacements[group_term] = users[0]
            
            # 按替換目標長度排序,先替換長的名稱
            sorted_replacements = sorted(replacements.items(), key=lambda x: len(x[1]), reverse=True)
            
            # 執行替換,避免重複
            for old_text, new_text in sorted_replacements:
                if old_text in text and new_text not in text:
                    # 直接替換,因為中文不需要詞邊界
                    text = text.replace(old_text, new_text)
                    self.logger.debug(f"替換: {old_text} -> {new_text}")
            
            return text
            
        except Exception as e:
            self.logger.error(f"統一解析用戶引用失敗: {e}")
            return text
    
    def _resolve_group_terms(self, text: str, platform: str = None) -> str:
        """解析群體稱呼"""
        try:
            # 常見的群體稱呼
            group_terms = ['大神', '大佬', '專家', '前輩', '老師', 'mentor', 'leader']
            
            for term in group_terms:
                if term in text:
                    # 查找這個群體稱呼對應的用戶
                    users = self.user_name_mapper.get_user_by_group_term(term, platform)
                    if users:
                        # 如果只有一個用戶,直接替換
                        if len(users) == 1:
                            user = users[0]
                            text = text.replace(term, user.display_name)
                        # 如果有多個用戶,根據上下文選擇最合適的
                        else:
                            # 這裡可以實現更複雜的上下文匹配邏輯
                            # 暫時使用第一個用戶
                            user = users[0]
                            text = text.replace(term, f"{user.display_name}({term})")
            
            return text
            
        except Exception as e:
            self.logger.error(f"解析群體稱呼失敗: {e}")
            return text
    
    def _resolve_aliases(self, text: str, platform: str = None) -> str:
        """解析別名"""
        try:
            # 獲取所有用戶映射
            all_mappings = self.user_name_mapper.get_all_mappings(platform)
            
            # 創建替換映射表,避免重複替換
            replacements = {}
            
            for mapping in all_mappings:
                # 收集所有需要替換的別名和群體稱呼
                for alias in mapping.aliases:
                    if alias and alias != mapping.display_name:
                        replacements[alias] = mapping.display_name
                
                for group_term in mapping.group_terms:
                    if group_term and group_term != mapping.display_name:
                        replacements[group_term] = mapping.display_name
            
            # 按替換目標長度排序,先替換長的名稱
            sorted_replacements = sorted(replacements.items(), key=lambda x: len(x[1]), reverse=True)
            
            # 執行替換
            for old_text, new_text in sorted_replacements:
                if old_text in text:
                    # 使用正則表達式確保只替換完整的詞
                    import re
                    pattern = r'\b' + re.escape(old_text) + r'\b'
                    text = re.sub(pattern, new_text, text)
            
            return text
            
        except Exception as e:
            self.logger.error(f"解析別名失敗: {e}")
            return text
