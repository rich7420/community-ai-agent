import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from ai.grok_llm import GrokLLM
from ai.prompts import CommunityPrompts
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class WeeklyReportGenerator:
    def __init__(self):
        self.db_connection_string = os.getenv("DATABASE_URL")
        self.engine = create_engine(self.db_connection_string)
        self.Session = sessionmaker(bind=self.engine)
        self.llm = GrokLLM.from_environment()
        self.prompt = CommunityPrompts.get_weekly_report_prompt()

    def generate_weekly_report(self, week_start: Optional[datetime] = None, week_end: Optional[datetime] = None) -> Dict[str, Any]:
        if not week_start or not week_end:
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday() + 7)  # Previous Monday
            week_end = week_start + timedelta(days=6)  # Sunday

        # Fetch data
        slack_data = self._get_slack_stats(week_start, week_end)
        github_data = self._get_github_stats(week_start, week_end)
        comparison_data = self._get_comparison_data(week_start - timedelta(days=7), week_start - timedelta(days=1))

        # Prepare input for LLM
        input_data = {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "slack_data": slack_data,
            "github_data": github_data,
            "comparison_data": comparison_data
        }

        # Generate report using LLM
        report_content = self.llm.generate(self.prompt.format_messages(**input_data))

        # Format for Slack (example blocks)
        slack_blocks = self._format_for_slack(report_content)

        return {
            "content": report_content,
            "blocks": slack_blocks,
            "week_start": week_start,
            "week_end": week_end
        }

    def _get_slack_stats(self, start: datetime, end: datetime) -> Dict[str, Any]:
        with self.Session() as session:
            query = text("""
                SELECT 
                    COUNT(*) as messages,
                    COUNT(DISTINCT author_anon) as active_users,
                    json_agg(channel_name) as top_channels
                FROM community_data
                WHERE platform = 'slack' AND timestamp BETWEEN :start AND :end
            """)
            result = session.execute(query, {"start": start, "end": end}).fetchone()
            return {
                "messages": result[0],
                "active_users": result[1],
                "top_channels": result[2][:5]  # Top 5
            }

    def _get_github_stats(self, start: datetime, end: datetime) -> Dict[str, Any]:
        with self.Session() as session:
            query = text("""
                SELECT 
                    COUNT(*) FILTER (WHERE metadata->>'type' = 'commit') as commits,
                    COUNT(*) FILTER (WHERE metadata->>'type' = 'pr') as prs,
                    COUNT(*) FILTER (WHERE metadata->>'type' = 'issue') as issues,
                    COUNT(DISTINCT author_anon) as contributors
                FROM community_data
                WHERE platform = 'github' AND timestamp BETWEEN :start AND :end
            """)
            result = session.execute(query, {"start": start, "end": end}).fetchone()
            return {
                "commits": result[0],
                "prs": result[1],
                "issues": result[2],
                "contributors": result[3]
            }

    def _get_comparison_data(self, prev_start: datetime, prev_end: datetime) -> Dict[str, Any]:
        prev_slack = self._get_slack_stats(prev_start, prev_end)
        prev_github = self._get_github_stats(prev_start, prev_end)
        return {
            "previous_slack_messages": prev_slack["messages"],
            "previous_github_commits": prev_github["commits"]
            # Add more as needed
        }

    def _format_for_slack(self, content: str) -> List[Dict[str, Any]]:
        # Simple markdown to Slack blocks conversion
        sections = content.split("\n\n")
        blocks = []
        for section in sections:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": section}
            })
        return blocks

if __name__ == "__main__":
    generator = WeeklyReportGenerator()
    report = generator.generate_weekly_report()
    print(report["content"])

