#!/usr/bin/env python3
"""
手動收集Slack數據的腳本 - 90天
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
        logger.info("開始收集Slack數據（90天）...")
        
        # 導入收集器
        from src.collectors.slack_collector import SlackCollector
        from src.collectors.data_merger import DataMerger
        from src.storage.postgres_storage import PostgreSQLStorage
        from src.ai.gemini_embedding_generator import GeminiEmbeddingGenerator
        
        # 獲取環境變量
        slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
        slack_app_token = os.getenv('SLACK_APP_TOKEN')
        
        if not slack_bot_token or not slack_app_token:
            logger.error("Slack tokens 未設置")
            sys.exit(1)
        
        # 初始化收集器
        slack_collector = SlackCollector(slack_bot_token, slack_app_token)
        logger.info("Slack收集器初始化成功")
        
        # 收集90天的Slack數據
        logger.info("開始收集90天的Slack數據...")
        slack_messages = slack_collector.collect_bot_channels(days_back=90)
        logger.info(f"Slack數據收集完成，共 {len(slack_messages)} 條訊息")
        
        if slack_messages:
            # 合併數據
            data_merger = DataMerger()
            slack_records = data_merger.merge_slack_data(slack_messages)
            logger.info(f"合併後得到 {len(slack_records)} 條Slack記錄")
            
            # 生成嵌入並保存到數據庫
            db_storage = PostgreSQLStorage()
            embedding_generator = GeminiEmbeddingGenerator()
            
            processed_count = 0
            for record in slack_records:
                try:
                    # 生成嵌入
                    embedding = embedding_generator.generate_embedding(record.content)
                    record.embedding = embedding
                    
                    # 保存到數據庫
                    db_storage.insert_record(record)
                    processed_count += 1
                    
                    if processed_count % 50 == 0:
                        logger.info(f"已處理 {processed_count}/{len(slack_records)} 條Slack記錄")
                        
                except Exception as e:
                    logger.error(f"處理Slack記錄失敗: {e}")
            
            logger.info(f"Slack數據保存完成，共處理 {processed_count} 條記錄")
        else:
            logger.warning("沒有收集到Slack數據")
        
        logger.info("Slack數據收集完成！")
        
    except Exception as e:
        logger.error(f"Slack數據收集失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
手動收集Slack數據的腳本 - 90天
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
        logger.info("開始收集Slack數據（90天）...")
        
        # 導入收集器
        from src.collectors.slack_collector import SlackCollector
        from src.collectors.data_merger import DataMerger
        from src.storage.postgres_storage import PostgreSQLStorage
        from src.ai.gemini_embedding_generator import GeminiEmbeddingGenerator
        
        # 獲取環境變量
        slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
        slack_app_token = os.getenv('SLACK_APP_TOKEN')
        
        if not slack_bot_token or not slack_app_token:
            logger.error("Slack tokens 未設置")
            sys.exit(1)
        
        # 初始化收集器
        slack_collector = SlackCollector(slack_bot_token, slack_app_token)
        logger.info("Slack收集器初始化成功")
        
        # 收集90天的Slack數據
        logger.info("開始收集90天的Slack數據...")
        slack_messages = slack_collector.collect_bot_channels(days_back=90)
        logger.info(f"Slack數據收集完成，共 {len(slack_messages)} 條訊息")
        
        if slack_messages:
            # 合併數據
            data_merger = DataMerger()
            slack_records = data_merger.merge_slack_data(slack_messages)
            logger.info(f"合併後得到 {len(slack_records)} 條Slack記錄")
            
            # 生成嵌入並保存到數據庫
            db_storage = PostgreSQLStorage()
            embedding_generator = GeminiEmbeddingGenerator()
            
            processed_count = 0
            for record in slack_records:
                try:
                    # 生成嵌入
                    embedding = embedding_generator.generate_embedding(record.content)
                    record.embedding = embedding
                    
                    # 保存到數據庫
                    db_storage.insert_record(record)
                    processed_count += 1
                    
                    if processed_count % 50 == 0:
                        logger.info(f"已處理 {processed_count}/{len(slack_records)} 條Slack記錄")
                        
                except Exception as e:
                    logger.error(f"處理Slack記錄失敗: {e}")
            
            logger.info(f"Slack數據保存完成，共處理 {processed_count} 條記錄")
        else:
            logger.warning("沒有收集到Slack數據")
        
        logger.info("Slack數據收集完成！")
        
    except Exception as e:
        logger.error(f"Slack數據收集失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
