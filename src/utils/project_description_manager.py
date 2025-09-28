"""
項目描述管理模組
處理項目描述的獲取,驗證和緩存
"""
import os
import logging
import hashlib
import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor
from storage.connection_pool import get_db_connection, return_db_connection

@dataclass
class ProjectDescription:
    """項目描述資料結構"""
    id: str
    repository: str
    title: str
    description: str
    readme_content: str
    source: str  # 'github_readme', 'ai_generated', 'manual'
    confidence_score: float  # 0-1,描述的可信度
    last_updated: datetime
    is_verified: bool
    metadata: Dict[str, Any]

class ProjectDescriptionManager:
    """項目描述管理器"""
    
    def __init__(self, github_token: str = None):
        self.logger = logging.getLogger(__name__)
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self._description_cache = {}
        
    def get_project_description(self, repository: str, force_refresh: bool = False) -> Optional[ProjectDescription]:
        """
        獲取項目描述
        
        Args:
            repository: 倉庫名稱 (格式: owner/repo)
            force_refresh: 是否強制刷新
            
        Returns:
            項目描述對象
        """
        try:
            from datetime import timezone
            
            # 檢查緩存
            if not force_refresh and repository in self._description_cache:
                cached_desc = self._description_cache[repository]
                # 統一使用UTC時間進行比較
                now = datetime.now(timezone.utc)
                if cached_desc.last_updated.tzinfo is None:
                    cached_desc.last_updated = cached_desc.last_updated.replace(tzinfo=timezone.utc)
                if now - cached_desc.last_updated < timedelta(hours=24):
                    return cached_desc
            
            # 從數據庫獲取
            db_desc = self._get_from_database(repository)
            if db_desc and not force_refresh:
                # 統一使用UTC時間進行比較
                now = datetime.now(timezone.utc)
                if db_desc.last_updated.tzinfo is None:
                    db_desc.last_updated = db_desc.last_updated.replace(tzinfo=timezone.utc)
                if now - db_desc.last_updated < timedelta(hours=24):
                    self._description_cache[repository] = db_desc
                    return db_desc
            
            # 從GitHub獲取最新描述
            github_desc = self._get_from_github(repository)
            if github_desc:
                # 保存到數據庫
                self._save_to_database(github_desc)
                self._description_cache[repository] = github_desc
                return github_desc
            
            # 如果GitHub獲取失敗,返回數據庫中的版本
            if db_desc:
                return db_desc
                
            return None
            
        except Exception as e:
            self.logger.error(f"獲取項目描述失敗 {repository}: {e}")
            return None
    
    def _get_from_github(self, repository: str) -> Optional[ProjectDescription]:
        """從GitHub獲取項目描述"""
        try:
            if not self.github_token:
                self.logger.warning("GitHub token未設置,無法獲取項目描述")
                return None
            
            # 獲取倉庫信息
            repo_info = self._fetch_repository_info(repository)
            if not repo_info:
                return None
            
            # 獲取README內容
            readme_content = self._fetch_readme_content(repository)
            
            # 構建項目描述
            description = self._extract_description_from_readme(readme_content, repo_info)
            
            from datetime import timezone
            return ProjectDescription(
                id=f"proj_{hashlib.md5(repository.encode()).hexdigest()[:8]}",
                repository=repository,
                title=repo_info.get('name', ''),
                description=description,
                readme_content=readme_content,
                source='github_readme',
                confidence_score=0.9,  # GitHub README的可信度較高
                last_updated=datetime.now(timezone.utc),
                is_verified=True,
                metadata={
                    'github_url': repo_info.get('html_url', ''),
                    'stars': repo_info.get('stargazers_count', 0),
                    'forks': repo_info.get('forks_count', 0),
                    'language': repo_info.get('language', ''),
                    'topics': list(repo_info.get('topics', []))  # 確保是list而不是其他類型
                }
            )
            
        except Exception as e:
            self.logger.error(f"從GitHub獲取項目描述失敗 {repository}: {e}")
            return None
    
    def _fetch_repository_info(self, repository: str) -> Optional[Dict[str, Any]]:
        """獲取倉庫基本信息"""
        try:
            url = f"https://api.github.com/repos/{repository}"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"獲取倉庫信息失敗 {repository}: {e}")
            return None
    
    def _fetch_readme_content(self, repository: str) -> str:
        """獲取README內容"""
        try:
            url = f"https://api.github.com/repos/{repository}/readme"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            content = data.get('content', '')
            
            # 解碼base64內容
            import base64
            decoded_content = base64.b64decode(content).decode('utf-8')
            
            return decoded_content
            
        except Exception as e:
            self.logger.warning(f"獲取README內容失敗 {repository}: {e}")
            return ""
    
    def _extract_description_from_readme(self, readme_content: str, repo_info: Dict[str, Any]) -> str:
        """從README中提取項目描述"""
        try:
            # 優先使用GitHub倉庫的基本信息構建描述
            language = repo_info.get('language', '')
            description = repo_info.get('description', '')
            name = repo_info.get('name', '')
            
            # 構建包含語言信息的描述
            if language and description:
                enhanced_description = f"{description} (開發語言: {language})"
            elif language:
                enhanced_description = f"{name} (開發語言: {language})"
            else:
                enhanced_description = description or name
            
            # 如果README內容存在且不是LICENSE信息,嘗試提取更多信息
            if readme_content and not readme_content.strip().startswith('<!--'):
                # 提取README的第一段非標題內容作為描述
                lines = readme_content.split('\n')
                description_lines = []
                
                for line in lines:
                    line = line.strip()
                    # 跳過空行和標題行
                    if not line or line.startswith('#'):
                        continue
                    # 跳過圖片和鏈接行
                    if line.startswith('![') or line.startswith('['):
                        continue
                    # 跳過代碼塊標記
                    if line.startswith('```'):
                        continue
                    # 跳過LICENSE相關內容
                    if 'license' in line.lower() or 'apache' in line.lower():
                        continue
                    
                    description_lines.append(line)
                    
                    # 如果已經有足夠的描述內容,停止
                    if len(' '.join(description_lines)) > 200:
                        break
                
                readme_description = ' '.join(description_lines).strip()
                
                # 如果README提取的描述有意義,則使用它
                if len(readme_description) > 50 and not readme_description.startswith('<!--'):
                    enhanced_description = f"{enhanced_description}\n\n{readme_description}"
            
            return enhanced_description[:1000]  # 增加長度限制
            
        except Exception as e:
            self.logger.error(f"提取README描述失敗: {e}")
            return repo_info.get('description', '')
    
    def _get_from_database(self, repository: str) -> Optional[ProjectDescription]:
        """從數據庫獲取項目描述"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT * FROM project_descriptions 
                WHERE repository = %s 
                ORDER BY last_updated DESC 
                LIMIT 1
            """, (repository,))
            
            result = cur.fetchone()
            if result:
                # 解析JSON metadata
                metadata = {}
                if result['metadata']:
                    try:
                        metadata = json.loads(result['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                
                return ProjectDescription(
                    id=result['id'],
                    repository=result['repository'],
                    title=result['title'],
                    description=result['description'],
                    readme_content=result['readme_content'],
                    source=result['source'],
                    confidence_score=result['confidence_score'],
                    last_updated=result['last_updated'],
                    is_verified=result['is_verified'],
                    metadata=metadata
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"從數據庫獲取項目描述失敗: {e}")
            return None
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def _save_to_database(self, description: ProjectDescription) -> bool:
        """保存項目描述到數據庫"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 將metadata轉換為JSON字符串
            metadata_json = json.dumps(description.metadata) if description.metadata else None
            
            # 檢查是否已存在
            cur.execute("""
                SELECT id FROM project_descriptions 
                WHERE repository = %s
            """, (description.repository,))
            
            if cur.fetchone():
                # 更新現有記錄
                cur.execute("""
                    UPDATE project_descriptions SET
                        title = %s,
                        description = %s,
                        readme_content = %s,
                        source = %s,
                        confidence_score = %s,
                        last_updated = %s,
                        is_verified = %s,
                        metadata = %s
                    WHERE repository = %s
                """, (
                    description.title,
                    description.description,
                    description.readme_content,
                    description.source,
                    description.confidence_score,
                    description.last_updated,
                    description.is_verified,
                    metadata_json,
                    description.repository
                ))
            else:
                # 插入新記錄
                cur.execute("""
                    INSERT INTO project_descriptions (
                        id, repository, title, description, readme_content,
                        source, confidence_score, last_updated, is_verified, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    description.id,
                    description.repository,
                    description.title,
                    description.description,
                    description.readme_content,
                    description.source,
                    description.confidence_score,
                    description.last_updated,
                    description.is_verified,
                    metadata_json
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"保存項目描述到數據庫失敗: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_all_project_descriptions(self) -> List[ProjectDescription]:
        """獲取所有項目描述"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT * FROM project_descriptions 
                ORDER BY last_updated DESC
            """)
            
            results = cur.fetchall()
            descriptions = []
            
            for result in results:
                # 解析JSON metadata
                metadata = {}
                if result['metadata']:
                    try:
                        metadata = json.loads(result['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                
                descriptions.append(ProjectDescription(
                    id=result['id'],
                    repository=result['repository'],
                    title=result['title'],
                    description=result['description'],
                    readme_content=result['readme_content'],
                    source=result['source'],
                    confidence_score=result['confidence_score'],
                    last_updated=result['last_updated'],
                    is_verified=result['is_verified'],
                    metadata=metadata
                ))
            
            return descriptions
            
        except Exception as e:
            self.logger.error(f"獲取所有項目描述失敗: {e}")
            return []
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def verify_project_description(self, repository: str, description: str) -> bool:
        """驗證項目描述是否準確"""
        try:
            # 獲取官方描述
            official_desc = self.get_project_description(repository)
            if not official_desc:
                return False
            
            # 簡單的相似度檢查(可以改進為更複雜的NLP比較)
            official_text = official_desc.description.lower()
            provided_text = description.lower()
            
            # 計算關鍵詞重疊度
            official_words = set(official_text.split())
            provided_words = set(provided_text.split())
            
            if len(official_words) == 0:
                return False
            
            overlap = len(official_words.intersection(provided_words))
            similarity = overlap / len(official_words)
            
            return similarity > 0.3  # 30%以上的重疊度認為是準確的
            
        except Exception as e:
            self.logger.error(f"驗證項目描述失敗: {e}")
            return False

import os
import logging
import hashlib
import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor
from storage.connection_pool import get_db_connection, return_db_connection

@dataclass
class ProjectDescription:
    """項目描述資料結構"""
    id: str
    repository: str
    title: str
    description: str
    readme_content: str
    source: str  # 'github_readme', 'ai_generated', 'manual'
    confidence_score: float  # 0-1,描述的可信度
    last_updated: datetime
    is_verified: bool
    metadata: Dict[str, Any]

class ProjectDescriptionManager:
    """項目描述管理器"""
    
    def __init__(self, github_token: str = None):
        self.logger = logging.getLogger(__name__)
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self._description_cache = {}
        
    def get_project_description(self, repository: str, force_refresh: bool = False) -> Optional[ProjectDescription]:
        """
        獲取項目描述
        
        Args:
            repository: 倉庫名稱 (格式: owner/repo)
            force_refresh: 是否強制刷新
            
        Returns:
            項目描述對象
        """
        try:
            from datetime import timezone
            
            # 檢查緩存
            if not force_refresh and repository in self._description_cache:
                cached_desc = self._description_cache[repository]
                # 統一使用UTC時間進行比較
                now = datetime.now(timezone.utc)
                if cached_desc.last_updated.tzinfo is None:
                    cached_desc.last_updated = cached_desc.last_updated.replace(tzinfo=timezone.utc)
                if now - cached_desc.last_updated < timedelta(hours=24):
                    return cached_desc
            
            # 從數據庫獲取
            db_desc = self._get_from_database(repository)
            if db_desc and not force_refresh:
                # 統一使用UTC時間進行比較
                now = datetime.now(timezone.utc)
                if db_desc.last_updated.tzinfo is None:
                    db_desc.last_updated = db_desc.last_updated.replace(tzinfo=timezone.utc)
                if now - db_desc.last_updated < timedelta(hours=24):
                    self._description_cache[repository] = db_desc
                    return db_desc
            
            # 從GitHub獲取最新描述
            github_desc = self._get_from_github(repository)
            if github_desc:
                # 保存到數據庫
                self._save_to_database(github_desc)
                self._description_cache[repository] = github_desc
                return github_desc
            
            # 如果GitHub獲取失敗,返回數據庫中的版本
            if db_desc:
                return db_desc
                
            return None
            
        except Exception as e:
            self.logger.error(f"獲取項目描述失敗 {repository}: {e}")
            return None
    
    def _get_from_github(self, repository: str) -> Optional[ProjectDescription]:
        """從GitHub獲取項目描述"""
        try:
            if not self.github_token:
                self.logger.warning("GitHub token未設置,無法獲取項目描述")
                return None
            
            # 獲取倉庫信息
            repo_info = self._fetch_repository_info(repository)
            if not repo_info:
                return None
            
            # 獲取README內容
            readme_content = self._fetch_readme_content(repository)
            
            # 構建項目描述
            description = self._extract_description_from_readme(readme_content, repo_info)
            
            from datetime import timezone
            return ProjectDescription(
                id=f"proj_{hashlib.md5(repository.encode()).hexdigest()[:8]}",
                repository=repository,
                title=repo_info.get('name', ''),
                description=description,
                readme_content=readme_content,
                source='github_readme',
                confidence_score=0.9,  # GitHub README的可信度較高
                last_updated=datetime.now(timezone.utc),
                is_verified=True,
                metadata={
                    'github_url': repo_info.get('html_url', ''),
                    'stars': repo_info.get('stargazers_count', 0),
                    'forks': repo_info.get('forks_count', 0),
                    'language': repo_info.get('language', ''),
                    'topics': list(repo_info.get('topics', []))  # 確保是list而不是其他類型
                }
            )
            
        except Exception as e:
            self.logger.error(f"從GitHub獲取項目描述失敗 {repository}: {e}")
            return None
    
    def _fetch_repository_info(self, repository: str) -> Optional[Dict[str, Any]]:
        """獲取倉庫基本信息"""
        try:
            url = f"https://api.github.com/repos/{repository}"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"獲取倉庫信息失敗 {repository}: {e}")
            return None
    
    def _fetch_readme_content(self, repository: str) -> str:
        """獲取README內容"""
        try:
            url = f"https://api.github.com/repos/{repository}/readme"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            content = data.get('content', '')
            
            # 解碼base64內容
            import base64
            decoded_content = base64.b64decode(content).decode('utf-8')
            
            return decoded_content
            
        except Exception as e:
            self.logger.warning(f"獲取README內容失敗 {repository}: {e}")
            return ""
    
    def _extract_description_from_readme(self, readme_content: str, repo_info: Dict[str, Any]) -> str:
        """從README中提取項目描述"""
        try:
            # 優先使用GitHub倉庫的基本信息構建描述
            language = repo_info.get('language', '')
            description = repo_info.get('description', '')
            name = repo_info.get('name', '')
            
            # 構建包含語言信息的描述
            if language and description:
                enhanced_description = f"{description} (開發語言: {language})"
            elif language:
                enhanced_description = f"{name} (開發語言: {language})"
            else:
                enhanced_description = description or name
            
            # 如果README內容存在且不是LICENSE信息,嘗試提取更多信息
            if readme_content and not readme_content.strip().startswith('<!--'):
                # 提取README的第一段非標題內容作為描述
                lines = readme_content.split('\n')
                description_lines = []
                
                for line in lines:
                    line = line.strip()
                    # 跳過空行和標題行
                    if not line or line.startswith('#'):
                        continue
                    # 跳過圖片和鏈接行
                    if line.startswith('![') or line.startswith('['):
                        continue
                    # 跳過代碼塊標記
                    if line.startswith('```'):
                        continue
                    # 跳過LICENSE相關內容
                    if 'license' in line.lower() or 'apache' in line.lower():
                        continue
                    
                    description_lines.append(line)
                    
                    # 如果已經有足夠的描述內容,停止
                    if len(' '.join(description_lines)) > 200:
                        break
                
                readme_description = ' '.join(description_lines).strip()
                
                # 如果README提取的描述有意義,則使用它
                if len(readme_description) > 50 and not readme_description.startswith('<!--'):
                    enhanced_description = f"{enhanced_description}\n\n{readme_description}"
            
            return enhanced_description[:1000]  # 增加長度限制
            
        except Exception as e:
            self.logger.error(f"提取README描述失敗: {e}")
            return repo_info.get('description', '')
    
    def _get_from_database(self, repository: str) -> Optional[ProjectDescription]:
        """從數據庫獲取項目描述"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT * FROM project_descriptions 
                WHERE repository = %s 
                ORDER BY last_updated DESC 
                LIMIT 1
            """, (repository,))
            
            result = cur.fetchone()
            if result:
                # 解析JSON metadata
                metadata = {}
                if result['metadata']:
                    try:
                        metadata = json.loads(result['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                
                return ProjectDescription(
                    id=result['id'],
                    repository=result['repository'],
                    title=result['title'],
                    description=result['description'],
                    readme_content=result['readme_content'],
                    source=result['source'],
                    confidence_score=result['confidence_score'],
                    last_updated=result['last_updated'],
                    is_verified=result['is_verified'],
                    metadata=metadata
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"從數據庫獲取項目描述失敗: {e}")
            return None
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def _save_to_database(self, description: ProjectDescription) -> bool:
        """保存項目描述到數據庫"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 將metadata轉換為JSON字符串
            metadata_json = json.dumps(description.metadata) if description.metadata else None
            
            # 檢查是否已存在
            cur.execute("""
                SELECT id FROM project_descriptions 
                WHERE repository = %s
            """, (description.repository,))
            
            if cur.fetchone():
                # 更新現有記錄
                cur.execute("""
                    UPDATE project_descriptions SET
                        title = %s,
                        description = %s,
                        readme_content = %s,
                        source = %s,
                        confidence_score = %s,
                        last_updated = %s,
                        is_verified = %s,
                        metadata = %s
                    WHERE repository = %s
                """, (
                    description.title,
                    description.description,
                    description.readme_content,
                    description.source,
                    description.confidence_score,
                    description.last_updated,
                    description.is_verified,
                    metadata_json,
                    description.repository
                ))
            else:
                # 插入新記錄
                cur.execute("""
                    INSERT INTO project_descriptions (
                        id, repository, title, description, readme_content,
                        source, confidence_score, last_updated, is_verified, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    description.id,
                    description.repository,
                    description.title,
                    description.description,
                    description.readme_content,
                    description.source,
                    description.confidence_score,
                    description.last_updated,
                    description.is_verified,
                    metadata_json
                ))
            
            conn.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"保存項目描述到數據庫失敗: {e}")
            if 'conn' in locals():
                conn.rollback()
            return False
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_all_project_descriptions(self) -> List[ProjectDescription]:
        """獲取所有項目描述"""
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT * FROM project_descriptions 
                ORDER BY last_updated DESC
            """)
            
            results = cur.fetchall()
            descriptions = []
            
            for result in results:
                # 解析JSON metadata
                metadata = {}
                if result['metadata']:
                    try:
                        metadata = json.loads(result['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        metadata = {}
                
                descriptions.append(ProjectDescription(
                    id=result['id'],
                    repository=result['repository'],
                    title=result['title'],
                    description=result['description'],
                    readme_content=result['readme_content'],
                    source=result['source'],
                    confidence_score=result['confidence_score'],
                    last_updated=result['last_updated'],
                    is_verified=result['is_verified'],
                    metadata=metadata
                ))
            
            return descriptions
            
        except Exception as e:
            self.logger.error(f"獲取所有項目描述失敗: {e}")
            return []
        finally:
            if 'conn' in locals():
                return_db_connection(conn)
    
    def verify_project_description(self, repository: str, description: str) -> bool:
        """驗證項目描述是否準確"""
        try:
            # 獲取官方描述
            official_desc = self.get_project_description(repository)
            if not official_desc:
                return False
            
            # 簡單的相似度檢查(可以改進為更複雜的NLP比較)
            official_text = official_desc.description.lower()
            provided_text = description.lower()
            
            # 計算關鍵詞重疊度
            official_words = set(official_text.split())
            provided_words = set(provided_text.split())
            
            if len(official_words) == 0:
                return False
            
            overlap = len(official_words.intersection(provided_words))
            similarity = overlap / len(official_words)
            
            return similarity > 0.3  # 30%以上的重疊度認為是準確的
            
        except Exception as e:
            self.logger.error(f"驗證項目描述失敗: {e}")
            return False
