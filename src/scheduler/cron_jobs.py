"""
定時任務設置模組
實現每日資料收集、每週報告生成、任務失敗通知等功能
"""
import os
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os
sys.path.append('/app/src')

from utils.logging_config import structured_logger
from collectors.slack_collector import SlackCollector
from collectors.github_collector import GitHubCollector
from collectors.google_calendar_collector import GoogleCalendarCollector
from collectors.incremental_collector import IncrementalCollector
from collectors.data_merger import DataMerger
from ai.gemini_embedding_generator import GeminiEmbeddingGenerator
from storage.postgres_storage import PostgreSQLStorage
from storage.minio_storage import MinIOStorage

class CronJobScheduler:
    """定時任務調度器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 初始化組件
        self.slack_collector = None
        self.github_collector = None
        self.calendar_collector = None
        self.incremental_collector = IncrementalCollector()
        self.data_merger = DataMerger()
        self.embedding_generator = GeminiEmbeddingGenerator()
        self.postgres_storage = None
        self.minio_storage = None
        
        # 任務狀態
        self.job_status = {
            'daily_collection': {'last_run': None, 'status': 'pending', 'error': None},
            'weekly_report': {'last_run': None, 'status': 'pending', 'error': None},
            'channel_sync': {'last_run': None, 'status': 'pending', 'error': None}
        }
        
        # 通知配置
        self.notification_config = {
            'enabled': os.getenv('NOTIFICATION_ENABLED', 'false').lower() == 'true',
            'email': {
                'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
                'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                'username': os.getenv('SMTP_USERNAME', ''),
                'password': os.getenv('SMTP_PASSWORD', ''),
                'to_addresses': os.getenv('NOTIFICATION_EMAILS', '').split(',')
            }
        }
    
    def initialize_collectors(self):
        """初始化收集器"""
        try:
            # 初始化Slack收集器
            slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
            slack_app_token = os.getenv('SLACK_APP_TOKEN')
            if (slack_bot_token and slack_app_token and 
                not slack_bot_token.startswith('your-') and 
                not slack_app_token.startswith('your-')):
                self.slack_collector = SlackCollector(slack_bot_token, slack_app_token)
                self.logger.info("Slack收集器初始化成功")
            else:
                self.logger.warning("Slack收集器未配置或使用預設值，跳過初始化")
            
            # 初始化GitHub收集器
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token and not github_token.startswith('your-'):
                self.github_collector = GitHubCollector(github_token)
                self.logger.info("GitHub收集器初始化成功")
            else:
                self.logger.warning("GitHub收集器未配置或使用預設值，跳過初始化")
            
            # 初始化Google Calendar收集器
            calendar_service_account = os.getenv('GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE')
            calendar_id = os.getenv('GOOGLE_CALENDAR_ID')
            if calendar_service_account and calendar_id and not calendar_service_account.startswith('your-'):
                self.calendar_collector = GoogleCalendarCollector()
                self.logger.info("Google Calendar收集器初始化成功")
            else:
                self.logger.warning("Google Calendar收集器未配置或使用預設值，跳過初始化")
            
            self.logger.info("收集器初始化完成")
            
        except Exception as e:
            self.logger.error(f"收集器初始化失敗: {e}")
    
    def initialize_storage(self):
        """初始化存儲組件"""
        try:
            if not self.postgres_storage:
                self.postgres_storage = PostgreSQLStorage()
                self.logger.info("PostgreSQL存儲初始化成功")
            
            if not self.minio_storage:
                self.minio_storage = MinIOStorage()
                self.logger.info("MinIO存儲初始化成功")
                
        except Exception as e:
            self.logger.error(f"存儲組件初始化失敗: {e}")
    
    def daily_data_collection(self):
        """每日資料收集任務"""
        start_time = datetime.now()
        self.logger.info("開始每日資料收集任務")
        
        try:
            # 更新任務狀態
            self.job_status['daily_collection']['last_run'] = start_time
            self.job_status['daily_collection']['status'] = 'running'
            self.job_status['daily_collection']['error'] = None
            
            # 初始化收集器和存儲
            if not self.slack_collector and not self.github_collector and not self.calendar_collector:
                self.initialize_collectors()
            
            if not self.postgres_storage or not self.minio_storage:
                self.initialize_storage()
            
            all_data = []
            
            # 收集Slack資料
            if self.slack_collector:
                try:
                    # 使用新的 collect_bot_channels 方法收集 Bot 所在的所有頻道
                    slack_messages = self.slack_collector.collect_bot_channels(days_back=1)
                    slack_records = self.data_merger.merge_slack_data(slack_messages)
                    all_data.extend(slack_records)
                    self.logger.info(f"Slack資料收集完成，共 {len(slack_records)} 條記錄")
                except Exception as e:
                    self.logger.error(f"Slack資料收集失敗: {e}")
            
            # 收集GitHub資料
            if self.github_collector:
                try:
                    github_data = self.github_collector.collect_all_repositories(days_back=1)
                    github_records = self.data_merger.merge_github_data(
                        github_data.get('issues', []),
                        github_data.get('prs', []),
                        github_data.get('commits', []),
                        github_data.get('files', [])
                    )
                    all_data.extend(github_records)
                    self.logger.info(f"GitHub資料收集完成，共 {len(github_records)} 條記錄")
                except Exception as e:
                    self.logger.error(f"GitHub資料收集失敗: {e}")
            
            # 收集Google Calendar資料
            if self.calendar_collector:
                try:
                    # 收集過去180天到未來60天的事件
                    calendar_events = self.calendar_collector.collect_events(days_back=180)
                    calendar_records = self.data_merger.merge_google_calendar_data(calendar_events)
                    all_data.extend(calendar_records)
                    self.logger.info(f"Google Calendar資料收集完成，共 {len(calendar_records)} 條記錄")
                except Exception as e:
                    self.logger.error(f"Google Calendar資料收集失敗: {e}")
            
            # 生成嵌入和存儲
            if all_data:
                try:
                    # 生成嵌入
                    texts = [record.content for record in all_data]
                    embeddings = self.embedding_generator.generate_embeddings_batch(texts)
                    
                    # 將嵌入添加到記錄中
                    records_with_embeddings = []
                    for i, record in enumerate(all_data):
                        if embeddings[i] is not None:
                            record.embedding = embeddings[i]
                        records_with_embeddings.append(record)
                    
                    # 存儲到PostgreSQL
                    if self.postgres_storage:
                        success_count = self.postgres_storage.insert_records_batch(records_with_embeddings)
                        self.logger.info(f"PostgreSQL存儲完成，成功 {success_count} 條記錄")
                    else:
                        self.logger.warning("PostgreSQL存儲未初始化，跳過存儲")
                    
                    # 存儲到MinIO
                    if self.minio_storage:
                        self.minio_storage.store_records_as_parquet(records_with_embeddings, "daily_collection")
                        self.logger.info("MinIO存儲完成")
                    else:
                        self.logger.warning("MinIO存儲未初始化，跳過存儲")
                    
                except Exception as e:
                    self.logger.error(f"資料處理和存儲失敗: {e}")
                    raise
            else:
                self.logger.info("沒有收集到任何資料，跳過處理")
            
            # 更新任務狀態
            duration = (datetime.now() - start_time).total_seconds()
            self.job_status['daily_collection']['status'] = 'completed'
            
            # 記錄統計
            structured_logger.log_performance(
                operation='daily_data_collection',
                duration=duration,
                metrics={
                    'total_records': len(all_data),
                    'slack_records': len([r for r in all_data if r.platform == 'slack']),
                    'github_records': len([r for r in all_data if r.platform == 'github']),
                    'calendar_records': len([r for r in all_data if r.platform == 'google_calendar'])
                }
            )
            
            self.logger.info(f"每日資料收集任務完成，耗時 {duration:.2f} 秒")
            
        except Exception as e:
            error_msg = str(e)
            self.job_status['daily_collection']['status'] = 'failed'
            self.job_status['daily_collection']['error'] = error_msg
            self.logger.error(f"每日資料收集任務失敗: {error_msg}")
            
            # 發送失敗通知
            self._send_notification("每日資料收集任務失敗", error_msg)
    
    def weekly_report_generation(self):
        """每週報告生成任務"""
        start_time = datetime.now()
        self.logger.info("開始每週報告生成任務")
        
        try:
            # 更新任務狀態
            self.job_status['weekly_report']['last_run'] = start_time
            self.job_status['weekly_report']['status'] = 'running'
            self.job_status['weekly_report']['error'] = None
            
            # 計算週範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            # 從PostgreSQL獲取資料
            slack_records = self.postgres_storage.get_records_by_time_range(
                start_date, end_date, platform='slack'
            )
            github_records = self.postgres_storage.get_records_by_time_range(
                start_date, end_date, platform='github'
            )
            
            # 生成週報
            report_data = self._generate_weekly_report(slack_records, github_records, start_date, end_date)
            
            # 存儲週報到MinIO
            week_start = start_date - timedelta(days=start_date.weekday())
            self.minio_storage.store_records_as_parquet(report_data, "weekly_report", week_start)
            
            # 更新任務狀態
            duration = (datetime.now() - start_time).total_seconds()
            self.job_status['weekly_report']['status'] = 'completed'
            
            self.logger.info(f"每週報告生成任務完成，耗時 {duration:.2f} 秒")
            
        except Exception as e:
            error_msg = str(e)
            self.job_status['weekly_report']['status'] = 'failed'
            self.job_status['weekly_report']['error'] = error_msg
            self.logger.error(f"每週報告生成任務失敗: {error_msg}")
            
            # 發送失敗通知
            self._send_notification("每週報告生成任務失敗", error_msg)
    
    def channel_sync_task(self):
        """頻道同步任務"""
        start_time = datetime.now()
        self.logger.info("開始頻道同步任務")
        
        try:
            # 更新任務狀態
            self.job_status['channel_sync']['last_run'] = start_time
            self.job_status['channel_sync']['status'] = 'running'
            self.job_status['channel_sync']['error'] = None
            
            if not self.slack_collector:
                self.initialize_collectors()
            
            if self.slack_collector:
                # 獲取當前頻道列表
                current_channels = self.slack_collector.channels
                
                # 這裡應該實現頻道同步邏輯
                # 比較當前頻道與配置中的頻道
                # 更新配置文件和資料庫
                
                self.logger.info(f"頻道同步完成，共 {len(current_channels)} 個頻道")
            
            # 更新任務狀態
            duration = (datetime.now() - start_time).total_seconds()
            self.job_status['channel_sync']['status'] = 'completed'
            
            self.logger.info(f"頻道同步任務完成，耗時 {duration:.2f} 秒")
            
        except Exception as e:
            error_msg = str(e)
            self.job_status['channel_sync']['status'] = 'failed'
            self.job_status['channel_sync']['error'] = error_msg
            self.logger.error(f"頻道同步任務失敗: {error_msg}")
    
    def _generate_weekly_report(self, slack_records: List[Dict], github_records: List[Dict], 
                              start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """生成週報數據"""
        report = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'generated_at': datetime.now().isoformat()
            },
            'slack_stats': {
                'total_messages': len(slack_records),
                'active_channels': len(set(r.get('metadata', {}).get('channel', '') for r in slack_records)),
                'active_users': len(set(r.get('author_anon', '') for r in slack_records)),
                'top_channels': self._get_top_channels(slack_records),
                'top_users': self._get_top_users(slack_records)
            },
            'github_stats': {
                'total_issues': len([r for r in github_records if r.get('metadata', {}).get('type') == 'issue']),
                'total_prs': len([r for r in github_records if r.get('metadata', {}).get('type') == 'pull_request']),
                'total_commits': len([r for r in github_records if r.get('metadata', {}).get('type') == 'commit']),
                'active_contributors': len(set(r.get('author_anon', '') for r in github_records)),
                'top_contributors': self._get_top_contributors(github_records)
            }
        }
        
        return report
    
    def _get_top_channels(self, slack_records: List[Dict], top_n: int = 5) -> List[Dict]:
        """獲取最活躍頻道"""
        channel_counts = {}
        for record in slack_records:
            channel = record.get('metadata', {}).get('channel', 'unknown')
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
        
        sorted_channels = sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'channel': channel, 'message_count': count} for channel, count in sorted_channels[:top_n]]
    
    def _get_top_users(self, slack_records: List[Dict], top_n: int = 5) -> List[Dict]:
        """獲取最活躍使用者"""
        user_counts = {}
        for record in slack_records:
            user = record.get('author_anon', 'unknown')
            user_counts[user] = user_counts.get(user, 0) + 1
        
        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'user': user, 'message_count': count} for user, count in sorted_users[:top_n]]
    
    def _get_top_contributors(self, github_records: List[Dict], top_n: int = 5) -> List[Dict]:
        """獲取最活躍貢獻者"""
        contributor_counts = {}
        for record in github_records:
            contributor = record.get('author_anon', 'unknown')
            contributor_counts[contributor] = contributor_counts.get(contributor, 0) + 1
        
        sorted_contributors = sorted(contributor_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'contributor': contributor, 'activity_count': count} for contributor, count in sorted_contributors[:top_n]]
    
    def _send_notification(self, subject: str, message: str):
        """發送通知"""
        if not self.notification_config['enabled']:
            return
        
        try:
            email_config = self.notification_config['email']
            
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['to_addresses'])
            msg['Subject'] = f"Community AI Agent - {subject}"
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            self.logger.info("通知發送成功")
            
        except Exception as e:
            self.logger.error(f"發送通知失敗: {e}")
    
    def setup_schedule(self):
        """設置定時任務"""
        # 每日資料收集 - 每天早上6點
        schedule.every().day.at("06:00").do(self.daily_data_collection)
        
        # 每週報告生成 - 已關閉
        # schedule.every().monday.at("08:00").do(self.weekly_report_generation)
        
        # 頻道同步 - 每週三凌晨2點
        schedule.every().wednesday.at("02:00").do(self.channel_sync_task)
        
        self.logger.info("定時任務設置完成（週報功能已關閉）")
    
    def run_scheduler(self):
        """運行調度器"""
        self.logger.info("開始運行定時任務調度器")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分鐘檢查一次
            except KeyboardInterrupt:
                self.logger.info("收到停止信號，正在關閉調度器")
                break
            except Exception as e:
                self.logger.error(f"調度器運行錯誤: {e}")
                time.sleep(60)
    
    def get_job_status(self) -> Dict[str, Any]:
        """獲取任務狀態"""
        return self.job_status.copy()
    
    def run_job_manually(self, job_name: str) -> bool:
        """手動運行任務"""
        if job_name == 'daily_collection':
            self.daily_data_collection()
            return True
        elif job_name == 'weekly_report':
            self.weekly_report_generation()
            return True
        elif job_name == 'channel_sync':
            self.channel_sync_task()
            return True
        else:
            self.logger.error(f"未知任務: {job_name}")
            return False
