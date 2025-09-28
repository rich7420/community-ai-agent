#!/usr/bin/env python3
"""
Google Calendar MCP (Model Context Protocol) 服務
提供日曆查詢功能供QA模型調用
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

@dataclass
class CalendarEventInfo:
    """日曆事件信息"""
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    description: Optional[str]
    attendees: List[str]
    creator: Optional[str]
    organizer: Optional[str]
    status: str
    source_url: Optional[str]

class CalendarMCP:
    """Google Calendar MCP 服務"""
    
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
            
            cur.execute("""
                SELECT id, title, start_time, end_time, location, description,
                       attendees, creator_email, organizer_email, status, source_url
                FROM calendar_events
                WHERE start_time >= %s AND start_time <= %s
                AND status = 'confirmed'
                ORDER BY start_time ASC
                LIMIT %s
            """, (now, future_time, limit))
            
            events = []
            for row in cur.fetchall():
                # 解析參與者
                attendees = []
                if row['attendees']:
                    try:
                        attendees_data = json.loads(row['attendees'])
                        attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                    except (json.JSONDecodeError, TypeError):
                        attendees = []
                
                event = CalendarEventInfo(
                    id=row['id'],
                    title=row['title'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    description=row['description'],
                    attendees=attendees,
                    creator=row['creator_email'],
                    organizer=row['organizer_email'],
                    status=row['status'],
                    source_url=row['source_url']
                )
                events.append(event)
            
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"獲取到 {len(events)} 個即將到來的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"獲取即將到來的事件失敗: {e}")
            return []
    
    def get_events_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 50) -> List[CalendarEventInfo]:
        """
        根據日期範圍獲取事件
        
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
                SELECT id, title, start_time, end_time, location, description,
                       attendees, creator_email, organizer_email, status, source_url
                FROM calendar_events
                WHERE start_time >= %s AND start_time <= %s
                AND status = 'confirmed'
                ORDER BY start_time ASC
                LIMIT %s
            """, (start_date, end_date, limit))
            
            events = []
            for row in cur.fetchall():
                # 解析參與者
                attendees = []
                if row['attendees']:
                    try:
                        attendees_data = json.loads(row['attendees'])
                        attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                    except (json.JSONDecodeError, TypeError):
                        attendees = []
                
                event = CalendarEventInfo(
                    id=row['id'],
                    title=row['title'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    description=row['description'],
                    attendees=attendees,
                    creator=row['creator_email'],
                    organizer=row['organizer_email'],
                    status=row['status'],
                    source_url=row['source_url']
                )
                events.append(event)
            
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"獲取到 {len(events)} 個指定日期範圍的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"根據日期範圍獲取事件失敗: {e}")
            return []
    
    def search_events(self, query: str, limit: int = 20) -> List[CalendarEventInfo]:
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
            
            search_pattern = f"%{query}%"
            
            cur.execute("""
                SELECT id, title, start_time, end_time, location, description,
                       attendees, creator_email, organizer_email, status, source_url
                FROM calendar_events
                WHERE (title ILIKE %s OR description ILIKE %s OR location ILIKE %s)
                AND status = 'confirmed'
                ORDER BY start_time DESC
                LIMIT %s
            """, (search_pattern, search_pattern, search_pattern, limit))
            
            events = []
            for row in cur.fetchall():
                # 解析參與者
                attendees = []
                if row['attendees']:
                    try:
                        attendees_data = json.loads(row['attendees'])
                        attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                    except (json.JSONDecodeError, TypeError):
                        attendees = []
                
                event = CalendarEventInfo(
                    id=row['id'],
                    title=row['title'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    description=row['description'],
                    attendees=attendees,
                    creator=row['creator_email'],
                    organizer=row['organizer_email'],
                    status=row['status'],
                    source_url=row['source_url']
                )
                events.append(event)
            
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"搜索到 {len(events)} 個包含 '{query}' 的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"搜索事件失敗: {e}")
            return []
    
    def get_events_by_attendee(self, attendee_email: str, limit: int = 20) -> List[CalendarEventInfo]:
        """
        根據參與者獲取事件
        
        Args:
            attendee_email: 參與者郵箱
            limit: 最大返回數量
            
        Returns:
            事件列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, title, start_time, end_time, location, description,
                       attendees, creator_email, organizer_email, status, source_url
                FROM calendar_events
                WHERE attendees::text ILIKE %s
                AND status = 'confirmed'
                ORDER BY start_time DESC
                LIMIT %s
            """, (f"%{attendee_email}%", limit))
            
            events = []
            for row in cur.fetchall():
                # 解析參與者
                attendees = []
                if row['attendees']:
                    try:
                        attendees_data = json.loads(row['attendees'])
                        attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                    except (json.JSONDecodeError, TypeError):
                        attendees = []
                
                event = CalendarEventInfo(
                    id=row['id'],
                    title=row['title'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    description=row['description'],
                    attendees=attendees,
                    creator=row['creator_email'],
                    organizer=row['organizer_email'],
                    status=row['status'],
                    source_url=row['source_url']
                )
                events.append(event)
            
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"獲取到 {len(events)} 個 {attendee_email} 參與的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"根據參與者獲取事件失敗: {e}")
            return []
    
    def get_calendar_info(self) -> Dict[str, Any]:
        """
        獲取日曆信息
        
        Returns:
            日曆信息字典
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 獲取日曆列表
            cur.execute("""
                SELECT id, name, description, timezone, is_primary, is_selected
                FROM google_calendars
                ORDER BY is_primary DESC, name ASC
            """)
            
            calendars = []
            for row in cur.fetchall():
                calendars.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'timezone': row['timezone'],
                    'is_primary': row['is_primary'],
                    'is_selected': row['is_selected']
                })
            
            # 獲取事件統計
            cur.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN start_time >= NOW() THEN 1 END) as upcoming_events,
                    COUNT(CASE WHEN start_time < NOW() THEN 1 END) as past_events,
                    COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_events,
                    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_events
                FROM calendar_events
            """)
            
            stats = cur.fetchone()
            
            cur.close()
            return_db_connection(conn)
            
            return {
                'calendars': calendars,
                'statistics': {
                    'total_events': stats['total_events'],
                    'upcoming_events': stats['upcoming_events'],
                    'past_events': stats['past_events'],
                    'confirmed_events': stats['confirmed_events'],
                    'cancelled_events': stats['cancelled_events']
                }
            }
            
        except Exception as e:
            self.logger.error(f"獲取日曆信息失敗: {e}")
            return {'calendars': [], 'statistics': {}}
    
    def format_events_for_display(self, events: List[CalendarEventInfo]) -> str:
        """
        格式化事件列表用於顯示
        
        Args:
            events: 事件列表
            
        Returns:
            格式化的事件字符串
        """
        if not events:
            return "沒有找到相關事件。"
        
        formatted_events = []
        for i, event in enumerate(events, 1):
            event_info = f"{i}. **{event.title}**\n"
            event_info += f"   📅 時間: {event.start_time.strftime('%Y-%m-%d %H:%M')} - {event.end_time.strftime('%H:%M')}\n"
            
            if event.location:
                event_info += f"   📍 地點: {event.location}\n"
            
            if event.description:
                # 截取描述前100個字符
                desc = event.description[:100] + "..." if len(event.description) > 100 else event.description
                event_info += f"   📝 描述: {desc}\n"
            
            if event.attendees:
                attendees_str = ", ".join(event.attendees[:5])  # 只顯示前5個參與者
                if len(event.attendees) > 5:
                    attendees_str += f" 等{len(event.attendees)}人"
                event_info += f"   👥 參與者: {attendees_str}\n"
            
            if event.source_url:
                event_info += f"   🔗 連結: {event.source_url}\n"
            
            formatted_events.append(event_info)
        
        return "\n".join(formatted_events)
"""
Google Calendar MCP (Model Context Protocol) 服務
提供日曆查詢功能供QA模型調用
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from storage.connection_pool import get_db_connection, return_db_connection
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

