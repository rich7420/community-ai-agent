#!/usr/bin/env python3
"""
手動收集Google Calendar數據的腳本 - 修復版本
"""

import os
import sys
import logging
from datetime import datetime

# 添加src目錄到Python路徑
sys.path.append('/app')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        # 設置環境變量
        os.environ['GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE'] = '/app/config/google-service-account.json'
        os.environ['GOOGLE_CALENDAR_ID'] = '39f25275dd411c20544fa301767c89b17bd551e4b3afd5b5c5f8678e82fa4849@group.calendar.google.com'
        os.environ['GOOGLE_CALENDAR_SCOPES'] = 'https://www.googleapis.com/auth/calendar.readonly'
        
        logger.info("開始收集Google Calendar數據...")
        
        # 導入收集器
        from src.collectors.google_calendar_collector import GoogleCalendarCollector
        from src.collectors.data_merger import DataMerger
        from src.storage.postgres_storage import PostgreSQLStorage
        from src.ai.gemini_embedding_generator import GeminiEmbeddingGenerator
        
        # 初始化收集器
        calendar_collector = GoogleCalendarCollector()
        logger.info(f"使用Calendar ID: {calendar_collector.calendar_id}")
        
        # 收集日曆數據
        calendar_data = calendar_collector.collect_all_calendars(days_back=90)
        logger.info(f"收集到 {len(calendar_data.get('events', []))} 個事件")
        
        if calendar_data.get('events'):
            # 合併數據
            data_merger = DataMerger()
            calendar_records = data_merger.merge_google_calendar_data(calendar_data['events'])
            logger.info(f"合併後得到 {len(calendar_records)} 條記錄")
            
            # 生成嵌入並保存到數據庫
            db_storage = PostgreSQLStorage()
            embedding_generator = GeminiEmbeddingGenerator()
            
            processed_count = 0
            for record in calendar_records:
                try:
                    # 生成嵌入
                    embedding = embedding_generator.generate_embedding(record.content)
                    record.embedding = embedding
                    
                    # 保存到數據庫
                    db_storage.insert_record(record)
                    processed_count += 1
                    
                    if processed_count % 5 == 0:
                        logger.info(f"已處理 {processed_count}/{len(calendar_records)} 條Calendar記錄")
                        
                except Exception as e:
                    logger.error(f"處理Calendar記錄失敗: {e}")
            
            logger.info(f"Google Calendar數據保存完成，共處理 {processed_count} 條記錄")
        
        # 保存日曆信息到數據庫
        if calendar_data.get('calendars'):
            calendar_collector.save_calendars_to_db(calendar_data['calendars'])
            logger.info(f"保存了 {len(calendar_data['calendars'])} 個日曆信息")
        
        logger.info("Google Calendar數據收集完成！")
        
    except Exception as e:
        logger.error(f"Google Calendar數據收集失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
手動收集Google Calendar數據的腳本 - 修復版本
"""

import os
import sys
import logging
from datetime import datetime

# 添加src目錄到Python路徑
sys.path.append('/app')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        # 設置環境變量
        os.environ['GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE'] = '/app/config/google-service-account.json'
        os.environ['GOOGLE_CALENDAR_ID'] = '39f25275dd411c20544fa301767c89b17bd551e4b3afd5b5c5f8678e82fa4849@group.calendar.google.com'
        os.environ['GOOGLE_CALENDAR_SCOPES'] = 'https://www.googleapis.com/auth/calendar.readonly'
        
        logger.info("開始收集Google Calendar數據...")
        
        # 導入收集器
        from src.collectors.google_calendar_collector import GoogleCalendarCollector
        from src.collectors.data_merger import DataMerger
        from src.storage.postgres_storage import PostgreSQLStorage
        from src.ai.gemini_embedding_generator import GeminiEmbeddingGenerator
        
        # 初始化收集器
        calendar_collector = GoogleCalendarCollector()
        logger.info(f"使用Calendar ID: {calendar_collector.calendar_id}")
        
        # 收集日曆數據
        calendar_data = calendar_collector.collect_all_calendars(days_back=90)
        logger.info(f"收集到 {len(calendar_data.get('events', []))} 個事件")
        
        if calendar_data.get('events'):
            # 合併數據
            data_merger = DataMerger()
            calendar_records = data_merger.merge_google_calendar_data(calendar_data['events'])
            logger.info(f"合併後得到 {len(calendar_records)} 條記錄")
            
            # 生成嵌入並保存到數據庫
            db_storage = PostgreSQLStorage()
            embedding_generator = GeminiEmbeddingGenerator()
            
            processed_count = 0
            for record in calendar_records:
                try:
                    # 生成嵌入
                    embedding = embedding_generator.generate_embedding(record.content)
                    record.embedding = embedding
                    
                    # 保存到數據庫
                    db_storage.insert_record(record)
                    processed_count += 1
                    
                    if processed_count % 5 == 0:
                        logger.info(f"已處理 {processed_count}/{len(calendar_records)} 條Calendar記錄")
                        
                except Exception as e:
                    logger.error(f"處理Calendar記錄失敗: {e}")
            
            logger.info(f"Google Calendar數據保存完成，共處理 {processed_count} 條記錄")
        
        # 保存日曆信息到數據庫
        if calendar_data.get('calendars'):
            calendar_collector.save_calendars_to_db(calendar_data['calendars'])
            logger.info(f"保存了 {len(calendar_data['calendars'])} 個日曆信息")
        
        logger.info("Google Calendar數據收集完成！")
        
    except Exception as e:
        logger.error(f"Google Calendar數據收集失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
