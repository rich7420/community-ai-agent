"""
用戶名稱映射管理模組
處理用戶名稱的匿名化,反匿名化和別名映射
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from storage.connection_pool import get_db_connection, return_db_connection

@dataclass
class UserMapping:
    """用戶映射資料結構"""
    id: int
    platform: str
    original_user_id: str
    anonymized_id: str
    display_name: str
    real_name: Optional[str]
    aliases: List[str]
    group_terms: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class UserNameMapper:
    """用戶名稱映射管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._mapping_cache = {}  # 緩存映射關係
        
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
        添加用戶映射
        
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
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 檢查是否已存在
            cur.execute("""
                SELECT id FROM user_name_mappings 
                WHERE platform = %s AND original_user_id = %s
            """, (platform, original_user_id))
            
            if cur.fetchone():
                # 更新現有映射
                cur.execute("""
                    UPDATE user_name_mappings SET
                        anonymized_id = %s,
                        display_name = %s,
                        real_name = %s,
                        aliases = %s,
                        group_terms = %s,
                        updated_at = NOW()
                    WHERE platform = %s AND original_user_id = %s
                """, (
                    anonymized_id, display_name, real_name, 
                    aliases or [], group_terms or [],
                    platform, original_user_id
                ))
            else:
                # 插入新映射
                cur.execute("""
                    INSERT INTO user_name_mappings (
                        platform, original_user_id, anonymized_id, 
                        display_name, real_name, aliases, group_terms
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    platform, original_user_id, anonymized_id,
                    display_name, real_name, aliases or [], group_terms or []
                ))
            
            conn.commit()
            
            # 更新緩存
            cache_key = f"{platform}:{original_user_id}"
            self._mapping_cache[cache_key] = {
                'anonymized_id': anonymized_id,
                'display_name': display_name,
                'real_name': real_name,
                'aliases': aliases or [],
                'group_terms': group_terms or []
            }
            
            self.logger.info(f"用戶映射已更新: {platform}:{original_user_id} -> {display_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加用戶映射失敗: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_display_name_by_original_id(self, original_user_id: str, platform: str = None) -> Optional[str]:
        """
        根據原始用戶ID獲取顯示名稱
        
        Args:
            original_user_id: 原始用戶ID
            platform: 平台名稱(可選)
            
        Returns:
            顯示名稱,如果找不到則返回None
        """
        try:
            # 先檢查緩存
            for cache_key, mapping in self._mapping_cache.items():
                if cache_key.endswith(f":{original_user_id}"):
                    return mapping['display_name']
            
            # 查詢數據庫
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT display_name, real_name, aliases, group_terms
                    FROM user_name_mappings 
                    WHERE original_user_id = %s AND platform = %s AND is_active = TRUE
                """, (original_user_id, platform))
            else:
                cur.execute("""
                    SELECT display_name, real_name, aliases, group_terms
                    FROM user_name_mappings 
                    WHERE original_user_id = %s AND is_active = TRUE
                """, (original_user_id,))
            
            result = cur.fetchone()
            cur.close()
            return_db_connection(conn)
            
            if result:
                return result['display_name']
            return None
            
        except Exception as e:
            self.logger.error(f"根據原始ID獲取顯示名稱失敗: {e}")
            return None

    def get_display_name(self, anonymized_id: str, platform: str = None) -> Optional[str]:
        """
        根據匿名化ID獲取顯示名稱
        
        Args:
            anonymized_id: 匿名化ID
            platform: 平台名稱(可選)
            
        Returns:
            顯示名稱,如果找不到則返回None
        """
        try:
            # 先檢查緩存
            for cache_key, mapping in self._mapping_cache.items():
                if mapping['anonymized_id'] == anonymized_id:
                    return mapping['display_name']
            
            # 查詢數據庫
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT display_name, real_name, aliases, group_terms
                    FROM user_name_mappings 
                    WHERE anonymized_id = %s AND platform = %s AND is_active = TRUE
                """, (anonymized_id, platform))
            else:
                cur.execute("""
                    SELECT display_name, real_name, aliases, group_terms
                    FROM user_name_mappings 
                    WHERE anonymized_id = %s AND is_active = TRUE
                """, (anonymized_id,))
            
            result = cur.fetchone()
            if result:
                return result['display_name']
            
            return None
            
        except Exception as e:
            self.logger.error(f"獲取顯示名稱失敗: {e}")
            return None
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_user_by_alias(self, alias: str, platform: str = None) -> Optional[UserMapping]:
        """
        根據別名獲取用戶映射
        
        Args:
            alias: 別名
            platform: 平台名稱(可選)
            
        Returns:
            用戶映射對象,如果找不到則返回None
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE %s = ANY(aliases) AND platform = %s AND is_active = TRUE
                """, (alias, platform))
            else:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE %s = ANY(aliases) AND is_active = TRUE
                """, (alias,))
            
            result = cur.fetchone()
            if result:
                return UserMapping(
                    id=result['id'],
                    platform=result['platform'],
                    original_user_id=result['original_user_id'],
                    anonymized_id=result['anonymized_id'],
                    display_name=result['display_name'],
                    real_name=result['real_name'],
                    aliases=result['aliases'] or [],
                    group_terms=result['group_terms'] or [],
                    is_active=result['is_active'],
                    created_at=result['created_at'],
                    updated_at=result['updated_at']
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"根據別名獲取用戶失敗: {e}")
            return None
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_user_by_group_term(self, group_term: str, platform: str = None) -> List[UserMapping]:
        """
        根據群體稱呼獲取用戶列表
        
        Args:
            group_term: 群體稱呼(如"大神","大佬")
            platform: 平台名稱(可選)
            
        Returns:
            用戶映射列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE %s = ANY(group_terms) AND platform = %s AND is_active = TRUE
                """, (group_term, platform))
            else:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE %s = ANY(group_terms) AND is_active = TRUE
                """, (group_term,))
            
            results = cur.fetchall()
            users = []
            
            for result in results:
                users.append(UserMapping(
                    id=result['id'],
                    platform=result['platform'],
                    original_user_id=result['original_user_id'],
                    anonymized_id=result['anonymized_id'],
                    display_name=result['display_name'],
                    real_name=result['real_name'],
                    aliases=result['aliases'] or [],
                    group_terms=result['group_terms'] or [],
                    is_active=result['is_active'],
                    created_at=result['created_at'],
                    updated_at=result['updated_at']
                ))
            
            return users
            
        except Exception as e:
            self.logger.error(f"根據群體稱呼獲取用戶失敗: {e}")
            return []
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def resolve_user_name(self, text: str, platform: str = None) -> str:
        """
        解析文本中的用戶名稱,將匿名化ID替換為顯示名稱
        
        Args:
            text: 包含匿名化ID的文本
            platform: 平台名稱(可選)
            
        Returns:
            替換後的文本
        """
        try:
            # 查找文本中的匿名化ID模式 (user_xxxxxxxx)
            import re
            pattern = r'user_[a-f0-9]{8}'
            matches = re.findall(pattern, text)
            
            resolved_text = text
            for anonymized_id in matches:
                display_name = self.get_display_name(anonymized_id, platform)
                if display_name:
                    resolved_text = resolved_text.replace(anonymized_id, display_name)
            
            return resolved_text
            
        except Exception as e:
            self.logger.error(f"解析用戶名稱失敗: {e}")
            return text
    
    def load_mappings_from_cache(self):
        """從數據庫加載所有映射到緩存"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT platform, original_user_id, anonymized_id, 
                       display_name, real_name, aliases, group_terms
                FROM user_name_mappings 
                WHERE is_active = TRUE
            """)
            
            results = cur.fetchall()
            self._mapping_cache.clear()
            
            for result in results:
                cache_key = f"{result['platform']}:{result['original_user_id']}"
                self._mapping_cache[cache_key] = {
                    'anonymized_id': result['anonymized_id'],
                    'display_name': result['display_name'],
                    'real_name': result['real_name'],
                    'aliases': result['aliases'] or [],
                    'group_terms': result['group_terms'] or []
                }
            
            self.logger.info(f"已加載 {len(self._mapping_cache)} 個用戶映射到緩存")
            
        except Exception as e:
            self.logger.error(f"加載映射緩存失敗: {e}")
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_all_mappings(self, platform: str = None) -> List[UserMapping]:
        """獲取所有用戶映射"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE platform = %s AND is_active = TRUE
                    ORDER BY created_at DESC
                """, (platform,))
            else:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE is_active = TRUE
                    ORDER BY created_at DESC
                """)
            
            results = cur.fetchall()
            mappings = []
            
            for result in results:
                mappings.append(UserMapping(
                    id=result['id'],
                    platform=result['platform'],
                    original_user_id=result['original_user_id'],
                    anonymized_id=result['anonymized_id'],
                    display_name=result['display_name'],
                    real_name=result['real_name'],
                    aliases=result['aliases'] or [],
                    group_terms=result['group_terms'] or [],
                    is_active=result['is_active'],
                    created_at=result['created_at'],
                    updated_at=result['updated_at']
                ))
            
            return mappings
            
        except Exception as e:
            self.logger.error(f"獲取所有映射失敗: {e}")
            return []
        finally:
            if 'conn' in locals():
                return_db_connection(conn)

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from storage.connection_pool import get_db_connection, return_db_connection