@dataclass
class CalendarEventInfo:
    """日曆事件信息"""
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    description: Optional[str]
    attendees: List[str]
    creator: Optional[str]
    organizer: Optional[str]
    status: str
    source_url: Optional[str]

class CalendarMCP:
    """Google Calendar MCP 服務"""
    
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
            
            cur.execute("""
                SELECT id, title, start_time, end_time, location, description,
                       attendees, creator_email, organizer_email, status, source_url
                FROM calendar_events
                WHERE start_time >= %s AND start_time <= %s
                AND status = 'confirmed'
                ORDER BY start_time ASC
                LIMIT %s
            """, (now, future_time, limit))
            
            events = []
            for row in cur.fetchall():
                # 解析參與者
                attendees = []
                if row['attendees']:
                    try:
                        attendees_data = json.loads(row['attendees'])
                        attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                    except (json.JSONDecodeError, TypeError):
                        attendees = []
                
                event = CalendarEventInfo(
                    id=row['id'],
                    title=row['title'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    description=row['description'],
                    attendees=attendees,
                    creator=row['creator_email'],
                    organizer=row['organizer_email'],
                    status=row['status'],
                    source_url=row['source_url']
                )
                events.append(event)
            
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"獲取到 {len(events)} 個即將到來的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"獲取即將到來的事件失敗: {e}")
            return []
    
    def get_events_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 50) -> List[CalendarEventInfo]:
        """
        根據日期範圍獲取事件
        
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
                SELECT id, title, start_time, end_time, location, description,
                       attendees, creator_email, organizer_email, status, source_url
                FROM calendar_events
                WHERE start_time >= %s AND start_time <= %s
                AND status = 'confirmed'
                ORDER BY start_time ASC
                LIMIT %s
            """, (start_date, end_date, limit))
            
            events = []
            for row in cur.fetchall():
                # 解析參與者
                attendees = []
                if row['attendees']:
                    try:
                        attendees_data = json.loads(row['attendees'])
                        attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                    except (json.JSONDecodeError, TypeError):
                        attendees = []
                
                event = CalendarEventInfo(
                    id=row['id'],
                    title=row['title'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    description=row['description'],
                    attendees=attendees,
                    creator=row['creator_email'],
                    organizer=row['organizer_email'],
                    status=row['status'],
                    source_url=row['source_url']
                )
                events.append(event)
            
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"獲取到 {len(events)} 個指定日期範圍的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"根據日期範圍獲取事件失敗: {e}")
            return []
    
    def search_events(self, query: str, limit: int = 20) -> List[CalendarEventInfo]:
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
            
            search_pattern = f"%{query}%"
            
            cur.execute("""
                SELECT id, title, start_time, end_time, location, description,
                       attendees, creator_email, organizer_email, status, source_url
                FROM calendar_events
                WHERE (title ILIKE %s OR description ILIKE %s OR location ILIKE %s)
                AND status = 'confirmed'
                ORDER BY start_time DESC
                LIMIT %s
            """, (search_pattern, search_pattern, search_pattern, limit))
            
            events = []
            for row in cur.fetchall():
                # 解析參與者
                attendees = []
                if row['attendees']:
                    try:
                        attendees_data = json.loads(row['attendees'])
                        attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                    except (json.JSONDecodeError, TypeError):
                        attendees = []
                
                event = CalendarEventInfo(
                    id=row['id'],
                    title=row['title'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    description=row['description'],
                    attendees=attendees,
                    creator=row['creator_email'],
                    organizer=row['organizer_email'],
                    status=row['status'],
                    source_url=row['source_url']
                )
                events.append(event)
            
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"搜索到 {len(events)} 個包含 '{query}' 的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"搜索事件失敗: {e}")
            return []
    
    def get_events_by_attendee(self, attendee_email: str, limit: int = 20) -> List[CalendarEventInfo]:
        """
        根據參與者獲取事件
        
        Args:
            attendee_email: 參與者郵箱
            limit: 最大返回數量
            
        Returns:
            事件列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, title, start_time, end_time, location, description,
                       attendees, creator_email, organizer_email, status, source_url
                FROM calendar_events
                WHERE attendees::text ILIKE %s
                AND status = 'confirmed'
                ORDER BY start_time DESC
                LIMIT %s
            """, (f"%{attendee_email}%", limit))
            
            events = []
            for row in cur.fetchall():
                # 解析參與者
                attendees = []
                if row['attendees']:
                    try:
                        attendees_data = json.loads(row['attendees'])
                        attendees = [att.get('display_name', att.get('email', '')) for att in attendees_data if att.get('display_name') or att.get('email')]
                    except (json.JSONDecodeError, TypeError):
                        attendees = []
                
                event = CalendarEventInfo(
                    id=row['id'],
                    title=row['title'],
                    start_time=row['start_time'],
                    end_time=row['end_time'],
                    location=row['location'],
                    description=row['description'],
                    attendees=attendees,
                    creator=row['creator_email'],
                    organizer=row['organizer_email'],
                    status=row['status'],
                    source_url=row['source_url']
                )
                events.append(event)
            
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"獲取到 {len(events)} 個 {attendee_email} 參與的事件")
            return events
            
        except Exception as e:
            self.logger.error(f"根據參與者獲取事件失敗: {e}")
            return []
    
    def get_calendar_info(self) -> Dict[str, Any]:
        """
        獲取日曆信息
        
        Returns:
            日曆信息字典
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 獲取日曆列表
            cur.execute("""
                SELECT id, name, description, timezone, is_primary, is_selected
                FROM google_calendars
                ORDER BY is_primary DESC, name ASC
            """)
            
            calendars = []
            for row in cur.fetchall():
                calendars.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'timezone': row['timezone'],
                    'is_primary': row['is_primary'],
                    'is_selected': row['is_selected']
                })
            
            # 獲取事件統計
            cur.execute("""
                SELECT 
                    COUNT(*) as total_events,
                    COUNT(CASE WHEN start_time >= NOW() THEN 1 END) as upcoming_events,
                    COUNT(CASE WHEN start_time < NOW() THEN 1 END) as past_events,
                    COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed_events,
                    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_events
                FROM calendar_events
            """)
            
            stats = cur.fetchone()
            
            cur.close()
            return_db_connection(conn)
            
            return {
                'calendars': calendars,
                'statistics': {
                    'total_events': stats['total_events'],
                    'upcoming_events': stats['upcoming_events'],
                    'past_events': stats['past_events'],
                    'confirmed_events': stats['confirmed_events'],
                    'cancelled_events': stats['cancelled_events']
                }
            }
            
        except Exception as e:
            self.logger.error(f"獲取日曆信息失敗: {e}")
            return {'calendars': [], 'statistics': {}}
    
    def format_events_for_display(self, events: List[CalendarEventInfo]) -> str:
        """
        格式化事件列表用於顯示
        
        Args:
            events: 事件列表
            
        Returns:
            格式化的事件字符串
        """
        if not events:
            return "沒有找到相關事件。"
        
        formatted_events = []
        for i, event in enumerate(events, 1):
            event_info = f"{i}. **{event.title}**\n"
            event_info += f"   📅 時間: {event.start_time.strftime('%Y-%m-%d %H:%M')} - {event.end_time.strftime('%H:%M')}\n"
            
            if event.location:
                event_info += f"   📍 地點: {event.location}\n"
            
            if event.description:
                # 截取描述前100個字符
                desc = event.description[:100] + "..." if len(event.description) > 100 else event.description
                event_info += f"   📝 描述: {desc}\n"
            
            if event.attendees:
                attendees_str = ", ".join(event.attendees[:5])  # 只顯示前5個參與者
                if len(event.attendees) > 5:
                    attendees_str += f" 等{len(event.attendees)}人"
                event_info += f"   👥 參與者: {attendees_str}\n"
            
            if event.source_url:
                event_info += f"   🔗 連結: {event.source_url}\n"
            
            formatted_events.append(event_info)
        
        return "\n".join(formatted_events)
