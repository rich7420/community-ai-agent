#!/usr/bin/env python3
"""
初始化數據收集腳本
用於生產環境的首次部署時進行數據收集
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main import initial_data_collection, set_initial_collection_completed

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """主函數"""
    try:
        logger.info("開始初始化數據收集...")
        
        # 執行初始數據收集
        await initial_data_collection()
        
        # 設置完成標記
        await set_initial_collection_completed()
        
        logger.info("初始化數據收集完成！")
        return True
        
    except Exception as e:
        logger.error(f"初始化數據收集失敗: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
