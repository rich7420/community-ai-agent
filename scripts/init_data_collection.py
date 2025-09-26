#!/usr/bin/env python3
"""
初始化資料收集腳本
在部署時自動收集初始資料
"""
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# 添加 src 目錄到 Python 路徑
sys.path.append('/app/src')

from collectors.slack_collector import SlackCollector
from collectors.github_collector import GitHubCollector
from collectors.data_merger import DataMerger
from storage.postgres_storage import PostgreSQLStorage
from ai.gemini_embedding_generator import GeminiEmbeddingGenerator

# 載入環境變數
load_dotenv()

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def init_data_collection():
    """初始化資料收集"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🚀 開始初始化資料收集...")
        
        # 檢查必要的環境變數
        required_env_vars = [
            'SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'GITHUB_TOKEN',
            'DATABASE_URL', 'OPENROUTER_API_KEY'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var) or os.getenv(var).startswith('your-'):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"⚠️  缺少環境變數: {', '.join(missing_vars)}")
            logger.warning("將跳過相關的資料收集")
        
        # 初始化組件
        logger.info("初始化資料收集組件...")
        
        all_data = []
        
        # 收集 Slack 資料
        if os.getenv('SLACK_BOT_TOKEN') and os.getenv('SLACK_APP_TOKEN') and not os.getenv('SLACK_BOT_TOKEN').startswith('your-'):
            try:
                logger.info("收集 Slack 資料...")
                slack_collector = SlackCollector(
                    bot_token=os.getenv('SLACK_BOT_TOKEN'),
                    app_token=os.getenv('SLACK_APP_TOKEN')
                )
                
                slack_messages = slack_collector.collect_all_channels(days_back=30)
                data_merger = DataMerger()
                slack_records = data_merger.merge_slack_data(slack_messages)
                all_data.extend(slack_records)
                logger.info(f"✅ Slack 資料收集完成，共 {len(slack_records)} 條記錄")
            except Exception as e:
                logger.error(f"❌ Slack 資料收集失敗: {e}")
        else:
            logger.info("⏭️  跳過 Slack 資料收集（未配置或使用預設值）")
        
        # 收集 GitHub 資料
        if os.getenv('GITHUB_TOKEN') and not os.getenv('GITHUB_TOKEN').startswith('your-'):
            try:
                logger.info("收集 GitHub 資料...")
                github_collector = GitHubCollector(
                    token=os.getenv('GITHUB_TOKEN')
                )
                
                github_data = github_collector.collect_all_repositories(days_back=30)
                data_merger = DataMerger()
                github_records = data_merger.merge_github_data(
                    github_data.get('issues', []),
                    github_data.get('prs', []),
                    github_data.get('commits', [])
                )
                all_data.extend(github_records)
                logger.info(f"✅ GitHub 資料收集完成，共 {len(github_records)} 條記錄")
            except Exception as e:
                logger.error(f"❌ GitHub 資料收集失敗: {e}")
        else:
            logger.info("⏭️  跳過 GitHub 資料收集（未配置或使用預設值）")
        
        # 生成嵌入並存儲到資料庫
        if all_data:
            logger.info(f"開始處理 {len(all_data)} 條記錄...")
            
            # 初始化資料庫存儲和嵌入生成器
            db_storage = PostgreSQLStorage()
            embedding_generator = GeminiEmbeddingGenerator()
            
            processed_count = 0
            for i, record in enumerate(all_data):
                try:
                    # 生成嵌入
                    embedding = embedding_generator.generate_embedding(record.content)
                    record.embedding = embedding
                    
                    # 存儲到資料庫
                    db_storage.insert_record(record)
                    processed_count += 1
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"已處理 {i + 1}/{len(all_data)} 條記錄")
                        
                except Exception as e:
                    logger.error(f"處理記錄 {i} 失敗: {e}")
            
            logger.info(f"🎉 初始化資料收集完成！共處理 {processed_count} 條記錄")
        else:
            logger.warning("⚠️  沒有收集到任何資料")
        
    except Exception as e:
        logger.error(f"❌ 初始化資料收集失敗: {e}")
        return False
    
    return True

def main():
    """主函數"""
    print("🚀 開始初始化資料收集...")
    
    if init_data_collection():
        print("✅ 初始化資料收集完成！")
        return 0
    else:
        print("❌ 初始化資料收集失敗！")
        return 1

if __name__ == "__main__":
    sys.exit(main())
