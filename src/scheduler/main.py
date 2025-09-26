#!/usr/bin/env python3
"""
定時任務主入口
"""
import os
import sys
import logging
from dotenv import load_dotenv
from cron_jobs import CronJobScheduler

# 載入環境變數
load_dotenv()

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/scheduler.log')
    ]
)

def main():
    """主函數"""
    logger = logging.getLogger(__name__)
    
    try:
        # 創建調度器
        scheduler = CronJobScheduler()
        
        # 設置定時任務
        scheduler.setup_schedule()
        
        # 運行調度器
        scheduler.run_scheduler()
        
    except Exception as e:
        logger.error(f"調度器運行失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
