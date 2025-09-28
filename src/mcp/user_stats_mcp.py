"""
用戶統計MCP (Model Context Protocol)
用於統計Slack用戶的活動數據，包括發訊息、回覆、給emoji等
"""
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from storage.connection_pool import get_db_connection, return_db_connection

logger = logging.getLogger(__name__)

@dataclass
class UserStats:
    """用戶統計數據結構"""
    user_id: str
    user_name: str
    message_count: int = 0
    reply_count: int = 0
    emoji_given_count: int = 0
    emoji_received_count: int = 0
    thread_count: int = 0
    channel_count: int = 0
    last_activity: Optional[datetime] = None
    channels: List[str] = None
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = []

class UserStatsMCP:
    """用戶統計MCP"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_user_stats(self, 
                      platform: str = "slack",
                      days_back: int = 90,
                      limit: int = 10) -> List[UserStats]:
        """
        獲取用戶統計數據
        
        Args:
            platform: 平台名稱 (slack, github等)
            days_back: 回溯天數
            limit: 返回結果數量限制
            
        Returns:
            用戶統計數據列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 計算時間範圍
            start_date = datetime.now() - timedelta(days=days_back)
            
            # 查詢用戶統計數據
            query = """
            SELECT 
                author_anon as user_name,
                COUNT(*) as message_count,
                COUNT(CASE WHEN metadata->>'thread_ts' IS NOT NULL THEN 1 END) as reply_count,
                MAX(timestamp) as last_activity,
                COUNT(DISTINCT metadata->>'channel') as channel_count,
                array_agg(DISTINCT metadata->>'channel') as channels
            FROM community_data 
            WHERE platform = %s 
                AND timestamp >= %s
                AND author_anon IS NOT NULL
            GROUP BY author_anon
            ORDER BY message_count DESC
            LIMIT %s
            """
            
            cur.execute(query, (platform, start_date, limit))
            results = cur.fetchall()
            
            user_stats = []
            for row in results:
                anonymized_id, message_count, reply_count, last_activity, channel_count, channels = row
                
                # 嘗試獲取真實用戶名稱
                from src.utils.pii_filter import PIIFilter
                pii_filter = PIIFilter()
                display_name = pii_filter._get_display_name_by_original_id(anonymized_id, platform)
                user_name = display_name if display_name else anonymized_id
                
                # 計算emoji統計
                emoji_stats = self._get_emoji_stats(cur, anonymized_id, platform, start_date)
                
                stats = UserStats(
                    user_id=anonymized_id,  # 使用anonymized_id作為ID
                    user_name=user_name,    # 使用顯示名稱
                    message_count=message_count or 0,
                    reply_count=reply_count or 0,
                    emoji_given_count=emoji_stats['given'],
                    emoji_received_count=emoji_stats['received'],
                    thread_count=0,  # 可以後續實現
                    channel_count=channel_count or 0,
                    last_activity=last_activity,
                    channels=channels or []
                )
                user_stats.append(stats)
            
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"獲取到 {len(user_stats)} 個用戶的統計數據")
            return user_stats
            
        except Exception as e:
            self.logger.error(f"獲取用戶統計數據失敗: {e}")
            return []
    
    def _get_emoji_stats(self, cur, user_name: str, platform: str, start_date: datetime) -> Dict[str, int]:
        """獲取用戶emoji統計"""
        try:
            # 查詢用戶給出的emoji
            given_query = """
            SELECT COUNT(*) 
            FROM community_data 
            WHERE platform = %s 
                AND timestamp >= %s
                AND author_anon = %s
                AND metadata->'reactions' IS NOT NULL
            """
            cur.execute(given_query, (platform, start_date, user_name))
            given_count = cur.fetchone()[0] or 0
            
            # 查詢用戶收到的emoji（需要解析reactions中的users）
            received_query = """
            SELECT metadata->'reactions'
            FROM community_data 
            WHERE platform = %s 
                AND timestamp >= %s
                AND metadata->'reactions' IS NOT NULL
            """
            cur.execute(received_query, (platform, start_date))
            
            received_count = 0
            for row in cur.fetchall():
                reactions = row[0]
                if isinstance(reactions, list):
                    for reaction in reactions:
                        if isinstance(reaction, dict) and 'users' in reaction:
                            users = reaction.get('users', [])
                            if user_name in users:
                                received_count += 1
            
            return {
                'given': given_count,
                'received': received_count
            }
            
        except Exception as e:
            self.logger.error(f"獲取emoji統計失敗: {e}")
            return {'given': 0, 'received': 0}
    
    def get_top_active_users(self, 
                           platform: str = "slack",
                           days_back: int = 90,
                           limit: int = 3) -> List[Dict[str, Any]]:
        """
        獲取最活躍的前N個用戶
        
        Args:
            platform: 平台名稱
            days_back: 回溯天數
            limit: 返回數量
            
        Returns:
            最活躍用戶列表
        """
        user_stats = self.get_user_stats(platform, days_back, limit)
        
        result = []
        for stats in user_stats:
            result.append({
                'user_name': stats.user_name,
                'message_count': stats.message_count,
                'reply_count': stats.reply_count,
                'emoji_given': stats.emoji_given_count,
                'emoji_received': stats.emoji_received_count,
                'channel_count': stats.channel_count,
                'last_activity': stats.last_activity.isoformat() if stats.last_activity else None,
                'channels': stats.channels,
                'total_score': stats.message_count + stats.reply_count + stats.emoji_given_count
            })
        
        return result
    
    def get_user_activity_summary(self, 
                                platform: str = "slack",
                                days_back: int = 90) -> Dict[str, Any]:
        """
        獲取用戶活動摘要
        
        Args:
            platform: 平台名稱
            days_back: 回溯天數
            
        Returns:
            活動摘要
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            start_date = datetime.now() - timedelta(days=days_back)
            
            # 總體統計 - 分開查詢避免子查詢問題
            # 1. 用戶和訊息統計
            user_message_query = """
            SELECT 
                COUNT(DISTINCT author_anon) as total_users,
                COUNT(*) as total_messages
            FROM community_data 
            WHERE platform = %s 
                AND timestamp >= %s
                AND author_anon IS NOT NULL
            """
            
            cur.execute(user_message_query, (platform, start_date))
            user_message_result = cur.fetchone()
            
            # 2. 頻道統計
            channel_query = """
            SELECT COUNT(DISTINCT metadata->>'channel') as total_channels
            FROM community_data 
            WHERE platform = %s 
                AND timestamp >= %s
                AND metadata->>'channel' IS NOT NULL
            """
            
            cur.execute(channel_query, (platform, start_date))
            channel_result = cur.fetchone()
            
            # 3. 平均訊息數
            avg_query = """
            SELECT ROUND(AVG(message_count), 2) as avg_messages_per_user
            FROM (
                SELECT COUNT(*) as message_count
                FROM community_data 
                WHERE platform = %s 
                    AND timestamp >= %s
                    AND author_anon IS NOT NULL
                GROUP BY author_anon
            ) user_counts
            """
            
            cur.execute(avg_query, (platform, start_date))
            avg_result = cur.fetchone()
            
            # 合併結果
            total_users = user_message_result[0] if user_message_result else 0
            total_messages = user_message_result[1] if user_message_result else 0
            total_channels = channel_result[0] if channel_result else 0
            avg_messages = avg_result[0] if avg_result else 0
            
            cur.close()
            return_db_connection(conn)
            
            return {
                'total_users': total_users,
                'total_messages': total_messages,
                'total_channels': total_channels,
                'avg_messages_per_user': avg_messages,
                'period_days': days_back,
                'platform': platform
            }
                
        except Exception as e:
            self.logger.error(f"獲取活動摘要失敗: {e}")
            return {
                'total_users': 0,
                'total_messages': 0,
                'total_channels': 0,
                'avg_messages_per_user': 0,
                'period_days': days_back,
                'platform': platform
            }
    
    def get_multi_platform_summary(self, days_back: int = 90) -> Dict[str, Any]:
        """
        獲取多平台活動摘要
        
        Args:
            days_back: 回溯天數
            
        Returns:
            多平台活動摘要
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            start_date = datetime.now() - timedelta(days=days_back)
            
            # 查詢各平台統計
            platform_query = """
            SELECT 
                platform,
                COUNT(DISTINCT author_anon) as total_users,
                COUNT(*) as total_messages,
                COUNT(DISTINCT metadata->>'channel') as total_channels
            FROM community_data 
            WHERE timestamp >= %s
                AND author_anon IS NOT NULL
            GROUP BY platform
            ORDER BY total_messages DESC
            """
            
            cur.execute(platform_query, (start_date,))
            platform_results = cur.fetchall()
            
            # 查詢總體統計
            total_query = """
            SELECT 
                COUNT(DISTINCT author_anon) as total_users,
                COUNT(*) as total_messages,
                COUNT(DISTINCT platform) as total_platforms
            FROM community_data 
            WHERE timestamp >= %s
                AND author_anon IS NOT NULL
            """
            
            cur.execute(total_query, (start_date,))
            total_result = cur.fetchone()
            
            cur.close()
            return_db_connection(conn)
            
            # 構建結果
            platforms = []
            for row in platform_results:
                platform, users, messages, channels = row
                platforms.append({
                    'platform': platform,
                    'total_users': users or 0,
                    'total_messages': messages or 0,
                    'total_channels': channels or 0
                })
            
            return {
                'total_users': total_result[0] if total_result else 0,
                'total_messages': total_result[1] if total_result else 0,
                'total_platforms': total_result[2] if total_result else 0,
                'platforms': platforms,
                'period_days': days_back
            }
                
        except Exception as e:
            self.logger.error(f"獲取多平台摘要失敗: {e}")
            return {
                'total_users': 0,
                'total_messages': 0,
                'total_platforms': 0,
                'platforms': [],
                'period_days': days_back
            }
    
    def get_calendar_event_stats(self, days_back: int = 90) -> Dict[str, Any]:
        """
        獲取日曆事件統計
        
        Args:
            days_back: 回溯天數
            
        Returns:
            日曆事件統計
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            start_date = datetime.now() - timedelta(days=days_back)
            
            # 查詢日曆事件統計
            query = """
            SELECT 
                COUNT(*) as total_events,
                COUNT(CASE WHEN start_time >= NOW() THEN 1 END) as upcoming_events,
                COUNT(CASE WHEN start_time < NOW() THEN 1 END) as past_events,
                COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_events,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_events,
                COUNT(DISTINCT calendar_id) as total_calendars
            FROM calendar_events
            WHERE start_time >= %s
            """
            
            cur.execute(query, (start_date,))
            result = cur.fetchone()
            
            cur.close()
            return_db_connection(conn)
            
            if result:
                return {
                    'total_events': result[0] or 0,
                    'upcoming_events': result[1] or 0,
                    'past_events': result[2] or 0,
                    'confirmed_events': result[3] or 0,
                    'cancelled_events': result[4] or 0,
                    'total_calendars': result[5] or 0,
                    'period_days': days_back
                }
            else:
                return {
                    'total_events': 0,
                    'upcoming_events': 0,
                    'past_events': 0,
                    'confirmed_events': 0,
                    'cancelled_events': 0,
                    'total_calendars': 0,
                    'period_days': days_back
                }
                
        except Exception as e:
            self.logger.error(f"獲取日曆事件統計失敗: {e}")
            return {
                'total_events': 0,
                'upcoming_events': 0,
                'past_events': 0,
                'confirmed_events': 0,
                'cancelled_events': 0,
                'total_calendars': 0,
                'period_days': days_back
            }

# MCP工具函數
def get_slack_user_stats(days_back: int = 90, limit: int = 10) -> List[Dict[str, Any]]:
    """獲取Slack用戶統計數據"""
    mcp = UserStatsMCP()
    return mcp.get_top_active_users("slack", days_back, limit)

def get_slack_activity_summary(days_back: int = 90) -> Dict[str, Any]:
    """獲取Slack活動摘要"""
    mcp = UserStatsMCP()
    return mcp.get_user_activity_summary("slack", days_back)

def get_multi_platform_summary(days_back: int = 90) -> Dict[str, Any]:
    """獲取多平台活動摘要"""
    mcp = UserStatsMCP()
    return mcp.get_multi_platform_summary(days_back)

def get_calendar_event_stats(days_back: int = 90) -> Dict[str, Any]:
    """獲取日曆事件統計"""
    mcp = UserStatsMCP()
    return mcp.get_calendar_event_stats(days_back)
