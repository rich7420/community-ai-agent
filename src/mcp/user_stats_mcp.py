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
                      days_back: int = 30,
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
                user_name, message_count, reply_count, last_activity, channel_count, channels = row
                
                # 計算emoji統計
                emoji_stats = self._get_emoji_stats(cur, user_name, platform, start_date)
                
                stats = UserStats(
                    user_id=user_name,  # 使用user_name作為ID
                    user_name=user_name,
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
            reactions_results = cur.fetchall()
            
            received_count = 0
            for row in reactions_results:
                reactions = row[0]
                if reactions:
                    for reaction in reactions:
                        users = reaction.get('users', [])
                        if user_name in users:
                            received_count += reaction.get('count', 0)
            
            return {
                'given': given_count,
                'received': received_count
            }
            
        except Exception as e:
            self.logger.error(f"獲取emoji統計失敗: {e}")
            return {'given': 0, 'received': 0}
    
    def get_top_active_users(self, 
                           platform: str = "slack",
                           days_back: int = 30,
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
                                days_back: int = 30) -> Dict[str, Any]:
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
            
            # 總體統計
            summary_query = """
            SELECT 
                COUNT(DISTINCT author_anon) as total_users,
                COUNT(*) as total_messages,
                COUNT(DISTINCT metadata->>'channel') as total_channels,
                AVG(message_count) as avg_messages_per_user
            FROM (
                SELECT 
                    author_anon,
                    COUNT(*) as message_count
                FROM community_data 
                WHERE platform = %s 
                    AND timestamp >= %s
                    AND author_anon IS NOT NULL
                GROUP BY author_anon
            ) user_counts
            """
            
            cur.execute(summary_query, (platform, start_date))
            summary_result = cur.fetchone()
            
            cur.close()
            return_db_connection(conn)
            
            if summary_result:
                total_users, total_messages, total_channels, avg_messages = summary_result
                return {
                    'total_users': total_users or 0,
                    'total_messages': total_messages or 0,
                    'total_channels': total_channels or 0,
                    'avg_messages_per_user': round(avg_messages or 0, 2),
                    'period_days': days_back,
                    'platform': platform
                }
            else:
                return {
                    'total_users': 0,
                    'total_messages': 0,
                    'total_channels': 0,
                    'avg_messages_per_user': 0,
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

# MCP工具函數
def get_slack_user_stats(days_back: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
    """獲取Slack用戶統計數據"""
    mcp = UserStatsMCP()
    return mcp.get_top_active_users("slack", days_back, limit)

def get_slack_activity_summary(days_back: int = 30) -> Dict[str, Any]:
    """獲取Slack活動摘要"""
    mcp = UserStatsMCP()
    return mcp.get_user_activity_summary("slack", days_back)
