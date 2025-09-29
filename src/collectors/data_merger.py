"""
資料整合與清理模組
實現多源資料合併、格式標準化、資料驗證等功能
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
import json
import re
from utils.logging_config import structured_logger
from utils.pii_filter import PIIFilter

@dataclass
class StandardizedRecord:
    """標準化記錄格式"""
    id: str
    platform: str
    content: str
    author: str
    timestamp: datetime
    source_url: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DataMerger:
    """資料整合器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pii_filter = PIIFilter()
        
        # 資料驗證規則
        self.validation_rules = {
            'required_fields': ['id', 'platform', 'content', 'author', 'timestamp'],
            'max_content_length': 100000,  # 增加到 100KB，支援大型文件
            'max_metadata_size': 50000,  # 字節
            'allowed_platforms': ['slack', 'github', 'facebook', 'google_calendar']
        }
    
    def merge_slack_data(self, messages: List[Dict[str, Any]]) -> List[StandardizedRecord]:
        """
        合併Slack資料
        
        Args:
            messages: Slack訊息列表
            
        Returns:
            標準化記錄列表
        """
        records = []
        
        for msg in messages:
            try:
                # 驗證資料
                if not self._validate_slack_message(msg):
                    continue
                
                # 轉換為標準格式
                record = self._convert_slack_to_standard(msg)
                if record:
                    records.append(record)
                    
            except Exception as e:
                self.logger.error(f"處理Slack訊息失敗: {e}")
                continue
        
        self.logger.info(f"Slack資料合併完成，共 {len(records)} 條記錄")
        return records
    
    def merge_github_data(self, issues: List[Dict[str, Any]], 
                         prs: List[Dict[str, Any]], 
                         commits: List[Dict[str, Any]],
                         files: List[Dict[str, Any]] = None) -> List[StandardizedRecord]:
        """
        合併GitHub資料
        
        Args:
            issues: Issues列表
            prs: Pull Requests列表
            commits: Commits列表
            files: Files列表（包括README等文件）
            
        Returns:
            標準化記錄列表
        """
        records = []
        
        # 處理Issues
        for issue in issues:
            try:
                if self._validate_github_issue(issue):
                    record = self._convert_github_issue_to_standard(issue)
                    if record:
                        records.append(record)
            except Exception as e:
                self.logger.error(f"處理GitHub Issue失敗: {e}")
                continue
        
        # 處理Pull Requests
        for pr in prs:
            try:
                if self._validate_github_pr(pr):
                    record = self._convert_github_pr_to_standard(pr)
                    if record:
                        records.append(record)
            except Exception as e:
                self.logger.error(f"處理GitHub PR失敗: {e}")
                continue
        
        # 處理Commits
        for commit in commits:
            try:
                if self._validate_github_commit(commit):
                    record = self._convert_github_commit_to_standard(commit)
                    if record:
                        records.append(record)
            except Exception as e:
                self.logger.error(f"處理GitHub Commit失敗: {e}")
                continue
        
        # 處理Files
        if files:
            for file_data in files:
                try:
                    if self._validate_github_file(file_data):
                        record = self._convert_github_file_to_standard(file_data)
                        if record:
                            records.append(record)
                except Exception as e:
                    self.logger.error(f"處理GitHub File失敗: {e}")
                    continue
        
        self.logger.info(f"GitHub資料合併完成，共 {len(records)} 條記錄")
        return records
    
    def merge_facebook_data(self, posts: List[Dict[str, Any]]) -> List[StandardizedRecord]:
        """
        合併Facebook資料
        
        Args:
            posts: Facebook貼文列表
            
        Returns:
            標準化記錄列表
        """
        records = []
        
        for post in posts:
            try:
                if self._validate_facebook_post(post):
                    record = self._convert_facebook_to_standard(post)
                    if record:
                        records.append(record)
            except Exception as e:
                self.logger.error(f"處理Facebook貼文失敗: {e}")
                continue
        
        self.logger.info(f"Facebook資料合併完成，共 {len(records)} 條記錄")
        return records
    
    def merge_google_calendar_data(self, events: List[Any]) -> List[StandardizedRecord]:
        """
        合併Google Calendar資料
        
        Args:
            events: Google Calendar事件列表 (CalendarEvent對象)
            
        Returns:
            標準化記錄列表
        """
        records = []
        
        for event in events:
            try:
                # 構建事件內容
                content_parts = [
                    f"事件標題: {event.title}",
                    f"開始時間: {event.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"結束時間: {event.end_time.strftime('%Y-%m-%d %H:%M:%S')}"
                ]
                
                if event.description:
                    content_parts.append(f"描述: {event.description}")
                
                if event.location:
                    content_parts.append(f"地點: {event.location}")
                
                if event.attendees:
                    attendee_names = [att.get('display_name', att.get('email', '')) for att in event.attendees if att.get('display_name') or att.get('email')]
                    if attendee_names:
                        content_parts.append(f"參與者: {', '.join(attendee_names)}")
                
                if event.creator_email:
                    content_parts.append(f"創建者: {event.creator_email}")
                
                if event.organizer_email:
                    content_parts.append(f"組織者: {event.organizer_email}")
                
                content = "\n".join(content_parts)
                
                # 構建元數據
                metadata = {
                    'event_id': event.id,
                    'calendar_id': event.calendar_id,
                    'status': event.status,
                    'visibility': event.visibility,
                    'recurrence': event.recurrence,
                    'source_url': event.source_url,
                    'attendees_count': len(event.attendees),
                    'is_recurring': bool(event.recurrence),
                    'event_type': 'calendar_event'
                }
                
                # 創建標準化記錄
                record = StandardizedRecord(
                    id=f"calendar_{event.id}",
                    platform='google_calendar',
                    content=content,
                    author=event.creator_email or event.organizer_email or 'unknown',
                    timestamp=event.start_time,
                    source_url=event.source_url or '',
                    metadata=metadata,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                records.append(record)
                
            except Exception as e:
                self.logger.error(f"合併Google Calendar事件失敗 {event.id}: {e}")
                continue
        
        self.logger.info(f"Google Calendar資料合併完成，共 {len(records)} 條記錄")
        return records
    
    def merge_all_data(self, slack_data: List[Dict[str, Any]] = None,
                      github_data: Dict[str, List[Dict[str, Any]]] = None,
                      facebook_data: List[Dict[str, Any]] = None,
                      calendar_data: List[Any] = None) -> List[StandardizedRecord]:
        """
        合併所有資料源
        
        Args:
            slack_data: Slack資料
            github_data: GitHub資料 {'issues': [], 'prs': [], 'commits': []}
            facebook_data: Facebook資料
            calendar_data: Google Calendar事件資料
            
        Returns:
            標準化記錄列表
        """
        all_records = []
        
        # 合併Slack資料
        if slack_data:
            slack_records = self.merge_slack_data(slack_data)
            all_records.extend(slack_records)
        
        # 合併GitHub資料
        if github_data:
            github_records = self.merge_github_data(
                github_data.get('issues', []),
                github_data.get('prs', []),
                github_data.get('commits', []),
                github_data.get('files', [])
            )
            all_records.extend(github_records)
        
        # 合併Facebook資料
        if facebook_data:
            facebook_records = self.merge_facebook_data(facebook_data)
            all_records.extend(facebook_records)
        
        # 合併Google Calendar資料
        if calendar_data:
            calendar_records = self.merge_google_calendar_data(calendar_data)
            all_records.extend(calendar_records)
        
        # 資料清理和驗證
        cleaned_records = self._clean_and_validate_records(all_records)
        
        self.logger.info(f"所有資料合併完成，共 {len(cleaned_records)} 條記錄")
        return cleaned_records
    
    def save_record(self, record: StandardizedRecord) -> bool:
        """
        保存標準化記錄到數據庫
        
        Args:
            record: 標準化記錄
            
        Returns:
            是否保存成功
        """
        try:
            from storage.connection_pool import get_db_connection, return_db_connection
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 插入或更新記錄
            cur.execute("""
                INSERT INTO community_data (
                    id, platform, content, author_anon, timestamp, source_url, metadata, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    author_anon = EXCLUDED.author_anon,
                    timestamp = EXCLUDED.timestamp,
                    source_url = EXCLUDED.source_url,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
            """, (
                record.id,
                record.platform,
                record.content,
                record.author,
                record.timestamp,
                record.source_url,
                json.dumps(record.metadata),
                record.created_at or datetime.now(),
                record.updated_at or datetime.now()
            ))
            
            conn.commit()
            cur.close()
            return_db_connection(conn)
            
            return True
            
        except Exception as e:
            self.logger.error(f"保存記錄失敗: {e}")
            if 'conn' in locals():
                conn.rollback()
                return_db_connection(conn)
            return False
    
    def _validate_slack_message(self, msg) -> bool:
        """驗證Slack訊息"""
        # 處理 SlackMessage 對象或字典
        if hasattr(msg, 'text'):
            # SlackMessage 對象
            if not msg.text or not msg.user or not msg.channel:
                return False
            if len(msg.text) > self.validation_rules['max_content_length']:
                return False
        else:
            # 字典格式
            required_fields = ['ts', 'text', 'user', 'channel']
            for field in required_fields:
                if field not in msg or not msg[field]:
                    return False
            if len(msg['text']) > self.validation_rules['max_content_length']:
                return False
        
        return True
    
    def _validate_github_issue(self, issue: Dict[str, Any]) -> bool:
        """驗證GitHub Issue"""
        required_fields = ['number', 'title', 'body', 'user', 'created_at']
        
        for field in required_fields:
            if field not in issue:
                return False
        
        return True
    
    def _validate_github_pr(self, pr: Dict[str, Any]) -> bool:
        """驗證GitHub PR"""
        required_fields = ['number', 'title', 'body', 'user', 'created_at']
        
        for field in required_fields:
            if field not in pr:
                return False
        
        return True
    
    def _validate_github_commit(self, commit) -> bool:
        """驗證GitHub Commit"""
        # 處理 GitHubCommit 對象或字典
        if hasattr(commit, 'sha'):
            # GitHubCommit 對象
            if not commit.sha or not commit.message or not commit.author:
                return False
        else:
            # 字典格式
            required_fields = ['sha', 'message', 'author', 'created_at']
            for field in required_fields:
                if field not in commit:
                    return False
        
        return True
    
    def _validate_facebook_post(self, post: Dict[str, Any]) -> bool:
        """驗證Facebook貼文"""
        required_fields = ['id', 'message', 'from', 'created_time']
        
        for field in required_fields:
            if field not in post:
                return False
        
        return True
    
    def _convert_slack_to_standard(self, msg) -> Optional[StandardizedRecord]:
        """將Slack訊息轉換為標準格式"""
        try:
            # 處理 SlackMessage 對象或字典
            if hasattr(msg, 'channel'):
                # SlackMessage 對象
                record_id = f"slack_{msg.channel}_{msg.ts}"
                timestamp = datetime.fromtimestamp(float(msg.ts))
                source_url = f"https://slack.com/channels/{msg.channel}/{msg.ts}"
                metadata = {
                    'original_ts': msg.ts,
                    'channel': msg.channel,
                    'thread_ts': getattr(msg, 'thread_ts', None),
                    'reactions': getattr(msg, 'reactions', []),
                    'attachments': getattr(msg, 'attachments', []),
                    'files': getattr(msg, 'files', []),
                    'user_profile': getattr(msg, 'user_profile', {}),
                    'bot_id': getattr(msg, 'bot_id', None),
                    'subtype': getattr(msg, 'subtype', None),
                }
                
                # 添加用戶信息到metadata
                if hasattr(msg, 'metadata') and msg.metadata:
                    metadata.update({
                        'real_name': msg.metadata.get('real_name'),
                        'display_name': msg.metadata.get('display_name'),
                        'user_name': msg.metadata.get('user_name'),
                        'name': msg.metadata.get('name'),
                        'user_info': msg.metadata.get('user_info'),
                        'original_user': msg.metadata.get('original_user'),
                    })
                content = msg.text
                # 使用匿名化的用戶ID，從metadata中獲取真實用戶名稱
                user_name = ''
                if hasattr(msg, 'metadata') and msg.metadata:
                    user_name = (msg.metadata.get('real_name') or 
                               msg.metadata.get('display_name') or 
                               msg.metadata.get('user_name') or 
                               msg.metadata.get('name', ''))
                author = self.pii_filter.anonymize_user(msg.user, user_name)
            else:
                # 字典格式
                record_id = f"slack_{msg['channel']}_{msg['ts']}"
                timestamp = datetime.fromtimestamp(float(msg['ts']))
                source_url = f"https://slack.com/channels/{msg['channel']}/{msg['ts']}"
                metadata = {
                    'original_ts': msg['ts'],
                    'channel': msg['channel'],
                    'thread_ts': msg.get('thread_ts'),
                    'reactions': msg.get('reactions', []),
                    'attachments': msg.get('attachments', []),
                    'files': msg.get('files', []),
                'subtype': msg.get('subtype'),
                'has_thread': bool(msg.get('thread_ts')),
                'reply_count': msg.get('reply_count', 0)
                }
                content = msg['text']
                # 使用匿名化的用戶ID
                author = self.pii_filter.anonymize_user(msg['user'], msg.get('user_name', ''))
            
            return StandardizedRecord(
                id=record_id,
                platform='slack',
                content=content,
                author=author,
                timestamp=timestamp,
                source_url=source_url,
                metadata=metadata,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"轉換Slack訊息失敗: {e}")
            return None
    
    def _convert_github_issue_to_standard(self, issue: Dict[str, Any]) -> Optional[StandardizedRecord]:
        """將GitHub Issue轉換為標準格式"""
        try:
            record_id = f"github_issue_{issue['number']}"
            
            # 轉換時間戳
            timestamp = issue['created_at']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # 構建內容
            content = f"{issue['title']}\n\n{issue['body'] or ''}"
            
            # 構建來源URL
            source_url = issue.get('url', '')
            
            # 構建元資料
            metadata = {
                'type': 'issue',
                'number': issue['number'],
                'state': issue['state'],
                'labels': issue.get('labels', []),
                'assignees': issue.get('assignees', []),
                'comments_count': issue.get('comments_count', 0),
                'closed_at': issue.get('closed_at'),
                'updated_at': issue.get('updated_at')
            }
            
            return StandardizedRecord(
                id=record_id,
                platform='github',
                content=content,
                author=issue['author'],
                timestamp=timestamp,
                source_url=source_url,
                metadata=metadata,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"轉換GitHub Issue失敗: {e}")
            return None
    
    def _convert_github_pr_to_standard(self, pr: Dict[str, Any]) -> Optional[StandardizedRecord]:
        """將GitHub PR轉換為標準格式"""
        try:
            record_id = f"github_pr_{pr['number']}"
            
            # 轉換時間戳
            timestamp = pr['created_at']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # 構建內容
            content = f"{pr['title']}\n\n{pr['body'] or ''}"
            
            # 構建來源URL
            source_url = pr.get('url', '')
            
            # 構建元資料
            metadata = {
                'type': 'pull_request',
                'number': pr['number'],
                'state': pr['state'],
                'labels': pr.get('labels', []),
                'assignees': pr.get('assignees', []),
                'reviewers': pr.get('reviewers', []),
                'comments_count': pr.get('comments_count', 0),
                'review_comments_count': pr.get('review_comments_count', 0),
                'commits_count': pr.get('commits_count', 0),
                'additions': pr.get('additions', 0),
                'deletions': pr.get('deletions', 0),
                'merged_at': pr.get('merged_at'),
                'closed_at': pr.get('closed_at')
            }
            
            return StandardizedRecord(
                id=record_id,
                platform='github',
                content=content,
                author=pr['author'],
                timestamp=timestamp,
                source_url=source_url,
                metadata=metadata,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"轉換GitHub PR失敗: {e}")
            return None
    
    def _convert_github_commit_to_standard(self, commit) -> Optional[StandardizedRecord]:
        """將GitHub Commit轉換為標準格式"""
        try:
            # 處理 GitHubCommit 對象或字典
            if hasattr(commit, 'sha'):
                # GitHubCommit 對象
                record_id = f"github_commit_{commit.sha}"
                timestamp = commit.created_at
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                content = commit.message
                source_url = getattr(commit, 'url', '')
                author = getattr(commit.author, 'login', 'unknown') if hasattr(commit, 'author') else 'unknown'
                sha = commit.sha
                committer = getattr(commit.committer, 'login', 'unknown') if hasattr(commit, 'committer') else 'unknown'
            else:
                # 字典格式
                record_id = f"github_commit_{commit['sha']}"
                timestamp = commit['created_at']
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                content = commit['message']
                source_url = commit.get('url', '')
                author = commit['author']
                sha = commit['sha']
                committer = commit.get('committer')
            
            # 構建元資料
            if hasattr(commit, 'sha'):
                # GitHubCommit 對象
                metadata = {
                    'type': 'commit',
                    'sha': sha,
                    'committer': committer,
                    'additions': getattr(commit, 'additions', 0),
                    'deletions': getattr(commit, 'deletions', 0),
                    'files_changed': getattr(commit, 'files_changed', []),
                    'verification': getattr(commit, 'verification', False)
                }
            else:
                # 字典格式
                metadata = {
                    'type': 'commit',
                    'sha': sha,
                    'committer': committer,
                    'additions': commit.get('additions', 0),
                    'deletions': commit.get('deletions', 0),
                    'files_changed': commit.get('files_changed', []),
                    'verification': commit.get('metadata', {}).get('verification', False)
                }
            
            return StandardizedRecord(
                id=record_id,
                platform='github',
                content=content,
                author=author,
                timestamp=timestamp,
                source_url=source_url,
                metadata=metadata,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"轉換GitHub Commit失敗: {e}")
            return None
    
    def _convert_facebook_to_standard(self, post: Dict[str, Any]) -> Optional[StandardizedRecord]:
        """將Facebook貼文轉換為標準格式"""
        try:
            record_id = f"facebook_{post['id']}"
            
            # 轉換時間戳
            timestamp = post['created_time']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            # 構建內容
            content = post.get('message', '')
            
            # 構建來源URL
            source_url = post.get('permalink_url', '')
            
            # 構建元資料
            metadata = {
                'type': 'post',
                'post_id': post['id'],
                'from': post.get('from', {}),
                'likes_count': post.get('likes', {}).get('summary', {}).get('total_count', 0),
                'comments_count': post.get('comments', {}).get('summary', {}).get('total_count', 0),
                'shares_count': post.get('shares', {}).get('count', 0),
                'updated_time': post.get('updated_time')
            }
            
            return StandardizedRecord(
                id=record_id,
                platform='facebook',
                content=content,
                author=post['from'].get('name', 'Unknown'),
                timestamp=timestamp,
                source_url=source_url,
                metadata=metadata,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"轉換Facebook貼文失敗: {e}")
            return None
    
    def _clean_and_validate_records(self, records: List[StandardizedRecord]) -> List[StandardizedRecord]:
        """清理和驗證記錄"""
        cleaned_records = []
        
        for record in records:
            try:
                # 驗證必需字段
                if not self._validate_standard_record(record):
                    continue
                
                # 清理內容
                record.content = self._clean_content(record.content)
                
                # 清理元資料
                record.metadata = self._clean_metadata(record.metadata)
                
                cleaned_records.append(record)
                
            except Exception as e:
                self.logger.error(f"清理記錄失敗: {e}")
                continue
        
        self.logger.info(f"記錄清理完成: {len(records)} -> {len(cleaned_records)}")
        return cleaned_records
    
    def _validate_standard_record(self, record: StandardizedRecord) -> bool:
        """驗證標準記錄"""
        # 檢查必需字段
        for field in self.validation_rules['required_fields']:
            if not getattr(record, field, None):
                return False
        
        # 檢查平台
        if record.platform not in self.validation_rules['allowed_platforms']:
            return False
        
        # 檢查內容長度
        if len(record.content) > self.validation_rules['max_content_length']:
            return False
        
        return True
    
    def _clean_content(self, content: str) -> str:
        """清理內容"""
        if not content:
            return content
        
        # 移除多餘的空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 移除HTML標籤（如果有）
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除特殊字符
        content = re.sub(r'[^\w\s.,!?;:()\-]', '', content)
        
        return content.strip()
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """清理元資料"""
        # 移除過大的元資料
        metadata_str = json.dumps(metadata)
        if len(metadata_str) > self.validation_rules['max_metadata_size']:
            # 保留最重要的字段
            cleaned_metadata = {
                'type': metadata.get('type'),
                'original_id': metadata.get('original_id'),
                'platform_specific_id': metadata.get('number') or metadata.get('sha') or metadata.get('post_id')
            }
            return cleaned_metadata
        
        return metadata
    
    def _validate_github_file(self, file_data) -> bool:
        """驗證GitHub文件資料"""
        try:
            # 處理 dataclass 對象或字典
            if hasattr(file_data, '__dict__'):
                # GitHubFile dataclass 對象
                path = file_data.path
                content = file_data.content
                sha = file_data.sha
                is_binary = file_data.metadata.get('is_binary', False) if hasattr(file_data, 'metadata') else False
            else:
                # 字典格式
                path = file_data.get('path', '')
                content = file_data.get('content', '')
                sha = file_data.get('sha', '')
                is_binary = file_data.get('is_binary', False)
            
            # 檢查必要字段
            if not path or not content or not sha:
                return False
            
            # 檢查內容長度
            if len(content) > self.validation_rules['max_content_length']:
                self.logger.warning(f"文件內容過長，跳過: {path}")
                return False
            
            # 檢查是否為二進制文件
            if is_binary:
                self.logger.info(f"跳過二進制文件: {path}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"驗證GitHub文件失敗: {e}")
            return False
    
    def _convert_github_file_to_standard(self, file_data) -> Optional[StandardizedRecord]:
        """將GitHub文件轉換為標準格式"""
        try:
            # 處理 dataclass 對象或字典
            if hasattr(file_data, '__dict__'):
                # GitHubFile dataclass 對象
                sha = file_data.sha
                content = file_data.content
                path = file_data.path
                author = file_data.author
                last_modified = file_data.last_modified
                url = file_data.url
                size = file_data.size
                metadata = file_data.metadata
            else:
                # 字典格式
                sha = file_data.get('sha', '')
                content = file_data.get('content', '')
                path = file_data.get('path', '')
                author = file_data.get('author', 'unknown')
                last_modified = file_data.get('last_modified', datetime.now())
                url = file_data.get('url', '')
                size = file_data.get('size', 0)
                metadata = file_data.get('metadata', {})
            
            # 生成唯一ID
            record_id = f"github_file_{sha}"
            
            # 構建內容（包含路徑信息）
            if path:
                formatted_content = f"文件路徑: {path}\n\n{content}"
            else:
                formatted_content = content
            
            # 構建元資料
            file_metadata = {
                'type': 'file',
                'path': path,
                'sha': sha,
                'size': size,
                'file_type': metadata.get('file_type', 'unknown'),
                'importance_score': metadata.get('importance_score', 0),
                'directory': metadata.get('directory', ''),
                'repository': metadata.get('repository', ''),
                'encoding': metadata.get('encoding', 'utf-8')
            }
            
            return StandardizedRecord(
                id=record_id,
                platform='github',
                content=formatted_content,
                author=author,
                timestamp=last_modified,
                source_url=url,
                metadata=file_metadata,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"轉換GitHub文件失敗: {e}")
            return None