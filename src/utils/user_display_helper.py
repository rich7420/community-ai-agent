"""
用戶顯示名稱輔助工具
確保所有輸出都使用真實用戶名稱而不是匿名化ID
"""
import logging
from typing import Dict, List, Any, Optional
from storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class UserDisplayHelper:
    """用戶顯示名稱輔助工具"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._display_name_cache = {}
    
    def get_display_name(self, anonymized_id: str, platform: str = 'slack') -> str:
        """
        獲取用戶的顯示名稱
        
        Args:
            anonymized_id: 匿名化ID
            platform: 平台名稱
            
        Returns:
            顯示名稱，如果找不到則返回匿名化ID
        """
        # 檢查緩存
        cache_key = f"{platform}:{anonymized_id}"
        if cache_key in self._display_name_cache:
            return self._display_name_cache[cache_key]
        
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 優先從社區數據中獲取用戶名稱
            cur.execute("""
                SELECT
                    COALESCE(
                        metadata->>'real_name',
                        metadata->>'display_name', 
                        metadata->>'user_name',
                        metadata->>'name',
                        metadata->'user_profile'->>'real_name',
                        metadata->'user_profile'->>'display_name',
                        metadata->'user_profile'->>'name'
                    ) as display_name
                FROM community_data 
                WHERE author_anon = %s AND platform = %s
                AND (
                    metadata->>'real_name' IS NOT NULL 
                    OR metadata->>'display_name' IS NOT NULL 
                    OR metadata->>'user_name' IS NOT NULL
                    OR metadata->>'name' IS NOT NULL
                    OR metadata->'user_profile'->>'real_name' IS NOT NULL
                    OR metadata->'user_profile'->>'display_name' IS NOT NULL
                    OR metadata->'user_profile'->>'name' IS NOT NULL
                )
                ORDER BY timestamp DESC
                LIMIT 1
            """, (anonymized_id, platform))
            
            result = cur.fetchone()
            cur.close()
            return_db_connection(conn)
            
            if result and result['display_name'] and result['display_name'].strip():
                display_name = result['display_name'].strip()
                self._display_name_cache[cache_key] = display_name
                return display_name
            
            # 如果社區數據中沒有找到，嘗試查詢用戶映射表
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT display_name, real_name
                FROM user_name_mappings 
                WHERE anonymized_id = %s AND platform = %s AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            """, (anonymized_id, platform))
            
            result = cur.fetchone()
            cur.close()
            return_db_connection(conn)
            
            if result:
                display_name = result['display_name'] or result['real_name']
                if display_name and display_name.strip():
                    display_name = display_name.strip()
                    self._display_name_cache[cache_key] = display_name
                    return display_name
            
            # 如果都找不到，返回匿名化ID
            self._display_name_cache[cache_key] = anonymized_id
            return anonymized_id
            
        except Exception as e:
            self.logger.error(f"獲取用戶顯示名稱失敗: {e}")
            return anonymized_id
    
    def resolve_user_stats(self, user_stats: List[Dict[str, Any]], platform: str = 'slack') -> List[Dict[str, Any]]:
        """
        解析用戶統計數據中的用戶名稱
        
        Args:
            user_stats: 用戶統計數據列表
            platform: 平台名稱
            
        Returns:
            解析後的用戶統計數據列表
        """
        resolved_stats = []
        
        for stat in user_stats:
            # 複製原始數據
            resolved_stat = stat.copy()
            
            # 解析用戶名稱
            if 'user_name' in stat:
                resolved_stat['user_name'] = self.get_display_name(stat['user_name'], platform)
            elif 'author_anon' in stat:
                resolved_stat['user_name'] = self.get_display_name(stat['author_anon'], platform)
            
            resolved_stats.append(resolved_stat)
        
        return resolved_stats
    
    def format_user_activity_report(self, user_stats: List[Dict[str, Any]], platform: str = 'slack') -> str:
        """
        格式化用戶活躍度報告，確保顯示真實用戶名稱
        
        Args:
            user_stats: 用戶統計數據列表
            platform: 平台名稱
            
        Returns:
            格式化的報告文本
        """
        if not user_stats:
            return "沒有找到用戶活動數據。"
        
        # 解析用戶名稱
        resolved_stats = self.resolve_user_stats(user_stats, platform)
        
        # 按訊息數量排序
        resolved_stats.sort(key=lambda x: x.get('message_count', 0), reverse=True)
        
        report_lines = []
        
        # 添加總體統計
        total_users = len(resolved_stats)
        total_messages = sum(stat.get('message_count', 0) for stat in resolved_stats)
        avg_messages = total_messages / total_users if total_users > 0 else 0
        
        report_lines.extend([
            f"根據過去30天的客觀數據統計:",
            f"",
        ])
        
        # 添加個別用戶統計
        for i, stat in enumerate(resolved_stats[:3], 1):  # 只顯示前3名
            user_name = stat.get('user_name', 'Unknown User')
            message_count = stat.get('message_count', 0)
            reply_count = stat.get('reply_count', 0)
            emoji_count = stat.get('emoji_given_count', 0)
            
            report_lines.append(f"{user_name} - 發送{message_count}條訊息, 回覆{reply_count}次, 給出{emoji_count}個emoji")
        
        # 添加總體統計
        report_lines.extend([
            f"",
            f"總體統計: {total_users}位活躍用戶, 共{total_messages}條訊息, 平均每人{avg_messages:.2f}條訊息。"
        ])
        
        return "\n".join(report_lines)
    
    def clear_cache(self):
        """清除緩存"""
        self._display_name_cache.clear()
    
    def preload_display_names(self, anonymized_ids: List[str], platform: str = 'slack'):
        """
        預載入顯示名稱到緩存
        
        Args:
            anonymized_ids: 匿名化ID列表
            platform: 平台名稱
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 批量查詢顯示名稱
            placeholders = ','.join(['%s'] * len(anonymized_ids))
            query = f"""
                SELECT DISTINCT
                    author_anon,
                    COALESCE(
                        metadata->>'real_name',
                        metadata->>'display_name', 
                        metadata->>'user_name',
                        metadata->>'name',
                        metadata->'user_profile'->>'real_name',
                        metadata->'user_profile'->>'display_name',
                        metadata->'user_profile'->>'name',
                        author_anon
                    ) as display_name
                FROM community_data 
                WHERE author_anon IN ({placeholders}) AND platform = %s
                ORDER BY timestamp DESC
            """
            
            cur.execute(query, anonymized_ids + [platform])
            results = cur.fetchall()
            
            for result in results:
                cache_key = f"{platform}:{result['author_anon']}"
                display_name = result['display_name']
                if display_name and display_name.strip():
                    self._display_name_cache[cache_key] = display_name.strip()
                else:
                    self._display_name_cache[cache_key] = result['author_anon']
            
            cur.close()
            return_db_connection(conn)
            
        except Exception as e:
            self.logger.error(f"預載入顯示名稱失敗: {e}")