@dataclass
class UserMapping:
    """用戶映射資料結構"""
    id: int
    platform: str
    original_user_id: str
    anonymized_id: str
    display_name: str
    real_name: Optional[str]
    aliases: List[str]
    group_terms: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class UserNameMapper:
    """用戶名稱映射管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._mapping_cache = {}  # 緩存映射關係
        
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
        添加用戶映射
        
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
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 檢查是否已存在
            cur.execute("""
                SELECT id FROM user_name_mappings 
                WHERE platform = %s AND original_user_id = %s
            """, (platform, original_user_id))
            
            if cur.fetchone():
                # 更新現有映射
                cur.execute("""
                    UPDATE user_name_mappings SET
                        anonymized_id = %s,
                        display_name = %s,
                        real_name = %s,
                        aliases = %s,
                        group_terms = %s,
                        updated_at = NOW()
                    WHERE platform = %s AND original_user_id = %s
                """, (
                    anonymized_id, display_name, real_name, 
                    aliases or [], group_terms or [],
                    platform, original_user_id
                ))
            else:
                # 插入新映射
                cur.execute("""
                    INSERT INTO user_name_mappings (
                        platform, original_user_id, anonymized_id, 
                        display_name, real_name, aliases, group_terms
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    platform, original_user_id, anonymized_id,
                    display_name, real_name, aliases or [], group_terms or []
                ))
            
            conn.commit()
            
            # 更新緩存
            cache_key = f"{platform}:{original_user_id}"
            self._mapping_cache[cache_key] = {
                'anonymized_id': anonymized_id,
                'display_name': display_name,
                'real_name': real_name,
                'aliases': aliases or [],
                'group_terms': group_terms or []
            }
            
            self.logger.info(f"用戶映射已更新: {platform}:{original_user_id} -> {display_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"添加用戶映射失敗: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_display_name_by_original_id(self, original_user_id: str, platform: str = None) -> Optional[str]:
        """
        根據原始用戶ID獲取顯示名稱
        
        Args:
            original_user_id: 原始用戶ID
            platform: 平台名稱(可選)
            
        Returns:
            顯示名稱,如果找不到則返回None
        """
        try:
            # 先檢查緩存
            for cache_key, mapping in self._mapping_cache.items():
                if cache_key.endswith(f":{original_user_id}"):
                    return mapping['display_name']
            
            # 查詢數據庫
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT display_name, real_name, aliases, group_terms
                    FROM user_name_mappings 
                    WHERE original_user_id = %s AND platform = %s AND is_active = TRUE
                """, (original_user_id, platform))
            else:
                cur.execute("""
                    SELECT display_name, real_name, aliases, group_terms
                    FROM user_name_mappings 
                    WHERE original_user_id = %s AND is_active = TRUE
                """, (original_user_id,))
            
            result = cur.fetchone()
            cur.close()
            return_db_connection(conn)
            
            if result:
                return result['display_name']
            return None
            
        except Exception as e:
            self.logger.error(f"根據原始ID獲取顯示名稱失敗: {e}")
            return None

    def get_display_name(self, anonymized_id: str, platform: str = None) -> Optional[str]:
        """
        根據匿名化ID獲取顯示名稱
        
        Args:
            anonymized_id: 匿名化ID
            platform: 平台名稱(可選)
            
        Returns:
            顯示名稱,如果找不到則返回None
        """
        try:
            # 先檢查緩存
            for cache_key, mapping in self._mapping_cache.items():
                if mapping['anonymized_id'] == anonymized_id:
                    return mapping['display_name']
            
            # 查詢數據庫
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT display_name, real_name, aliases, group_terms
                    FROM user_name_mappings 
                    WHERE anonymized_id = %s AND platform = %s AND is_active = TRUE
                """, (anonymized_id, platform))
            else:
                cur.execute("""
                    SELECT display_name, real_name, aliases, group_terms
                    FROM user_name_mappings 
                    WHERE anonymized_id = %s AND is_active = TRUE
                """, (anonymized_id,))
            
            result = cur.fetchone()
            if result:
                return result['display_name']
            
            return None
            
        except Exception as e:
            self.logger.error(f"獲取顯示名稱失敗: {e}")
            return None
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_user_by_alias(self, alias: str, platform: str = None) -> Optional[UserMapping]:
        """
        根據別名獲取用戶映射
        
        Args:
            alias: 別名
            platform: 平台名稱(可選)
            
        Returns:
            用戶映射對象,如果找不到則返回None
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE %s = ANY(aliases) AND platform = %s AND is_active = TRUE
                """, (alias, platform))
            else:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE %s = ANY(aliases) AND is_active = TRUE
                """, (alias,))
            
            result = cur.fetchone()
            if result:
                return UserMapping(
                    id=result['id'],
                    platform=result['platform'],
                    original_user_id=result['original_user_id'],
                    anonymized_id=result['anonymized_id'],
                    display_name=result['display_name'],
                    real_name=result['real_name'],
                    aliases=result['aliases'] or [],
                    group_terms=result['group_terms'] or [],
                    is_active=result['is_active'],
                    created_at=result['created_at'],
                    updated_at=result['updated_at']
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"根據別名獲取用戶失敗: {e}")
            return None
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_user_by_group_term(self, group_term: str, platform: str = None) -> List[UserMapping]:
        """
        根據群體稱呼獲取用戶列表
        
        Args:
            group_term: 群體稱呼(如"大神","大佬")
            platform: 平台名稱(可選)
            
        Returns:
            用戶映射列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE %s = ANY(group_terms) AND platform = %s AND is_active = TRUE
                """, (group_term, platform))
            else:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE %s = ANY(group_terms) AND is_active = TRUE
                """, (group_term,))
            
            results = cur.fetchall()
            users = []
            
            for result in results:
                users.append(UserMapping(
                    id=result['id'],
                    platform=result['platform'],
                    original_user_id=result['original_user_id'],
                    anonymized_id=result['anonymized_id'],
                    display_name=result['display_name'],
                    real_name=result['real_name'],
                    aliases=result['aliases'] or [],
                    group_terms=result['group_terms'] or [],
                    is_active=result['is_active'],
                    created_at=result['created_at'],
                    updated_at=result['updated_at']
                ))
            
            return users
            
        except Exception as e:
            self.logger.error(f"根據群體稱呼獲取用戶失敗: {e}")
            return []
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def resolve_user_name(self, text: str, platform: str = None) -> str:
        """
        解析文本中的用戶名稱,將匿名化ID替換為顯示名稱
        
        Args:
            text: 包含匿名化ID的文本
            platform: 平台名稱(可選)
            
        Returns:
            替換後的文本
        """
        try:
            # 查找文本中的匿名化ID模式 (user_xxxxxxxx)
            import re
            pattern = r'user_[a-f0-9]{8}'
            matches = re.findall(pattern, text)
            
            resolved_text = text
            for anonymized_id in matches:
                display_name = self.get_display_name(anonymized_id, platform)
                if display_name:
                    resolved_text = resolved_text.replace(anonymized_id, display_name)
            
            return resolved_text
            
        except Exception as e:
            self.logger.error(f"解析用戶名稱失敗: {e}")
            return text
    
    def load_mappings_from_cache(self):
        """從數據庫加載所有映射到緩存"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT platform, original_user_id, anonymized_id, 
                       display_name, real_name, aliases, group_terms
                FROM user_name_mappings 
                WHERE is_active = TRUE
            """)
            
            results = cur.fetchall()
            self._mapping_cache.clear()
            
            for result in results:
                cache_key = f"{result['platform']}:{result['original_user_id']}"
                self._mapping_cache[cache_key] = {
                    'anonymized_id': result['anonymized_id'],
                    'display_name': result['display_name'],
                    'real_name': result['real_name'],
                    'aliases': result['aliases'] or [],
                    'group_terms': result['group_terms'] or []
                }
            
            self.logger.info(f"已加載 {len(self._mapping_cache)} 個用戶映射到緩存")
            
        except Exception as e:
            self.logger.error(f"加載映射緩存失敗: {e}")
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_all_mappings(self, platform: str = None) -> List[UserMapping]:
        """獲取所有用戶映射"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            if platform:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE platform = %s AND is_active = TRUE
                    ORDER BY created_at DESC
                """, (platform,))
            else:
                cur.execute("""
                    SELECT * FROM user_name_mappings 
                    WHERE is_active = TRUE
                    ORDER BY created_at DESC
                """)
            
            results = cur.fetchall()
            mappings = []
            
            for result in results:
                mappings.append(UserMapping(
                    id=result['id'],
                    platform=result['platform'],
                    original_user_id=result['original_user_id'],
                    anonymized_id=result['anonymized_id'],
                    display_name=result['display_name'],
                    real_name=result['real_name'],
                    aliases=result['aliases'] or [],
                    group_terms=result['group_terms'] or [],
                    is_active=result['is_active'],
                    created_at=result['created_at'],
                    updated_at=result['updated_at']
                ))
            
            return mappings
            
        except Exception as e:
            self.logger.error(f"獲取所有映射失敗: {e}")
            return []
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
