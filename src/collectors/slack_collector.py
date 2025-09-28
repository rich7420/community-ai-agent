"""
Slack資料收集器
基於auto-activity-report實現Slack資料收集功能
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import yaml
from utils.logging_config import structured_logger
from utils.pii_filter import PIIFilter
from storage.connection_pool import get_db_connection, return_db_connection

@dataclass
class SlackMessage:
    """Slack訊息資料結構"""
    ts: str
    text: str
    user: str
    channel: str
    thread_ts: Optional[str] = None
    reactions: List[Dict[str, Any]] = None
    attachments: List[Dict[str, Any]] = None
    files: List[Dict[str, Any]] = None
    replies: List[Dict[str, Any]] = None
    reply_count: int = 0
    metadata: Dict[str, Any] = None

class SlackCollector:
    """Slack資料收集器"""
    
    def __init__(self, bot_token: str, app_token: str):
        """
        初始化Slack收集器
        
        Args:
            bot_token: Slack Bot User OAuth Token
            app_token: Slack App Token
        """
        self.bot_client = WebClient(token=bot_token)
        self.app_client = WebClient(token=app_token)
        self.pii_filter = PIIFilter()
        self.logger = logging.getLogger(__name__)
        
        # 載入配置
        self.config = self._load_config()
        
        # 使用者快取
        self.user_cache = {}
        self._build_user_cache()
        self.channels = self.config.get('slack', {}).get('channels', [])
        
        # 收集統計
        self.stats = {
            'messages_collected': 0,
            'channels_processed': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """載入配置"""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'data_sources.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"載入配置失敗: {e}")
            return {}
    
    def _join_channel_if_needed(self, channel_id: str) -> bool:
        """
        嘗試加入頻道（如果需要）
        
        Args:
            channel_id: 頻道ID
            
        Returns:
            是否成功加入或已在頻道中
        """
        try:
            # 先嘗試直接加入頻道
            self.logger.info(f"嘗試加入頻道 {channel_id}...")
            join_response = self.bot_client.conversations_join(channel=channel_id)
            
            if join_response['ok']:
                self.logger.info(f"成功加入頻道 {channel_id}")
                return True
            else:
                error = join_response.get('error', 'Unknown error')
                if error == 'already_in_channel':
                    self.logger.info(f"Bot 已在頻道 {channel_id} 中")
                    return True
                else:
                    self.logger.warning(f"無法加入頻道 {channel_id}: {error}")
                    return False
                
        except Exception as e:
            self.logger.error(f"加入頻道時發生錯誤: {e}")
            return False

    def collect_channel_messages(self, channel_id: str, days_back: int = 7) -> List[SlackMessage]:
        """
        收集指定頻道的訊息（包含主訊息和回覆）
        
        Args:
            channel_id: 頻道ID
            days_back: 回溯天數
            
        Returns:
            訊息列表
        """
        messages = []
        start_time = time.time()
        
        try:
            # 先嘗試加入頻道
            if not self._join_channel_if_needed(channel_id):
                self.logger.warning(f"無法訪問頻道 {channel_id}，跳過收集")
                return messages
            
            # 獲取頻道資訊
            channel_info = self._get_channel_info(channel_id)
            
            # 計算時間範圍
            end_time = datetime.now()
            start_time_dt = end_time - timedelta(days=days_back)
            
            # 轉換為Slack時間戳
            oldest = start_time_dt.timestamp()
            latest = end_time.timestamp()
            
            self.logger.info(f"開始收集頻道 {channel_id} 的訊息，時間範圍: {start_time_dt} 到 {end_time}")
            
            # 收集主訊息和回覆
            messages = self._fetch_channel_messages_with_replies(channel_id, oldest, latest, channel_info)
            
            duration = time.time() - start_time
            self.logger.info(f"頻道 {channel_id} 收集完成，共 {len(messages)} 條訊息，耗時 {duration:.2f} 秒")
            
            # 記錄統計
            structured_logger.log_data_collection(
                platform='slack',
                records_count=len(messages),
                duration=duration,
                channel_id=channel_id
            )
            
        except Exception as e:
            self.logger.error(f"收集頻道 {channel_id} 訊息失敗: {e}")
            self.stats['errors'] += 1
        
        return messages
    
    def _fetch_channel_messages_with_replies(self, channel_id: str, oldest: float, latest: float, channel_info: Dict[str, str]) -> List[SlackMessage]:
        """收集頻道訊息和回覆"""
        messages = []
        
        # 分頁收集主訊息
        cursor = None
        while True:
            try:
                response = self.bot_client.conversations_history(
                    channel=channel_id,
                    oldest=str(oldest),
                    latest=str(latest),
                    cursor=cursor,
                    limit=1000,
                    inclusive=True
                )
                
                if not response['ok']:
                    self.logger.error(f"Slack API錯誤: {response['error']}")
                    break
                
                # 處理主訊息
                for msg in response['messages']:
                    if self._should_collect_message(msg):
                        slack_msg = self._parse_message(msg, channel_id, channel_info)
                        if slack_msg:
                            messages.append(slack_msg)
                        
                        # 收集回覆
                        thread_ts = msg.get('thread_ts')
                        if thread_ts and msg.get('reply_count', 0) > 0:
                            self.logger.info(f"主訊息 {msg['ts']} 有 {msg.get('reply_count', 0)} 個回覆，開始收集...")
                            thread_replies = self._collect_thread_replies_enhanced(channel_id, thread_ts, oldest, latest, channel_info)
                            messages.extend(thread_replies)
                
                # 檢查是否還有更多頁面
                if not response.get('has_more', False):
                    break
                
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                
                # 避免API限制
                time.sleep(5)
                
            except SlackApiError as e:
                if e.response['error'] == 'ratelimited':
                    wait_time = int(e.response['headers'].get('Retry-After', 5))
                    self.logger.warning(f"API限制，等待 {wait_time} 秒")
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(f"Slack API錯誤: {e}")
                    break
            except Exception as e:
                self.logger.error(f"收集訊息時發生錯誤: {e}")
                break
        
        return messages
    
    def _collect_thread_replies_enhanced(self, channel_id: str, thread_ts: str, oldest: float, latest: float, channel_info: Dict[str, str]) -> List[SlackMessage]:
        """收集線程回覆（增強版）"""
        replies = []
        
        try:
            self.logger.info(f"開始收集線程 {thread_ts} 的回覆")
            cursor = None
            
            while True:
                response = self.bot_client.conversations_replies(
                    channel=channel_id,
                    ts=thread_ts,
                    oldest=str(oldest),
                    latest=str(latest),
                    cursor=cursor,
                    limit=1000,
                    inclusive=True
                )
                
                if not response['ok']:
                    self.logger.error(f"收集回覆失敗: {response['error']}")
                    break
                
                # 跳過第一個訊息（主訊息），只收集回覆
                for reply_msg in response['messages'][1:]:
                    if self._should_collect_message(reply_msg):
                        slack_msg = self._parse_message(reply_msg, channel_id, channel_info)
                        if slack_msg:
                            replies.append(slack_msg)
                
                # 檢查是否還有更多頁面
                if not response.get('has_more', False):
                    break
                
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                
                # 避免API限制
                time.sleep(5)
            
            self.logger.info(f"線程 {thread_ts} 回覆收集完成，共 {len(replies)} 條回覆")
                        
        except Exception as e:
            self.logger.warning(f"收集線程 {thread_ts} 回覆失敗: {e}")
        
        return replies
    
    def _should_collect_message(self, msg: Dict[str, Any]) -> bool:
        """判斷是否應該收集此訊息"""
        # 過濾掉bot訊息（除非是我們自己的bot）
        if msg.get('bot_id') and not msg.get('app_id'):
            return False
        
        # 過濾掉系統訊息
        if msg.get('subtype') in ['channel_join', 'channel_leave', 'channel_topic', 'channel_purpose']:
            return False
        
        # 過濾掉空訊息
        if not msg.get('text', '').strip():
            return False
        
        return True
    
    def _parse_message(self, msg: Dict[str, Any], channel_id: str, channel_info: Dict[str, str] = None) -> Optional[SlackMessage]:
        """解析Slack訊息"""
        try:
            # 獲取使用者資訊
            user_id = msg.get('user', '')
            if user_id:
                user_info = self._get_user_info(user_id)
                # 使用真實使用者名稱，優先使用 real_name，其次使用 name
                real_name = user_info.get('real_name') or user_info.get('name') or 'Unknown User'
                
                # 匿名化使用者資訊
                anon_user = self.pii_filter.anonymize_user(user_id, real_name)
                
                # 添加用戶映射到映射表
                display_name = user_info.get('real_name') or user_info.get('name', 'Unknown User')
                self.pii_filter.add_user_mapping(
                    platform='slack',
                    original_user_id=user_id,
                    anonymized_id=anon_user,
                    display_name=display_name,
                    real_name=user_info.get('real_name'),
                    aliases=[user_info.get('name', '')] if user_info.get('name') else []
                )
            else:
                user_info = {'name': 'unknown', 'real_name': 'Unknown User'}
                real_name = 'Unknown User'
                anon_user = 'unknown'
            
            # 解析訊息內容
            text = msg.get('text', '')
            anon_text = self.pii_filter.anonymize_text(text)
            
            # 收集反應（使用真實使用者名稱）
            reactions = []
            if 'reactions' in msg:
                for reaction in msg['reactions']:
                    # 收集表情符號的真實使用者名稱
                    reaction_users = []
                    for uid in reaction.get('users', []):
                        if uid:
                            user_info = self._get_user_info(uid)
                            real_name = user_info.get('real_name') or user_info.get('name') or 'Unknown User'
                            reaction_users.append({
                                'user_id': uid,
                                'user_name': real_name,
                                'display_name': user_info.get('display_name', real_name)
                            })
                        else:
                            reaction_users.append({
                                'user_id': uid,
                                'user_name': 'Unknown User',
                                'display_name': 'Unknown User'
                            })
                    
                    reactions.append({
                        'emoji': reaction['name'],
                        'count': reaction['count'],
                        'users': reaction_users
                    })
            
            # 收集附件
            attachments = []
            if 'attachments' in msg:
                for attachment in msg['attachments']:
                    attachments.append({
                        'title': attachment.get('title', ''),
                        'text': self.pii_filter.anonymize_text(attachment.get('text', '')),
                        'fallback': attachment.get('fallback', '')
                    })
            
            # 收集文件
            files = []
            if 'files' in msg:
                for file in msg['files']:
                    files.append({
                        'name': file.get('name', ''),
                        'title': file.get('title', ''),
                        'filetype': file.get('filetype', ''),
                        'size': file.get('size', 0)
                    })
            
            # 收集線程回覆（如果這是主訊息且有回覆）
            thread_replies = []
            reply_count = msg.get('reply_count', 0)
            thread_ts = msg.get('thread_ts')
            
            self.logger.info(f"訊息 {msg['ts']}: reply_count={reply_count}, thread_ts={thread_ts}")
            
            if reply_count > 0:
                # 檢查這是否是主訊息還是回覆訊息
                # 主訊息：thread_ts 為 None 或者 thread_ts 等於 ts
                # 回覆訊息：thread_ts 不等於 ts
                if not thread_ts or thread_ts == msg['ts']:
                    # 這是主訊息，收集其回覆
                    self.logger.info(f"主訊息 {msg['ts']} 有 {reply_count} 個回覆，開始收集...")
                    thread_replies = self._collect_thread_replies(channel_id, msg['ts'])
                else:
                    self.logger.info(f"回覆訊息 {msg['ts']} 屬於線程 {thread_ts}")
                # 如果是回覆訊息（thread_ts 不等於 ts），我們不需要收集回覆，因為它本身就是回覆
            
            return SlackMessage(
                ts=msg['ts'],
                text=anon_text,
                user=real_name,  # 使用真實使用者名稱
                channel=channel_id,
                thread_ts=msg.get('thread_ts'),
                reactions=reactions,
                attachments=attachments,
                files=files,
                replies=thread_replies,
                reply_count=len(thread_replies),
                metadata={
                    'original_text': text,
                    'original_user': user_id,
                    'real_name': real_name,  # 添加真實使用者名稱
                    'user_info': user_info,  # 保留完整使用者資訊
                    'user_profile': user_info,  # 添加user_profile字段，與user_info相同
                    'user_name': user_info.get('name', ''),  # 添加user_name字段
                    'display_name': user_info.get('display_name', ''),  # 添加display_name字段
                    'channel': channel_id,  # 頻道ID
                    'channel_name': channel_info.get('name', 'unknown') if channel_info else 'unknown',  # 頻道名稱
                    'channel_info': channel_info,  # 完整頻道資訊
                    'subtype': msg.get('subtype'),
                    'has_thread': bool(msg.get('thread_ts')),
                    'reply_count': msg.get('reply_count', 0),
                    'reply_users_count': msg.get('reply_users_count', 0),
                    'is_edited': bool(msg.get('edited')),
                    'edit_count': msg.get('edit_count', 0),
                    'reactions': reactions,  # 完整的反應資訊
                    'attachments': attachments,  # 附件資訊
                    'files': files,  # 文件資訊
                    'thread_ts': msg.get('thread_ts'),  # 線程時間戳
                    'parent_user_id': msg.get('parent_user_id'),  # 父訊息用戶ID
                    'is_thread_reply': bool(msg.get('thread_ts') and msg.get('thread_ts') != msg.get('ts')),  # 是否為線程回覆
                    'message_type': 'thread_reply' if (msg.get('thread_ts') and msg.get('thread_ts') != msg.get('ts')) else 'main_message'  # 訊息類型
                }
            )
            
        except Exception as e:
            self.logger.error(f"解析訊息失敗: {e}")
            return None
    
    def _build_user_cache(self):
        """建立使用者快取，避免大量呼叫 users.info"""
        try:
            self.logger.info("開始建立使用者快取...")
            users = {}
            cursor = None
            
            while True:
                resp = self.bot_client.users_list(limit=200, cursor=cursor)
                if not resp['ok']:
                    self.logger.error(f"獲取使用者列表失敗: {resp.get('error', 'unknown error')}")
                    break
                
                for u in resp["members"]:
                    prof = u.get("profile", {})
                    users[u["id"]] = {
                        "display_name": prof.get("display_name") or prof.get("real_name") or u.get("name"),
                        "real_name": prof.get("real_name"),
                        "name": u.get("name"),
                        "deleted": u.get("deleted", False),
                        "is_bot": u.get("is_bot", False),
                        "email": prof.get("email", "")
                    }
                
                cursor = resp.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
                
                # 避免速率限制
                time.sleep(5)
            
            self.user_cache = users
            self.logger.info(f"使用者快取建立完成，共 {len(users)} 個使用者")
            
        except Exception as e:
            self.logger.error(f"建立使用者快取失敗: {e}")
            self.user_cache = {}
    
    def _get_channel_info(self, channel_id: str) -> Dict[str, str]:
        """獲取頻道資訊"""
        try:
            response = self.bot_client.conversations_info(channel=channel_id)
            if response['ok']:
                channel = response['channel']
                return {
                    'id': channel.get('id', channel_id),
                    'name': channel.get('name', 'unknown'),
                    'is_private': channel.get('is_private', False),
                    'is_archived': channel.get('is_archived', False),
                    'num_members': channel.get('num_members', 0)
                }
        except Exception as e:
            self.logger.warning(f"獲取頻道 {channel_id} 資訊失敗: {e}")
        
        return {
            'id': channel_id,
            'name': 'unknown',
            'is_private': False,
            'is_archived': False,
            'num_members': 0
        }

    def _get_user_info(self, user_id: str) -> Dict[str, str]:
        """從快取獲取使用者資訊"""
        if user_id in self.user_cache:
            user = self.user_cache[user_id]
            return {
                'name': user.get('name', ''),
                'real_name': user.get('real_name', ''),
                'display_name': user.get('display_name', ''),
                'email': user.get('email', '')
            }
        else:
            # 如果快取中沒有，嘗試從API獲取
            try:
                response = self.bot_client.users_info(user=user_id)
                if response['ok']:
                    user = response['user']
                    profile = user.get('profile', {})
                    user_info = {
                        'name': user.get('name', ''),
                        'real_name': profile.get('real_name', ''),
                        'display_name': profile.get('display_name', '') or profile.get('real_name', ''),
                        'email': profile.get('email', '')
                    }
                    # 更新快取
                    self.user_cache[user_id] = user_info
                    self.logger.info(f"從API獲取使用者資訊: {user_id} -> {user_info['real_name']}")
                    return user_info
                else:
                    self.logger.warning(f"無法獲取使用者資訊: {user_id}, 錯誤: {response.get('error')}")
            except Exception as e:
                self.logger.warning(f"獲取使用者資訊失敗: {user_id}, 錯誤: {e}")
            
            # 如果API也失敗，返回預設值
            self.logger.debug(f"使用者 {user_id} 不在快取中且API獲取失敗")
            return {
                'name': user_id, 
                'real_name': f'User {user_id}', 
                'display_name': user_id,
                'email': ''
            }
    
    def _collect_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """收集線程回覆"""
        replies = []
        
        try:
            self.logger.info(f"開始收集線程 {thread_ts} 的回覆")
            response = self.bot_client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1000
            )
            
            if response['ok']:
                total_messages = len(response['messages'])
                self.logger.info(f"線程 {thread_ts} 共有 {total_messages} 條訊息")
                
                # 跳過第一個訊息（主訊息），只收集回覆
                for reply_msg in response['messages'][1:]:
                    if self._should_collect_message(reply_msg):
                        # 獲取使用者資訊
                        user_id = reply_msg.get('user', '')
                        if user_id:
                            user_info = self._get_user_info(user_id)
                        else:
                            user_info = {'name': 'unknown', 'real_name': 'Unknown User'}
                        
                        # 匿名化使用者資訊
                        real_name = user_info.get('real_name') or user_info.get('name') or 'Unknown User'
                        anon_user = self.pii_filter.anonymize_user(user_id, real_name)
                        
                        # 添加用戶映射到映射表
                        display_name = user_info.get('real_name') or user_info.get('name', 'Unknown User')
                        self.pii_filter.add_user_mapping(
                            platform='slack',
                            original_user_id=user_id,
                            anonymized_id=anon_user,
                            display_name=display_name,
                            real_name=user_info.get('real_name'),
                            aliases=[user_info.get('name', '')] if user_info.get('name') else []
                        )
                        
                        # 解析回覆內容
                        text = reply_msg.get('text', '')
                        anon_text = self.pii_filter.anonymize_text(text)
                        
                        # 收集回覆的反應
                        reply_reactions = []
                        if 'reactions' in reply_msg:
                            for reaction in reply_msg['reactions']:
                                reply_reactions.append({
                                    'name': reaction['name'],
                                    'count': reaction['count'],
                                    'users': [self.pii_filter.anonymize_user(uid, 'Unknown User') for uid in reaction.get('users', [])]
                                })
                        
                        reply_data = {
                            'ts': reply_msg['ts'],
                            'text': anon_text,
                            'user': anon_user,
                            'user_profile': user_info,
                            'reactions': reply_reactions,
                            'metadata': {
                                'original_text': text,
                                'original_user': user_id,
                                'is_edited': bool(reply_msg.get('edited')),
                                'edit_count': reply_msg.get('edit_count', 0),
                                'thread_ts': thread_ts
                            }
                        }
                        replies.append(reply_data)
                
                self.logger.info(f"線程 {thread_ts} 回覆收集完成，共 {len(replies)} 條回覆")
                        
        except Exception as e:
            self.logger.warning(f"收集線程 {thread_ts} 回覆失敗: {e}")
        
        return replies
    
    def collect_all_channels(self, days_back: int = 7) -> List[SlackMessage]:
        """收集所有配置頻道的訊息"""
        all_messages = []
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"開始收集所有頻道訊息，回溯 {days_back} 天")
        
        for channel in self.channels:
            channel_id = channel.get('id')
            channel_name = channel.get('name', 'unknown')
            
            if not channel_id:
                self.logger.warning(f"頻道 {channel_name} 沒有ID，跳過")
                continue
            
            try:
                self.logger.info(f"收集頻道 {channel_name} ({channel_id})")
                messages = self.collect_channel_messages(channel_id, days_back)
                all_messages.extend(messages)
                self.stats['channels_processed'] += 1
                self.stats['messages_collected'] += len(messages)
                
                # 避免API限制 - 增加等待時間
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"收集頻道 {channel_name} 失敗: {e}")
                self.stats['errors'] += 1
                # 錯誤後等待更長時間
                time.sleep(15)
        
        self.stats['end_time'] = datetime.now()
        self.logger.info(f"所有頻道收集完成，共 {len(all_messages)} 條訊息")
        
        return all_messages
    
    def collect_bot_channels(self, days_back: int = 90) -> List[SlackMessage]:
        """
        收集 Bot 所在的所有頻道訊息（90天）
        
        Args:
            days_back: 回溯天數，預設90天
            
        Returns:
            訊息列表
        """
        all_messages = []
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"開始收集 Bot 所在頻道訊息，回溯 {days_back} 天")
        
        # 獲取 Bot 所在的所有頻道
        bot_channels = self._get_bot_channels()
        
        for channel_info in bot_channels:
            channel_id = channel_info['id']
            channel_name = channel_info['name']
            
            try:
                self.logger.info(f"收集頻道 {channel_name} ({channel_id})")
                messages = self.collect_channel_messages(channel_id, days_back)
                all_messages.extend(messages)
                self.stats['channels_processed'] += 1
                self.stats['messages_collected'] += len(messages)
                
                # 避免API限制
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"收集頻道 {channel_name} 失敗: {e}")
                self.stats['errors'] += 1
                time.sleep(5)
        
        self.stats['end_time'] = datetime.now()
        self.logger.info(f"Bot 頻道收集完成，共 {len(all_messages)} 條訊息")
        
        return all_messages
    
    def _get_bot_channels(self) -> List[Dict[str, Any]]:
        """獲取 Bot 所在的所有頻道"""
        channels = []
        
        try:
            # 獲取 Bot 用戶 ID
            auth_response = self.bot_client.auth_test()
            bot_user_id = auth_response['user_id']
            
            # 獲取所有頻道類型
            channel_types = ['public_channel', 'private_channel']
            
            for channel_type in channel_types:
                try:
                    # 分頁獲取頻道列表
                    cursor = None
                    while True:
                        response = self.bot_client.conversations_list(
                            types=channel_type,
                            limit=1000,
                            cursor=cursor,
                            exclude_archived=True
                        )
                        
                        if not response['ok']:
                            self.logger.error(f"獲取 {channel_type} 頻道失敗: {response['error']}")
                            break
                        
                        # 檢查 Bot 是否在頻道中
                        for channel in response['channels']:
                            channel_id = channel['id']
                            
                            # 檢查 Bot 是否在頻道中
                            if self._is_bot_in_channel(channel_id, bot_user_id):
                                channels.append({
                                    'id': channel_id,
                                    'name': channel.get('name', 'unknown'),
                                    'is_private': channel.get('is_private', False),
                                    'num_members': channel.get('num_members', 0)
                                })
                        
                        # 檢查是否還有更多頁面
                        cursor = response.get('response_metadata', {}).get('next_cursor')
                        if not cursor:
                            break
                        
                        time.sleep(5)  # 避免API限制
                        
                except Exception as e:
                    self.logger.warning(f"獲取 {channel_type} 頻道時發生錯誤: {e}")
                    continue
            
            self.logger.info(f"找到 {len(channels)} 個 Bot 所在的頻道")
            
        except Exception as e:
            self.logger.error(f"獲取 Bot 頻道失敗: {e}")
        
        return channels
    
    def _is_bot_in_channel(self, channel_id: str, bot_user_id: str) -> bool:
        """檢查 Bot 是否在頻道中"""
        try:
            # 對於小頻道，使用 conversations.members
            response = self.bot_client.conversations_members(
                channel=channel_id,
                limit=1000
            )
            
            if response['ok']:
                return bot_user_id in response.get('members', [])
            else:
                # 如果無法獲取成員列表，嘗試加入頻道來測試
                join_response = self.bot_client.conversations_join(channel=channel_id)
                return join_response['ok']
                
        except Exception as e:
            self.logger.debug(f"檢查頻道 {channel_id} 成員失敗: {e}")
            return False
    
    def collect_thread_replies(self, channel_id: str, thread_ts: str) -> List[SlackMessage]:
        """收集thread回覆"""
        replies = []
        
        try:
            response = self.bot_client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=1000
            )
            
            if response['ok']:
                for msg in response['messages'][1:]:  # 跳過原始訊息
                    if self._should_collect_message(msg):
                        slack_msg = self._parse_message(msg, channel_id)
                        if slack_msg:
                            replies.append(slack_msg)
            
        except Exception as e:
            self.logger.error(f"收集thread回覆失敗: {e}")
        
        return replies
    
    def collect_user_activity(self, days_back: int = 7) -> Dict[str, Any]:
        """收集使用者活躍度統計"""
        activity_stats = {}
        
        try:
            # 獲取所有使用者
            response = self.bot_client.users_list()
            if not response['ok']:
                return activity_stats
            
            users = response['members']
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)
            
            for user in users:
                user_id = user['id']
                if user.get('deleted') or user.get('is_bot'):
                    continue
                
                # 統計訊息數量
                message_count = 0
                for channel in self.channels:
                    channel_id = channel.get('id')
                    if channel_id:
                        messages = self.collect_channel_messages(channel_id, days_back)
                        user_messages = [msg for msg in messages if msg.metadata.get('original_user') == user_id]
                        message_count += len(user_messages)
                
                activity_stats[user_id] = {
                    'name': user.get('name', ''),
                    'real_name': user.get('real_name', ''),
                    'message_count': message_count,
                    'is_active': message_count > 0
                }
        
        except Exception as e:
            self.logger.error(f"收集使用者活躍度失敗: {e}")
        
        return activity_stats
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """獲取收集統計"""
        return self.stats.copy()

