import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from ai.qa_system import CommunityQASystem
from reports.weekly_report_generator import WeeklyReportGenerator  # Assuming this exists from stage 36
from scheduler.cron_jobs import CronJobScheduler  # For triggering channel sync

load_dotenv()

# Logger setup
logger = logging.getLogger(__name__)

# Slack App setup
app = App(
    token=os.getenv("SLACK_BOT_TOKEN") or "xoxb-placeholder",
    signing_secret=os.getenv("SLACK_SIGNING_SECRET") or "placeholder-secret"
)

# Database connection for opt-out (placeholder until DB is configured)
# DB_CONNECTION_STRING = os.getenv("DATABASE_URL")  # postgresql://user:pass@host/db
# engine = create_engine(DB_CONNECTION_STRING)
# Session = sessionmaker(bind=engine)

# Initialize Q&A system (assuming it's set up)
# Note: This will fail without proper RAG and LLM initialization
# qa_system = CommunityQASystem()  # Need proper initialization

# Initialize report generator
# report_generator = WeeklyReportGenerator()

# Initialize scheduler for channel sync
# scheduler = CronJobScheduler()

@app.command("/ask-community")
def handle_ask_command(ack, body, client):
    ack()
    question = body["text"]
    try:
        # Placeholder response until Q&A system is properly initialized
        client.chat_postMessage(
            channel=body["channel_id"],
            text=f"Q&A system not yet initialized. Question: {question}",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": f"Q&A system not yet initialized. Question: {question}"}}]
        )
    except Exception as e:
        logger.error(f"Error handling /ask-community: {e}")
        client.chat_postMessage(channel=body["channel_id"], text="Sorry, an error occurred.")

@app.command("/optout")
def handle_optout_command(ack, body, client):
    ack()
    user_id = body["user_id"]
    platform = "slack"
    
    # Placeholder response until database is configured
    client.chat_postMessage(channel=body["channel_id"], text="Opt-out functionality not yet configured. User ID recorded for future implementation.")

@app.command("/weekly-report")
def handle_report_command(ack, body, client):
    ack()
    try:
        # Placeholder response until report generator is properly initialized
        client.chat_postMessage(
            channel=body["channel_id"],
            text="Weekly report generator not yet initialized.",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Weekly report generator not yet initialized."}}]
        )
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}")
        client.chat_postMessage(channel=body["channel_id"], text="Sorry, could not generate report.")

# Event handlers for channel changes
@app.event("channel_created")
def handle_channel_created(event, say):
    logger.info(f"New channel created: {event['channel']['name']}")
    # scheduler.channel_sync_task()  # Trigger sync - commented until scheduler is initialized
    say("Channel list updated.")

@app.event("channel_rename")
def handle_channel_rename(event, say):
    logger.info(f"Channel renamed: {event['channel']['name']}")
    # scheduler.channel_sync_task()  # Commented until scheduler is initialized
    say("Channel list updated.")

@app.event("channel_archive")
def handle_channel_archive(event, say):
    logger.info(f"Channel archived: {event['channel']['id']}")
    # scheduler.channel_sync_task()  # Commented until scheduler is initialized
    say("Channel list updated.")

def start_bot():
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()

if __name__ == "__main__":
    start_bot()
