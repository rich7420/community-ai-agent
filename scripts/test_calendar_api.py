#!/usr/bin/env python3
"""
測試Google Calendar API的最小可行範例
"""

import os
import sys
import json
from datetime import datetime, timezone

# 添加src目錄到Python路徑
sys.path.append('/app')

def main():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        SERVICE_ACCOUNT_FILE = "/app/config/google-service-account.json"
        CALENDAR_ID = "39f25275dd411c20544fa301767c89b17bd551e4b3afd5b5c5f8678e82fa4849@group.calendar.google.com"
        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
        
        print("開始測試Google Calendar API...")
        print(f"Service Account File: {SERVICE_ACCOUNT_FILE}")
        print(f"Calendar ID: {CALENDAR_ID}")
        
        # 1) 用服務帳戶憑證與 readonly scope 建立 credentials
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        print("✅ 服務帳戶憑證載入成功")
        
        # 2) 建立 Calendar API client
        service = build("calendar", "v3", credentials=creds)
        print("✅ Calendar API client 建立成功")
        
        # 3) 設定查詢範圍（抓未來的 50 筆事件）
        time_min = datetime.now(timezone.utc).isoformat()
        print(f"查詢時間範圍: {time_min} 之後")
        
        # 4) 呼叫 events.list
        result = (
            service.events()
            .list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                singleEvents=True,       # 展開循環事件
                orderBy="startTime",     # 依開始時間排序
                maxResults=50,
            )
            .execute()
        )
        
        items = result.get("items", [])
        print(f"✅ 成功獲取 {len(items)} 個事件")
        
        if items:
            print("\n📅 事件列表:")
            for i, event in enumerate(items, 1):
                summary = event.get('summary', '無標題')
                start = event.get('start', {})
                end = event.get('end', {})
                html_link = event.get('htmlLink', '無連結')
                
                start_time = start.get('dateTime', start.get('date', '未知時間'))
                end_time = end.get('dateTime', end.get('date', '未知時間'))
                
                print(f"{i:2d}. {summary}")
                print(f"    時間: {start_time} -> {end_time}")
                print(f"    連結: {html_link}")
                print()
        else:
            print("❌ 沒有找到任何事件")
            
        return True
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        
        # 印出更有用的錯誤資訊
        status = getattr(getattr(e, "resp", None), "status", None)
        content = getattr(e, "content", None)
        print("錯誤狀態碼:", status)
        if content:
            try:
                print("錯誤內容:", json.loads(content.decode()))
            except Exception:
                print("錯誤內容 (原始):", content)
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
"""
測試Google Calendar API的最小可行範例
"""

import os
import sys
import json
from datetime import datetime, timezone

# 添加src目錄到Python路徑
sys.path.append('/app')

def main():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        SERVICE_ACCOUNT_FILE = "/app/config/google-service-account.json"
        CALENDAR_ID = "39f25275dd411c20544fa301767c89b17bd551e4b3afd5b5c5f8678e82fa4849@group.calendar.google.com"
        SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
        
        print("開始測試Google Calendar API...")
        print(f"Service Account File: {SERVICE_ACCOUNT_FILE}")
        print(f"Calendar ID: {CALENDAR_ID}")
        
        # 1) 用服務帳戶憑證與 readonly scope 建立 credentials
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        print("✅ 服務帳戶憑證載入成功")
        
        # 2) 建立 Calendar API client
        service = build("calendar", "v3", credentials=creds)
        print("✅ Calendar API client 建立成功")
        
        # 3) 設定查詢範圍（抓未來的 50 筆事件）
        time_min = datetime.now(timezone.utc).isoformat()
        print(f"查詢時間範圍: {time_min} 之後")
        
        # 4) 呼叫 events.list
        result = (
            service.events()
            .list(
                calendarId=CALENDAR_ID,
                timeMin=time_min,
                singleEvents=True,       # 展開循環事件
                orderBy="startTime",     # 依開始時間排序
                maxResults=50,
            )
            .execute()
        )
        
        items = result.get("items", [])
        print(f"✅ 成功獲取 {len(items)} 個事件")
        
        if items:
            print("\n📅 事件列表:")
            for i, event in enumerate(items, 1):
                summary = event.get('summary', '無標題')
                start = event.get('start', {})
                end = event.get('end', {})
                html_link = event.get('htmlLink', '無連結')
                
                start_time = start.get('dateTime', start.get('date', '未知時間'))
                end_time = end.get('dateTime', end.get('date', '未知時間'))
                
                print(f"{i:2d}. {summary}")
                print(f"    時間: {start_time} -> {end_time}")
                print(f"    連結: {html_link}")
                print()
        else:
            print("❌ 沒有找到任何事件")
            
        return True
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        
        # 印出更有用的錯誤資訊
        status = getattr(getattr(e, "resp", None), "status", None)
        content = getattr(e, "content", None)
        print("錯誤狀態碼:", status)
        if content:
            try:
                print("錯誤內容:", json.loads(content.decode()))
            except Exception:
                print("錯誤內容 (原始):", content)
        
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
