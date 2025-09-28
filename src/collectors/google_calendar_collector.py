#!/usr/bin/env python3
"""
Google Calendar 數據收集器
使用 Google Calendar API 收集日曆事件數據
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.storage.connection_pool import get_db_connection, return_db_connection
from src.utils.logging_config import structured_logger

logger = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """日曆事件數據結構"""
    id: str
    calendar_id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    attendees: List[Dict[str, Any]]
    creator_email: Optional[str]
    organizer_email: Optional[str]
    status: str
    visibility: str
    recurrence: Optional[str]
    source_url: Optional[str]
    metadata: Dict[str, Any]

class GoogleCalendarCollector:
    """Google Calendar 數據收集器"""
    
    def __init__(self, service_account_file: str = None, calendar_id: str = None):
        """
        初始化 Google Calendar 收集器
        
        Args:
            service_account_file: Service Account JSON 文件路徑
            calendar_id: 要收集的日曆ID，默認為 'primary'
        """
        self.logger = logging.getLogger(__name__)
        self.service_account_file = service_account_file or os.getenv('GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE')
        self.calendar_id = calendar_id or os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        # 如果calendar_id是完整的group.calendar.google.com格式，直接使用
        # 如果是舊的格式，需要轉換
        if self.calendar_id and '@' not in self.calendar_id and len(self.calendar_id) == 64:
            self.calendar_id = f"{self.calendar_id}@group.calendar.google.com"
        self.scopes = [os.getenv('GOOGLE_CALENDAR_SCOPES', 'https://www.googleapis.com/auth/calendar.readonly')]
        
        self.service = None
        self.stats = {
            'events_collected': 0,
            'calendars_processed': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        self._initialize_service()
    
    def _initialize_service(self):
        """初始化 Google Calendar API 服務"""
        try:
            if not self.service_account_file:
                raise ValueError("Google Calendar Service Account file not provided")
            
            if not os.path.exists(self.service_account_file):
                raise FileNotFoundError(f"Service Account file not found: {self.service_account_file}")
            
            # 從環境變數或文件讀取 Service Account 信息
            if os.path.exists(self.service_account_file):
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=self.scopes
                )
            else:
                # 從環境變數讀取
                service_account_info = json.loads(os.getenv('GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON', '{}'))
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=self.scopes
                )
            
            self.service = build('calendar', 'v3', credentials=credentials)
            self.logger.info("Google Calendar API 服務初始化成功")
            
        except Exception as e:
            self.logger.error(f"初始化 Google Calendar API 服務失敗: {e}")
            raise
    
    def collect_calendars(self) -> List[Dict[str, Any]]:
        """收集可用的日曆列表"""
        calendars = []
        
        try:
            self.logger.info("開始收集日曆列表...")
            
            calendar_list = self.service.calendarList().list().execute()
            
            for calendar_item in calendar_list.get('items', []):
                calendar_info = {
                    'id': calendar_item['id'],
                    'name': calendar_item.get('summary', 'Unknown'),
                    'description': calendar_item.get('description', ''),
                    'timezone': calendar_item.get('timeZone', 'UTC'),
                    'access_role': calendar_item.get('accessRole', ''),
                    'is_primary': calendar_item.get('primary', False),
                    'is_selected': calendar_item.get('selected', True),
                    'color_id': calendar_item.get('colorId', ''),
                    'background_color': calendar_item.get('backgroundColor', ''),
                    'foreground_color': calendar_item.get('foregroundColor', ''),
                    'metadata': {
                        'kind': calendar_item.get('kind', ''),
                        'etag': calendar_item.get('etag', ''),
                        'conference_properties': calendar_item.get('conferenceProperties', {}),
                        'notification_settings': calendar_item.get('notificationSettings', {})
                    }
                }
                calendars.append(calendar_info)
                self.stats['calendars_processed'] += 1
            
            self.logger.info(f"日曆列表收集完成，共 {len(calendars)} 個日曆")
            
        except HttpError as e:
            self.logger.error(f"收集日曆列表失敗: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            self.logger.error(f"收集日曆列表時發生錯誤: {e}")
            self.stats['errors'] += 1
        
        return calendars
    
    def collect_events(self, days_back: int = 90, calendar_id: str = None) -> List[CalendarEvent]:
        """
        收集日曆事件
        
        Args:
            days_back: 回溯天數
            calendar_id: 日曆ID，如果為None則使用初始化時的calendar_id
            
        Returns:
            日曆事件列表
        """
        events = []
        target_calendar_id = calendar_id or self.calendar_id
        
        try:
            self.logger.info(f"開始收集日曆 {target_calendar_id} 的事件，回溯 {days_back} 天")
            
            # 計算時間範圍
            now = datetime.now(timezone.utc)
            time_min = now - timedelta(days=days_back)
            time_max = now + timedelta(days=30)  # 也收集未來30天的事件
            
            # 構建查詢參數
            events_result = self.service.events().list(
                calendarId=target_calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy='startTime',
                maxResults=1000
            ).execute()
            
            for event_data in events_result.get('items', []):
                try:
                    event = self._parse_event(event_data, target_calendar_id)
                    if event:
                        events.append(event)
                        self.stats['events_collected'] += 1
                except Exception as e:
                    self.logger.error(f"解析事件失敗 {event_data.get('id', 'unknown')}: {e}")
                    self.stats['errors'] += 1
            
            self.logger.info(f"日曆 {target_calendar_id} 事件收集完成，共 {len(events)} 個事件")
            
        except HttpError as e:
            self.logger.error(f"收集日曆事件失敗: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            self.logger.error(f"收集日曆事件時發生錯誤: {e}")
            self.stats['errors'] += 1
        
        return events
    
    def _parse_event(self, event_data: Dict[str, Any], calendar_id: str) -> Optional[CalendarEvent]:
        """解析日曆事件數據"""
        try:
            event_id = event_data.get('id')
            if not event_id:
                return None
            
            # 解析時間
            start_time = self._parse_datetime(event_data.get('start', {}))
            end_time = self._parse_datetime(event_data.get('end', {}))
            
            if not start_time or not end_time:
                self.logger.warning(f"事件 {event_id} 缺少有效的開始或結束時間")
                return None
            
            # 解析參與者
            attendees = []
            for attendee in event_data.get('attendees', []):
                attendees.append({
                    'email': attendee.get('email', ''),
                    'display_name': attendee.get('displayName', ''),
                    'response_status': attendee.get('responseStatus', 'needsAction'),
                    'optional': attendee.get('optional', False),
                    'organizer': attendee.get('organizer', False)
                })
            
            # 構建事件對象
            event = CalendarEvent(
                id=event_id,
                calendar_id=calendar_id,
                title=event_data.get('summary', 'No Title'),
                description=event_data.get('description', ''),
                start_time=start_time,
                end_time=end_time,
                location=event_data.get('location', ''),
                attendees=attendees,
                creator_email=event_data.get('creator', {}).get('email', ''),
                organizer_email=event_data.get('organizer', {}).get('email', ''),
                status=event_data.get('status', 'confirmed'),
                visibility=event_data.get('visibility', 'default'),
                recurrence=event_data.get('recurrence', [None])[0] if event_data.get('recurrence') else None,
                source_url=event_data.get('htmlLink', ''),
                metadata={
                    'kind': event_data.get('kind', ''),
                    'etag': event_data.get('etag', ''),
                    'created': event_data.get('created', ''),
                    'updated': event_data.get('updated', ''),
                    'sequence': event_data.get('sequence', 0),
                    'transparency': event_data.get('transparency', 'opaque'),
                    'reminders': event_data.get('reminders', {}),
                    'conference_data': event_data.get('conferenceData', {}),
                    'hangout_link': event_data.get('hangoutLink', ''),
                    'html_link': event_data.get('htmlLink', ''),
                    'i_cal_uid': event_data.get('iCalUID', ''),
                    'recurring_event_id': event_data.get('recurringEventId', '')
                }
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"解析事件數據失敗: {e}")
            return None
    
    def _parse_datetime(self, datetime_data: Dict[str, Any]) -> Optional[datetime]:
        """解析日期時間數據"""
        try:
            if 'dateTime' in datetime_data:
                # 有時區信息的日期時間
                return datetime.fromisoformat(datetime_data['dateTime'].replace('Z', '+00:00'))
            elif 'date' in datetime_data:
                # 全天事件
                date_str = datetime_data['date']
                return datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
            else:
                return None
        except Exception as e:
            self.logger.error(f"解析日期時間失敗: {e}")
            return None
    
    def collect_all_calendars(self, days_back: int = 90) -> Dict[str, Any]:
        """收集所有日曆的事件"""
        all_events = []
        all_calendars = []
        
        self.stats['start_time'] = datetime.now()
        
        try:
            # 如果指定了特定的日曆ID，直接收集該日曆的事件
            if self.calendar_id and self.calendar_id != 'primary':
                self.logger.info(f"直接收集指定日曆 {self.calendar_id} 的事件")
                events = self.collect_events(days_back=days_back, calendar_id=self.calendar_id)
                all_events.extend(events)
                
                # 創建日曆信息
                calendar_info = {
                    'id': self.calendar_id,
                    'name': '源來適你社群日曆',
                    'description': '源來適你社群活動日曆',
                    'timezone': 'Asia/Taipei',
                    'access_role': 'reader',
                    'is_primary': False,
                    'is_selected': True,
                    'color_id': '',
                    'background_color': '',
                    'foreground_color': '',
                    'metadata': {}
                }
                all_calendars.append(calendar_info)
            else:
                # 收集日曆列表
                calendars = self.collect_calendars()
                all_calendars.extend(calendars)
                
                # 為每個日曆收集事件
                for calendar in calendars:
                    calendar_id = calendar['id']
                    calendar_name = calendar['name']
                    
                    self.logger.info(f"收集日曆 {calendar_name} ({calendar_id}) 的事件")
                    
                    events = self.collect_events(days_back=days_back, calendar_id=calendar_id)
                    all_events.extend(events)
                
                # 避免API限制
                import time
                time.sleep(1)
            
            self.stats['end_time'] = datetime.now()
            
            self.logger.info(f"所有日曆事件收集完成，共 {len(all_events)} 個事件，{len(all_calendars)} 個日曆")
            
        except Exception as e:
            self.logger.error(f"收集所有日曆事件失敗: {e}")
            self.stats['errors'] += 1
        
        return {
            'events': all_events,
            'calendars': all_calendars,
            'stats': self.stats
        }
    
    def save_calendars_to_db(self, calendars: List[Dict[str, Any]]) -> bool:
        """將日曆信息保存到數據庫"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            for calendar in calendars:
                cur.execute("""
                    INSERT INTO google_calendars (
                        id, name, description, timezone, access_role, is_primary,
                        is_selected, color_id, background_color, foreground_color, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        timezone = EXCLUDED.timezone,
                        access_role = EXCLUDED.access_role,
                        is_primary = EXCLUDED.is_primary,
                        is_selected = EXCLUDED.is_selected,
                        color_id = EXCLUDED.color_id,
                        background_color = EXCLUDED.background_color,
                        foreground_color = EXCLUDED.foreground_color,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """, (
                    calendar['id'],
                    calendar['name'],
                    calendar['description'],
                    calendar['timezone'],
                    calendar['access_role'],
                    calendar['is_primary'],
                    calendar['is_selected'],
                    calendar['color_id'],
                    calendar['background_color'],
                    calendar['foreground_color'],
                    json.dumps(calendar['metadata'])
                ))
            
            conn.commit()
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"成功保存 {len(calendars)} 個日曆到數據庫")
            return True
            
        except Exception as e:
            self.logger.error(f"保存日曆到數據庫失敗: {e}")
            return False
    
    def save_events_to_db(self, events: List[CalendarEvent]) -> bool:
        """將事件保存到數據庫"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            for event in events:
                cur.execute("""
                    INSERT INTO calendar_events (
                        id, calendar_id, title, description, start_time, end_time,
                        location, attendees, creator_email, organizer_email, status,
                        visibility, recurrence, source_url, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        calendar_id = EXCLUDED.calendar_id,
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        start_time = EXCLUDED.start_time,
                        end_time = EXCLUDED.end_time,
                        location = EXCLUDED.location,
                        attendees = EXCLUDED.attendees,
                        creator_email = EXCLUDED.creator_email,
                        organizer_email = EXCLUDED.organizer_email,
                        status = EXCLUDED.status,
                        visibility = EXCLUDED.visibility,
                        recurrence = EXCLUDED.recurrence,
                        source_url = EXCLUDED.source_url,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """, (
                    event.id,
                    event.calendar_id,
                    event.title,
                    event.description,
                    event.start_time,
                    event.end_time,
                    event.location,
                    json.dumps(event.attendees),
                    event.creator_email,
                    event.organizer_email,
                    event.status,
                    event.visibility,
                    event.recurrence,
                    event.source_url,
                    json.dumps(event.metadata)
                ))
            
            conn.commit()
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"成功保存 {len(events)} 個事件到數據庫")
            return True
            
        except Exception as e:
            self.logger.error(f"保存事件到數據庫失敗: {e}")
            return False

Google Calendar 數據收集器
使用 Google Calendar API 收集日曆事件數據
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from src.storage.connection_pool import get_db_connection, return_db_connection
from src.utils.logging_config import structured_logger

logger = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """日曆事件數據結構"""
    id: str
    calendar_id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    location: Optional[str]
    attendees: List[Dict[str, Any]]
    creator_email: Optional[str]
    organizer_email: Optional[str]
    status: str
    visibility: str
    recurrence: Optional[str]
    source_url: Optional[str]
    metadata: Dict[str, Any]

class GoogleCalendarCollector:
    """Google Calendar 數據收集器"""
    
    def __init__(self, service_account_file: str = None, calendar_id: str = None):
        """
        初始化 Google Calendar 收集器
        
        Args:
            service_account_file: Service Account JSON 文件路徑
            calendar_id: 要收集的日曆ID，默認為 'primary'
        """
        self.logger = logging.getLogger(__name__)
        self.service_account_file = service_account_file or os.getenv('GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE')
        self.calendar_id = calendar_id or os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        # 如果calendar_id是完整的group.calendar.google.com格式，直接使用
        # 如果是舊的格式，需要轉換
        if self.calendar_id and '@' not in self.calendar_id and len(self.calendar_id) == 64:
            self.calendar_id = f"{self.calendar_id}@group.calendar.google.com"
        self.scopes = [os.getenv('GOOGLE_CALENDAR_SCOPES', 'https://www.googleapis.com/auth/calendar.readonly')]
        
        self.service = None
        self.stats = {
            'events_collected': 0,
            'calendars_processed': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        self._initialize_service()
    
    def _initialize_service(self):
        """初始化 Google Calendar API 服務"""
        try:
            if not self.service_account_file:
                raise ValueError("Google Calendar Service Account file not provided")
            
            if not os.path.exists(self.service_account_file):
                raise FileNotFoundError(f"Service Account file not found: {self.service_account_file}")
            
            # 從環境變數或文件讀取 Service Account 信息
            if os.path.exists(self.service_account_file):
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=self.scopes
                )
            else:
                # 從環境變數讀取
                service_account_info = json.loads(os.getenv('GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON', '{}'))
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=self.scopes
                )
            
            self.service = build('calendar', 'v3', credentials=credentials)
            self.logger.info("Google Calendar API 服務初始化成功")
            
        except Exception as e:
            self.logger.error(f"初始化 Google Calendar API 服務失敗: {e}")
            raise
    
    def collect_calendars(self) -> List[Dict[str, Any]]:
        """收集可用的日曆列表"""
        calendars = []
        
        try:
            self.logger.info("開始收集日曆列表...")
            
            calendar_list = self.service.calendarList().list().execute()
            
            for calendar_item in calendar_list.get('items', []):
                calendar_info = {
                    'id': calendar_item['id'],
                    'name': calendar_item.get('summary', 'Unknown'),
                    'description': calendar_item.get('description', ''),
                    'timezone': calendar_item.get('timeZone', 'UTC'),
                    'access_role': calendar_item.get('accessRole', ''),
                    'is_primary': calendar_item.get('primary', False),
                    'is_selected': calendar_item.get('selected', True),
                    'color_id': calendar_item.get('colorId', ''),
                    'background_color': calendar_item.get('backgroundColor', ''),
                    'foreground_color': calendar_item.get('foregroundColor', ''),
                    'metadata': {
                        'kind': calendar_item.get('kind', ''),
                        'etag': calendar_item.get('etag', ''),
                        'conference_properties': calendar_item.get('conferenceProperties', {}),
                        'notification_settings': calendar_item.get('notificationSettings', {})
                    }
                }
                calendars.append(calendar_info)
                self.stats['calendars_processed'] += 1
            
            self.logger.info(f"日曆列表收集完成，共 {len(calendars)} 個日曆")
            
        except HttpError as e:
            self.logger.error(f"收集日曆列表失敗: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            self.logger.error(f"收集日曆列表時發生錯誤: {e}")
            self.stats['errors'] += 1
        
        return calendars
    
    def collect_events(self, days_back: int = 90, calendar_id: str = None) -> List[CalendarEvent]:
        """
        收集日曆事件
        
        Args:
            days_back: 回溯天數
            calendar_id: 日曆ID，如果為None則使用初始化時的calendar_id
            
        Returns:
            日曆事件列表
        """
        events = []
        target_calendar_id = calendar_id or self.calendar_id
        
        try:
            self.logger.info(f"開始收集日曆 {target_calendar_id} 的事件，回溯 {days_back} 天")
            
            # 計算時間範圍
            now = datetime.now(timezone.utc)
            time_min = now - timedelta(days=days_back)
            time_max = now + timedelta(days=30)  # 也收集未來30天的事件
            
            # 構建查詢參數
            events_result = self.service.events().list(
                calendarId=target_calendar_id,
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy='startTime',
                maxResults=1000
            ).execute()
            
            for event_data in events_result.get('items', []):
                try:
                    event = self._parse_event(event_data, target_calendar_id)
                    if event:
                        events.append(event)
                        self.stats['events_collected'] += 1
                except Exception as e:
                    self.logger.error(f"解析事件失敗 {event_data.get('id', 'unknown')}: {e}")
                    self.stats['errors'] += 1
            
            self.logger.info(f"日曆 {target_calendar_id} 事件收集完成，共 {len(events)} 個事件")
            
        except HttpError as e:
            self.logger.error(f"收集日曆事件失敗: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            self.logger.error(f"收集日曆事件時發生錯誤: {e}")
            self.stats['errors'] += 1
        
        return events
    
    def _parse_event(self, event_data: Dict[str, Any], calendar_id: str) -> Optional[CalendarEvent]:
        """解析日曆事件數據"""
        try:
            event_id = event_data.get('id')
            if not event_id:
                return None
            
            # 解析時間
            start_time = self._parse_datetime(event_data.get('start', {}))
            end_time = self._parse_datetime(event_data.get('end', {}))
            
            if not start_time or not end_time:
                self.logger.warning(f"事件 {event_id} 缺少有效的開始或結束時間")
                return None
            
            # 解析參與者
            attendees = []
            for attendee in event_data.get('attendees', []):
                attendees.append({
                    'email': attendee.get('email', ''),
                    'display_name': attendee.get('displayName', ''),
                    'response_status': attendee.get('responseStatus', 'needsAction'),
                    'optional': attendee.get('optional', False),
                    'organizer': attendee.get('organizer', False)
                })
            
            # 構建事件對象
            event = CalendarEvent(
                id=event_id,
                calendar_id=calendar_id,
                title=event_data.get('summary', 'No Title'),
                description=event_data.get('description', ''),
                start_time=start_time,
                end_time=end_time,
                location=event_data.get('location', ''),
                attendees=attendees,
                creator_email=event_data.get('creator', {}).get('email', ''),
                organizer_email=event_data.get('organizer', {}).get('email', ''),
                status=event_data.get('status', 'confirmed'),
                visibility=event_data.get('visibility', 'default'),
                recurrence=event_data.get('recurrence', [None])[0] if event_data.get('recurrence') else None,
                source_url=event_data.get('htmlLink', ''),
                metadata={
                    'kind': event_data.get('kind', ''),
                    'etag': event_data.get('etag', ''),
                    'created': event_data.get('created', ''),
                    'updated': event_data.get('updated', ''),
                    'sequence': event_data.get('sequence', 0),
                    'transparency': event_data.get('transparency', 'opaque'),
                    'reminders': event_data.get('reminders', {}),
                    'conference_data': event_data.get('conferenceData', {}),
                    'hangout_link': event_data.get('hangoutLink', ''),
                    'html_link': event_data.get('htmlLink', ''),
                    'i_cal_uid': event_data.get('iCalUID', ''),
                    'recurring_event_id': event_data.get('recurringEventId', '')
                }
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"解析事件數據失敗: {e}")
            return None
    
    def _parse_datetime(self, datetime_data: Dict[str, Any]) -> Optional[datetime]:
        """解析日期時間數據"""
        try:
            if 'dateTime' in datetime_data:
                # 有時區信息的日期時間
                return datetime.fromisoformat(datetime_data['dateTime'].replace('Z', '+00:00'))
            elif 'date' in datetime_data:
                # 全天事件
                date_str = datetime_data['date']
                return datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
            else:
                return None
        except Exception as e:
            self.logger.error(f"解析日期時間失敗: {e}")
            return None
    
    def collect_all_calendars(self, days_back: int = 90) -> Dict[str, Any]:
        """收集所有日曆的事件"""
        all_events = []
        all_calendars = []
        
        self.stats['start_time'] = datetime.now()
        
        try:
            # 如果指定了特定的日曆ID，直接收集該日曆的事件
            if self.calendar_id and self.calendar_id != 'primary':
                self.logger.info(f"直接收集指定日曆 {self.calendar_id} 的事件")
                events = self.collect_events(days_back=days_back, calendar_id=self.calendar_id)
                all_events.extend(events)
                
                # 創建日曆信息
                calendar_info = {
                    'id': self.calendar_id,
                    'name': '源來適你社群日曆',
                    'description': '源來適你社群活動日曆',
                    'timezone': 'Asia/Taipei',
                    'access_role': 'reader',
                    'is_primary': False,
                    'is_selected': True,
                    'color_id': '',
                    'background_color': '',
                    'foreground_color': '',
                    'metadata': {}
                }
                all_calendars.append(calendar_info)
            else:
                # 收集日曆列表
                calendars = self.collect_calendars()
                all_calendars.extend(calendars)
                
                # 為每個日曆收集事件
                for calendar in calendars:
                    calendar_id = calendar['id']
                    calendar_name = calendar['name']
                    
                    self.logger.info(f"收集日曆 {calendar_name} ({calendar_id}) 的事件")
                    
                    events = self.collect_events(days_back=days_back, calendar_id=calendar_id)
                    all_events.extend(events)
                
                # 避免API限制
                import time
                time.sleep(1)
            
            self.stats['end_time'] = datetime.now()
            
            self.logger.info(f"所有日曆事件收集完成，共 {len(all_events)} 個事件，{len(all_calendars)} 個日曆")
            
        except Exception as e:
            self.logger.error(f"收集所有日曆事件失敗: {e}")
            self.stats['errors'] += 1
        
        return {
            'events': all_events,
            'calendars': all_calendars,
            'stats': self.stats
        }
    
    def save_calendars_to_db(self, calendars: List[Dict[str, Any]]) -> bool:
        """將日曆信息保存到數據庫"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            for calendar in calendars:
                cur.execute("""
                    INSERT INTO google_calendars (
                        id, name, description, timezone, access_role, is_primary,
                        is_selected, color_id, background_color, foreground_color, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        timezone = EXCLUDED.timezone,
                        access_role = EXCLUDED.access_role,
                        is_primary = EXCLUDED.is_primary,
                        is_selected = EXCLUDED.is_selected,
                        color_id = EXCLUDED.color_id,
                        background_color = EXCLUDED.background_color,
                        foreground_color = EXCLUDED.foreground_color,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """, (
                    calendar['id'],
                    calendar['name'],
                    calendar['description'],
                    calendar['timezone'],
                    calendar['access_role'],
                    calendar['is_primary'],
                    calendar['is_selected'],
                    calendar['color_id'],
                    calendar['background_color'],
                    calendar['foreground_color'],
                    json.dumps(calendar['metadata'])
                ))
            
            conn.commit()
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"成功保存 {len(calendars)} 個日曆到數據庫")
            return True
            
        except Exception as e:
            self.logger.error(f"保存日曆到數據庫失敗: {e}")
            return False
    
    def save_events_to_db(self, events: List[CalendarEvent]) -> bool:
        """將事件保存到數據庫"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            for event in events:
                cur.execute("""
                    INSERT INTO calendar_events (
                        id, calendar_id, title, description, start_time, end_time,
                        location, attendees, creator_email, organizer_email, status,
                        visibility, recurrence, source_url, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        calendar_id = EXCLUDED.calendar_id,
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        start_time = EXCLUDED.start_time,
                        end_time = EXCLUDED.end_time,
                        location = EXCLUDED.location,
                        attendees = EXCLUDED.attendees,
                        creator_email = EXCLUDED.creator_email,
                        organizer_email = EXCLUDED.organizer_email,
                        status = EXCLUDED.status,
                        visibility = EXCLUDED.visibility,
                        recurrence = EXCLUDED.recurrence,
                        source_url = EXCLUDED.source_url,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """, (
                    event.id,
                    event.calendar_id,
                    event.title,
                    event.description,
                    event.start_time,
                    event.end_time,
                    event.location,
                    json.dumps(event.attendees),
                    event.creator_email,
                    event.organizer_email,
                    event.status,
                    event.visibility,
                    event.recurrence,
                    event.source_url,
                    json.dumps(event.metadata)
                ))
            
            conn.commit()
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"成功保存 {len(events)} 個事件到數據庫")
            return True
            
        except Exception as e:
            self.logger.error(f"保存事件到數據庫失敗: {e}")
            return False
