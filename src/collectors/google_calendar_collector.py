#!/usr/bin/env python3
"""
Google Calendar 數據收集器
使用 Google Calendar API 收集日曆事件數據
"""

import os
import json
import logging
import base64
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from storage.connection_pool import get_db_connection, return_db_connection
from utils.logging_config import structured_logger

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
        
        # 處理日曆 ID 格式
        self.calendar_id = self._normalize_calendar_id(self.calendar_id)
        
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
    
    def _normalize_calendar_id(self, calendar_id: str) -> str:
        """標準化日曆 ID 格式"""
        if not calendar_id or calendar_id == 'primary':
            return 'primary'
        
        # 如果已經是完整的 email 格式，直接返回
        if '@' in calendar_id:
            return calendar_id
        
        # 如果是 Base64 編碼的 ID（長度超過 64 字符）
        if len(calendar_id) > 64:
            try:
                # 嘗試解碼 Base64
                decoded_bytes = base64.b64decode(calendar_id)
                decoded_str = decoded_bytes.decode('utf-8')
                self.logger.info(f"解碼日曆 ID: {calendar_id} -> {decoded_str}")
                return decoded_str
            except Exception as e:
                self.logger.warning(f"無法解碼日曆 ID {calendar_id}: {e}")
                # 如果解碼失敗，嘗試添加 @group.calendar.google.com
                return f"{calendar_id}@group.calendar.google.com"
        
        # 如果是 64 字符長度的 ID，可能是 Base64 編碼
        if len(calendar_id) == 64 and calendar_id.isalnum():
            try:
                # 嘗試解碼 Base64
                decoded_bytes = base64.b64decode(calendar_id)
                decoded_str = decoded_bytes.decode('utf-8')
                self.logger.info(f"解碼日曆 ID: {calendar_id} -> {decoded_str}")
                return decoded_str
            except Exception as e:
                self.logger.warning(f"無法解碼日曆 ID {calendar_id}: {e}")
                # 如果解碼失敗，嘗試添加 @group.calendar.google.com
                return f"{calendar_id}@group.calendar.google.com"
        
        # 如果長度不是 64，可能是其他格式，嘗試添加 @group.calendar.google.com
        if len(calendar_id) > 20:  # 假設是有效的日曆 ID
            return f"{calendar_id}@group.calendar.google.com"
        
        # 如果都不符合，返回原始值
        return calendar_id
    
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
        """收集日曆事件"""
        events = []
        target_calendar_id = calendar_id or self.calendar_id
        
        try:
            self.logger.info(f"開始收集日曆事件，日曆ID: {target_calendar_id}")
            self.stats['start_time'] = datetime.now()
            
            # 首先驗證日曆是否存在
            if not self._validate_calendar_access(target_calendar_id):
                self.logger.error(f"無法訪問日曆: {target_calendar_id}")
                return events
            
            # 計算時間範圍
            now = datetime.now(timezone.utc)
            time_min = (now - timedelta(days=days_back)).isoformat()
            time_max = (now + timedelta(days=60)).isoformat()  # 也收集未來60天的事件
            
            # 收集事件
            events_result = self.service.events().list(
                calendarId=target_calendar_id,
                timeMin=time_min,
                timeMax=time_max,
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
                    self.logger.error(f"解析事件失敗: {e}")
                    self.stats['errors'] += 1
            
            self.stats['end_time'] = datetime.now()
            self.logger.info(f"事件收集完成，共 {len(events)} 個事件")
            
        except HttpError as e:
            if e.resp.status == 404:
                self.logger.error(f"日曆不存在或無權限訪問: {target_calendar_id}")
                self.logger.info("嘗試使用 'primary' 日曆...")
                # 嘗試使用 primary 日曆
                if target_calendar_id != 'primary':
                    return self.collect_events(days_back, 'primary')
            else:
                self.logger.error(f"收集日曆事件失敗: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            self.logger.error(f"收集日曆事件時發生錯誤: {e}")
            self.stats['errors'] += 1
        
        return events
    
    def _validate_calendar_access(self, calendar_id: str) -> bool:
        """驗證日曆訪問權限"""
        try:
            # 嘗試獲取日曆信息
            calendar_info = self.service.calendars().get(calendarId=calendar_id).execute()
            self.logger.info(f"成功驗證日曆訪問: {calendar_info.get('summary', calendar_id)}")
            return True
        except HttpError as e:
            if e.resp.status == 404:
                self.logger.error(f"日曆不存在: {calendar_id}")
            elif e.resp.status == 403:
                self.logger.error(f"無權限訪問日曆: {calendar_id}")
            else:
                self.logger.error(f"驗證日曆訪問失敗: {e}")
            return False
        except Exception as e:
            self.logger.error(f"驗證日曆訪問時發生錯誤: {e}")
            return False
    
    def _parse_event(self, event_data: Dict[str, Any], calendar_id: str) -> Optional[CalendarEvent]:
        """解析單個事件數據"""
        try:
            # 解析時間
            start_data = event_data.get('start', {})
            end_data = event_data.get('end', {})
            
            start_time = self._parse_datetime(start_data)
            end_time = self._parse_datetime(end_data)
            
            if not start_time or not end_time:
                return None
            
            # 解析參與者
            attendees = []
            for attendee in event_data.get('attendees', []):
                attendees.append({
                    'email': attendee.get('email', ''),
                    'name': attendee.get('displayName', ''),
                    'response_status': attendee.get('responseStatus', 'needsAction'),
                    'organizer': attendee.get('organizer', False)
                })
            
            # 創建事件對象
            event = CalendarEvent(
                id=event_data.get('id', ''),
                calendar_id=calendar_id,
                title=event_data.get('summary', '無標題'),
                description=event_data.get('description', ''),
                start_time=start_time,
                end_time=end_time,
                location=event_data.get('location', ''),
                attendees=attendees,
                creator_email=event_data.get('creator', {}).get('email', ''),
                organizer_email=event_data.get('organizer', {}).get('email', ''),
                status=event_data.get('status', 'confirmed'),
                visibility=event_data.get('visibility', 'default'),
                recurrence=event_data.get('recurrence', None),
                source_url=event_data.get('htmlLink', ''),
                metadata={
                    'kind': event_data.get('kind', ''),
                    'etag': event_data.get('etag', ''),
                    'created': event_data.get('created', ''),
                    'updated': event_data.get('updated', ''),
                    'hangout_link': event_data.get('hangoutLink', ''),
                    'conference_data': event_data.get('conferenceData', {}),
                    'reminders': event_data.get('reminders', {}),
                    'source': event_data.get('source', {})
                }
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"解析事件數據失敗: {e}")
            return None
    
    def _parse_datetime(self, time_data: Dict[str, Any]) -> Optional[datetime]:
        """解析時間數據"""
        try:
            # 優先使用 dateTime，如果沒有則使用 date
            if 'dateTime' in time_data:
                return datetime.fromisoformat(time_data['dateTime'].replace('Z', '+00:00'))
            elif 'date' in time_data:
                # 全天事件，使用當天的開始時間
                date_str = time_data['date']
                return datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
            else:
                return None
        except Exception as e:
            self.logger.error(f"解析時間失敗: {e}")
            return None
    
    def collect_all_calendars(self, days_back: int = 90) -> Dict[str, Any]:
        """收集所有日曆的數據"""
        result = {
            'calendars': [],
            'events': [],
            'stats': self.stats
        }
        
        try:
            # 收集日曆列表
            calendars = self.collect_calendars()
            result['calendars'] = calendars
            
            # 如果沒有找到日曆，嘗試使用 primary 日曆
            if not calendars:
                self.logger.warning("沒有找到任何日曆，嘗試使用 primary 日曆")
                calendars = [{
                    'id': 'primary', 
                    'name': 'Primary Calendar', 
                    'description': 'Default calendar',
                    'timezone': 'UTC',
                    'access_role': 'owner',
                    'is_primary': True,
                    'is_selected': True,
                    'color_id': '',
                    'background_color': '',
                    'foreground_color': '',
                    'metadata': {}
                }]
                result['calendars'] = calendars
            
            # 收集主要日曆的事件
            events = self.collect_events(days_back)
            result['events'] = events
            
            # 如果主要日曆沒有事件，嘗試收集所有可用日曆的事件
            if not events and calendars:
                self.logger.info("主要日曆沒有事件，嘗試收集所有可用日曆的事件")
                all_events = []
                for calendar in calendars:
                    calendar_id = calendar.get('id')
                    if calendar_id and calendar_id != self.calendar_id:
                        try:
                            calendar_events = self.collect_events(days_back, calendar_id)
                            all_events.extend(calendar_events)
                            self.logger.info(f"從日曆 {calendar.get('name', calendar_id)} 收集到 {len(calendar_events)} 個事件")
                        except Exception as e:
                            self.logger.error(f"收集日曆 {calendar_id} 事件失敗: {e}")
                
                result['events'] = all_events
                events = all_events
            
            self.logger.info(f"所有日曆數據收集完成，共 {len(calendars)} 個日曆，{len(events)} 個事件")
            
        except Exception as e:
            self.logger.error(f"收集所有日曆數據失敗: {e}")
            self.stats['errors'] += 1
        
        return result
    
    def save_events_to_db(self, events: List[CalendarEvent]) -> bool:
        """保存事件到數據庫"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            for event in events:
                cur.execute("""
                    INSERT INTO calendar_events (
                        id, calendar_id, title, description, start_time, end_time,
                        location, attendees, creator_email, organizer_email, status,
                        visibility, recurrence, source_url, metadata, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (id) DO UPDATE SET
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
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    event.id, event.calendar_id, event.title, event.description,
                    event.start_time, event.end_time, event.location,
                    json.dumps(event.attendees), event.creator_email, event.organizer_email,
                    event.status, event.visibility, event.recurrence, event.source_url,
                    json.dumps(event.metadata), datetime.now()
                ))
            
            conn.commit()
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"成功保存 {len(events)} 個事件到數據庫")
            return True
            
        except Exception as e:
            self.logger.error(f"保存事件到數據庫失敗: {e}")
            return False
    
    def save_calendars_to_db(self, calendars: List[Dict[str, Any]]) -> bool:
        """保存日曆信息到數據庫"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            for calendar in calendars:
                # 確保所有必要欄位都存在
                calendar_data = {
                    'id': calendar.get('id', ''),
                    'name': calendar.get('name', 'Unknown'),
                    'description': calendar.get('description', ''),
                    'timezone': calendar.get('timezone', 'UTC'),
                    'access_role': calendar.get('access_role', ''),
                    'is_primary': calendar.get('is_primary', False),
                    'is_selected': calendar.get('is_selected', True),
                    'color_id': calendar.get('color_id', ''),
                    'background_color': calendar.get('background_color', ''),
                    'foreground_color': calendar.get('foreground_color', ''),
                    'metadata': calendar.get('metadata', {})
                }
                
                cur.execute("""
                    INSERT INTO google_calendars (
                        id, name, description, timezone, access_role,
                        is_primary, is_selected, color_id, background_color,
                        foreground_color, metadata, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (id) DO UPDATE SET
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
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    calendar_data['id'], calendar_data['name'], calendar_data['description'],
                    calendar_data['timezone'], calendar_data['access_role'], calendar_data['is_primary'],
                    calendar_data['is_selected'], calendar_data['color_id'], calendar_data['background_color'],
                    calendar_data['foreground_color'], json.dumps(calendar_data['metadata']), datetime.now()
                ))
            
            conn.commit()
            cur.close()
            return_db_connection(conn)
            
            self.logger.info(f"成功保存 {len(calendars)} 個日曆信息到數據庫")
            return True
            
        except Exception as e:
            self.logger.error(f"保存日曆信息到數據庫失敗: {e}")
            return False