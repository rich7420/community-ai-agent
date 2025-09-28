import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from psycopg2.extras import RealDictCursor
from storage.connection_pool import get_db_connection, return_db_connection
import json

logger = logging.getLogger(__name__)

class CalendarEventInfo:
    """日曆事件信息"""
    def __init__(self, id: str, title: str, start_time: datetime, end_time: datetime, 
                 location: Optional[str] = None, description: Optional[str] = None,
                 attendees: List[str] = None, creator: Optional[str] = None, 
                 organizer: Optional[str] = None, status: str = 'confirmed', 
                 source_url: Optional[str] = None):
        self.id = id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.description = description
        self.attendees = attendees or []
        self.creator = creator
        self.organizer = organizer
        self.status = status
        self.source_url = source_url

class CalendarMCPFixed:
    """修復版本的Google Calendar MCP 服務 - 查詢community_data表"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_upcoming_events(self, days_ahead: int = 7, limit: int = 10) -> List[CalendarEventInfo]:
        """
        獲取即將到來的事件
        
        Args:
            days_ahead: 未來多少天
            limit: 最大返回數量
            
        Returns:
            事件列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            now = datetime.now(timezone.utc)
            future_time = now + timedelta(days=days_ahead)
            
            # 查詢community_data表中的日曆事件
            cur.execute("""
                SELECT id, content, timestamp, metadata
                FROM community_data
                WHERE platform = 'google_calendar'
                AND timestamp >= %s AND timestamp <= %s
                ORDER BY timestamp ASC
                LIMIT %s
            """, (now, future_time, limit))
            
            events = []
            for row in cur.fetchall():
                event = self._parse_calendar_event(row)
                if event:
                    events.append(event)
            
            self.logger.info(f"獲取到 {len(events)} 個即將到來的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"獲取即將到來的事件失敗: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    def get_events_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 10) -> List[CalendarEventInfo]:
        """
        獲取指定日期範圍內的事件
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            limit: 最大返回數量
            
        Returns:
            事件列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, content, timestamp, metadata
                FROM community_data
                WHERE platform = 'google_calendar'
                AND timestamp >= %s AND timestamp <= %s
                ORDER BY timestamp ASC
                LIMIT %s
            """, (start_date, end_date, limit))
            
            events = []
            for row in cur.fetchall():
                event = self._parse_calendar_event(row)
                if event:
                    events.append(event)
            
            self.logger.info(f"獲取到 {len(events)} 個指定日期範圍內的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"獲取指定日期範圍內的事件失敗: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    def search_events(self, query: str, limit: int = 5) -> List[CalendarEventInfo]:
        """
        搜索事件
        
        Args:
            query: 搜索關鍵詞
            limit: 最大返回數量
            
        Returns:
            事件列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, content, timestamp, metadata
                FROM community_data
                WHERE platform = 'google_calendar'
                AND content ILIKE %s
                ORDER BY 
                    CASE 
                        WHEN metadata->>'start_time' IS NOT NULL 
                        THEN (metadata->>'start_time')::timestamp 
                        ELSE timestamp 
                    END DESC
                LIMIT %s
            """, (f'%{query}%', limit))
            
            events = []
            for row in cur.fetchall():
                event = self._parse_calendar_event(row)
                if event:
                    events.append(event)
            
            self.logger.info(f"搜索到 {len(events)} 個包含關鍵字 '{query}' 的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"搜索事件失敗: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    def _parse_calendar_event(self, row: Dict[str, Any]) -> Optional[CalendarEventInfo]:
        """解析日曆事件數據"""
        try:
            content = row['content']
            metadata = row['metadata'] or {}
            
            # 從content中提取事件信息
            lines = content.split('\n')
            title = "未知事件"
            start_time = row['timestamp']
            end_time = row['timestamp']
            location = None
            description = None
            
            for line in lines:
                if line.startswith('事件標題:'):
                    title = line.replace('事件標題:', '').strip()
                elif line.startswith('開始時間:'):
                    try:
                        start_time = datetime.fromisoformat(line.replace('開始時間:', '').strip())
                    except:
                        start_time = row['timestamp']
                elif line.startswith('結束時間:'):
                    try:
                        end_time = datetime.fromisoformat(line.replace('結束時間:', '').strip())
                    except:
                        end_time = row['timestamp']
                elif line.startswith('地點:'):
                    location = line.replace('地點:', '').strip()
                elif line.startswith('描述:'):
                    description = line.replace('描述:', '').strip()
            
            # 解析參與者
            attendees = []
            if metadata.get('attendees'):
                try:
                    attendees_data = json.loads(metadata['attendees'])
                    attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                except (json.JSONDecodeError, TypeError):
                    attendees = []
            
            return CalendarEventInfo(
                id=row['id'],
                title=title,
                start_time=start_time,
                end_time=end_time,
                location=location,
                description=description,
                attendees=attendees,
                creator=metadata.get('creator_email'),
                organizer=metadata.get('organizer_email'),
                status=metadata.get('status', 'confirmed'),
                source_url=metadata.get('source_url')
            )
            
        except Exception as e:
            self.logger.error(f"解析日曆事件失敗: {e}")
            return None
    
    def format_events_for_display(self, events: List[CalendarEventInfo]) -> str:
        """
        格式化事件列表以便顯示
        
        Args:
            events: 事件列表
            
        Returns:
            格式化的事件字符串
        """
        if not events:
            return "沒有找到相關的日曆事件。"
        
        formatted_output = []
        for event in events:
            start_time_str = event.start_time.strftime('%Y-%m-%d %H:%M')
            end_time_str = event.end_time.strftime('%H:%M')
            
            event_info = f"**{event.title}**\n" \
                         f"  時間: {start_time_str} - {end_time_str}\n"
            if event.location:
                event_info += f"  地點: {event.location}\n"
            if event.description:
                event_info += f"  描述: {event.description.splitlines()[0][:100]}...\n" if len(event.description) > 100 else f"  描述: {event.description}\n"
            if event.source_url:
                event_info += f"  連結: {event.source_url}\n"
            
            formatted_output.append(event_info)
        
        return "\n---\n".join(formatted_output)

from datetime import datetime, timedelta, timezone
from psycopg2.extras import RealDictCursor
from storage.connection_pool import get_db_connection, return_db_connection
import json

logger = logging.getLogger(__name__)

class CalendarEventInfo:
    """日曆事件信息"""
    def __init__(self, id: str, title: str, start_time: datetime, end_time: datetime, 
                 location: Optional[str] = None, description: Optional[str] = None,
                 attendees: List[str] = None, creator: Optional[str] = None, 
                 organizer: Optional[str] = None, status: str = 'confirmed', 
                 source_url: Optional[str] = None):
        self.id = id
        self.title = title
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.description = description
        self.attendees = attendees or []
        self.creator = creator
        self.organizer = organizer
        self.status = status
        self.source_url = source_url

class CalendarMCPFixed:
    """修復版本的Google Calendar MCP 服務 - 查詢community_data表"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_upcoming_events(self, days_ahead: int = 7, limit: int = 10) -> List[CalendarEventInfo]:
        """
        獲取即將到來的事件
        
        Args:
            days_ahead: 未來多少天
            limit: 最大返回數量
            
        Returns:
            事件列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            now = datetime.now(timezone.utc)
            future_time = now + timedelta(days=days_ahead)
            
            # 查詢community_data表中的日曆事件
            cur.execute("""
                SELECT id, content, timestamp, metadata
                FROM community_data
                WHERE platform = 'google_calendar'
                AND timestamp >= %s AND timestamp <= %s
                ORDER BY timestamp ASC
                LIMIT %s
            """, (now, future_time, limit))
            
            events = []
            for row in cur.fetchall():
                event = self._parse_calendar_event(row)
                if event:
                    events.append(event)
            
            self.logger.info(f"獲取到 {len(events)} 個即將到來的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"獲取即將到來的事件失敗: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    def get_events_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 10) -> List[CalendarEventInfo]:
        """
        獲取指定日期範圍內的事件
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            limit: 最大返回數量
            
        Returns:
            事件列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, content, timestamp, metadata
                FROM community_data
                WHERE platform = 'google_calendar'
                AND timestamp >= %s AND timestamp <= %s
                ORDER BY timestamp ASC
                LIMIT %s
            """, (start_date, end_date, limit))
            
            events = []
            for row in cur.fetchall():
                event = self._parse_calendar_event(row)
                if event:
                    events.append(event)
            
            self.logger.info(f"獲取到 {len(events)} 個指定日期範圍內的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"獲取指定日期範圍內的事件失敗: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    def search_events(self, query: str, limit: int = 5) -> List[CalendarEventInfo]:
        """
        搜索事件
        
        Args:
            query: 搜索關鍵詞
            limit: 最大返回數量
            
        Returns:
            事件列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, content, timestamp, metadata
                FROM community_data
                WHERE platform = 'google_calendar'
                AND content ILIKE %s
                ORDER BY 
                    CASE 
                        WHEN metadata->>'start_time' IS NOT NULL 
                        THEN (metadata->>'start_time')::timestamp 
                        ELSE timestamp 
                    END DESC
                LIMIT %s
            """, (f'%{query}%', limit))
            
            events = []
            for row in cur.fetchall():
                event = self._parse_calendar_event(row)
                if event:
                    events.append(event)
            
            self.logger.info(f"搜索到 {len(events)} 個包含關鍵字 '{query}' 的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"搜索事件失敗: {e}")
            return []
        finally:
            if conn:
                return_db_connection(conn)
    
    def _parse_calendar_event(self, row: Dict[str, Any]) -> Optional[CalendarEventInfo]:
        """解析日曆事件數據"""
        try:
            content = row['content']
            metadata = row['metadata'] or {}
            
            # 從content中提取事件信息
            lines = content.split('\n')
            title = "未知事件"
            start_time = row['timestamp']
            end_time = row['timestamp']
            location = None
            description = None
            
            for line in lines:
                if line.startswith('事件標題:'):
                    title = line.replace('事件標題:', '').strip()
                elif line.startswith('開始時間:'):
                    try:
                        start_time = datetime.fromisoformat(line.replace('開始時間:', '').strip())
                    except:
                        start_time = row['timestamp']
                elif line.startswith('結束時間:'):
                    try:
                        end_time = datetime.fromisoformat(line.replace('結束時間:', '').strip())
                    except:
                        end_time = row['timestamp']
                elif line.startswith('地點:'):
                    location = line.replace('地點:', '').strip()
                elif line.startswith('描述:'):
                    description = line.replace('描述:', '').strip()
            
            # 解析參與者
            attendees = []
            if metadata.get('attendees'):
                try:
                    attendees_data = json.loads(metadata['attendees'])
                    attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                except (json.JSONDecodeError, TypeError):
                    attendees = []
            
            return CalendarEventInfo(
                id=row['id'],
                title=title,
                start_time=start_time,
                end_time=end_time,
                location=location,
                description=description,
                attendees=attendees,
                creator=metadata.get('creator_email'),
                organizer=metadata.get('organizer_email'),
                status=metadata.get('status', 'confirmed'),
                source_url=metadata.get('source_url')
            )
            
        except Exception as e:
            self.logger.error(f"解析日曆事件失敗: {e}")
            return None
    
    def format_events_for_display(self, events: List[CalendarEventInfo]) -> str:
        """
        格式化事件列表以便顯示
        
        Args:
            events: 事件列表
            
        Returns:
            格式化的事件字符串
        """
        if not events:
            return "沒有找到相關的日曆事件。"
        
        formatted_output = []
        for event in events:
            start_time_str = event.start_time.strftime('%Y-%m-%d %H:%M')
            end_time_str = event.end_time.strftime('%H:%M')
            
            event_info = f"**{event.title}**\n" \
                         f"  時間: {start_time_str} - {end_time_str}\n"
            if event.location:
                event_info += f"  地點: {event.location}\n"
            if event.description:
                event_info += f"  描述: {event.description.splitlines()[0][:100]}...\n" if len(event.description) > 100 else f"  描述: {event.description}\n"
            if event.source_url:
                event_info += f"  連結: {event.source_url}\n"
            
            formatted_output.append(event_info)
        
        return "\n---\n".join(formatted_output)
