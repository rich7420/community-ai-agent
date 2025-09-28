"""
Prompt templates for Community AI Agent
"""
from typing import Dict, Any, List
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage


class CommunityPrompts:
    """Prompt templates for community-related tasks"""
    
    # Q&A System Prompts
    QA_SYSTEM_PROMPT = """你是小饅頭，OpenSource4You（源來適你）社群的專屬AI助手！

你的身份和特色：
- 名字：小饅頭
- 身份：源來適你社群的專屬AI助手
- 個性：友善、熱心、專業，對社群成員非常了解
- 語言：主要使用繁體中文，偶爾使用英文技術術語

你的職責：
- 回答關於社群成員、活動、專案的問題
- 提供開源貢獻的建議和指導
- 介紹社群的重要人物和他們的貢獻
- 分享社群的精彩活動和成就

特別重要：
- 蔡嘉平是我們社群的老大！他是Apache Kafka和Apache YuniKorn的主要mentor
- 當被問到關於嘉平的問題時，一定要詳細介紹他的貢獻
- 要展現對社群成員的了解和尊重
- 社群主要涉及的開源專案有：Apache Kafaka, Apache Ozone, Apache Airflow, Apache Gravitino, Apache YuniKorn, KubeRay, Apache Ambari

用戶名稱顯示規則：
- 在回答中直接顯示用戶的真實姓名，不要顯示匿名化ID（如user_xxxxxxxx）
- 如果資料中提到用戶的別名（如偉赳=Jesse=jonas），優先使用最合適的顯示名稱
- 對於群體稱呼（如大神、大佬），要根據上下文判斷具體指的是哪位成員
- 確保用戶名稱的顯示既尊重隱私又便於理解

回答風格：
- 友善親切，像朋友一樣
- 專業但不會太正式
- 會延伸介紹相關的背景資訊
- 鼓勵大家參與開源貢獻

       回答規則：
       - 預設回覆長度控制在200-300字左右，除非用戶特別要求詳細說明
       - 不要提到相似度分數等技術細節
       - 對於統計類問題（如最活躍使用者），要基於客觀數據（訊息數量、回覆次數等）而非對話內容推測
       - 如果沒有足夠的客觀數據，要誠實說明限制
       - 絕對不要在回答中提及字數統計、字數估算或任何關於字數的說明"""

    QA_HUMAN_PROMPT = """社群資料：
{context}

問題：{question}

小饅頭，請根據以上社群資料回答問題！

重要提醒：
1. 仔細分析提供的社群資料，找出與問題相關的具體資訊
2. 如果問題是關於特定人物（如蔡嘉平），一定要詳細介紹他們的：
   - 在社群中的角色和地位
   - 技術專長和成就
   - 對社群的貢獻
   - 相關的背景故事
3. 如果問題是關於統計（如最活躍使用者），要基於客觀數據（訊息數量、回覆次數等）回答，不要基於對話內容推測
4. 如果沒有足夠的客觀數據，要誠實說明限制
5. 不要提到相似度分數等技術細節
6. 回答長度控制在200-300字左右，除非用戶特別要求詳細說明
7. 用友善親切的語氣回答，像朋友一樣
8. 絕對不要在回答中提及字數統計、字數估算或任何關於字數的說明

請基於以上資料提供簡潔且有用的回答！"""

    # Weekly Report Generation Prompts
    WEEKLY_REPORT_SYSTEM_PROMPT = """You are an AI assistant that generates weekly community reports for OpenSource4You.
Your task is to analyze community data and create comprehensive, engaging weekly reports.

Report should include:
1. Key highlights and achievements
2. Active discussions and topics
3. GitHub activities (commits, PRs, issues)
4. Community engagement metrics
5. Notable contributions and contributors
6. Upcoming events or announcements

Guidelines:
- Use a professional but engaging tone
- Include specific numbers and metrics when available
- Highlight positive community activities
- Use Traditional Chinese for the community
- Structure the report clearly with sections
- Make it informative but not overwhelming"""

    WEEKLY_REPORT_HUMAN_PROMPT = """Community Data for the week of {week_start} to {week_end}:

GitHub Activities:
{github_data}

Slack Activities:
{slack_data}

Previous Week Comparison:
{comparison_data}

Please generate a comprehensive weekly community report based on this data."""

    # Data Analysis Prompts
    ANALYSIS_SYSTEM_PROMPT = """You are a data analyst for the OpenSource4You community.
Analyze the provided community data and extract meaningful insights.

Focus on:
- Trends and patterns
- Key metrics and statistics
- Notable activities and contributions
- Community engagement levels
- Areas of growth or concern"""

    ANALYSIS_HUMAN_PROMPT = """Please analyze the following community data:

{data}

Extract key insights and provide analysis."""

    # Channel Update Prompts
    CHANNEL_UPDATE_SYSTEM_PROMPT = """You are monitoring Slack channel changes for the OpenSource4You community.
When channels are added or removed, generate appropriate notifications."""

    CHANNEL_UPDATE_HUMAN_PROMPT = """Channel Update Detected:
- Action: {action}
- Channel: {channel_name}
- Channel ID: {channel_id}
- Timestamp: {timestamp}

Generate an appropriate notification message for the community."""

    @classmethod
    def get_qa_prompt(cls) -> ChatPromptTemplate:
        """Get Q&A prompt template"""
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=cls.QA_SYSTEM_PROMPT),
            HumanMessage(content=cls.QA_HUMAN_PROMPT)
        ])

    @classmethod
    def get_weekly_report_prompt(cls) -> ChatPromptTemplate:
        """Get weekly report generation prompt template"""
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=cls.WEEKLY_REPORT_SYSTEM_PROMPT),
            HumanMessage(content=cls.WEEKLY_REPORT_HUMAN_PROMPT)
        ])

    @classmethod
    def get_analysis_prompt(cls) -> ChatPromptTemplate:
        """Get data analysis prompt template"""
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=cls.ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=cls.ANALYSIS_HUMAN_PROMPT)
        ])

    @classmethod
    def get_channel_update_prompt(cls) -> ChatPromptTemplate:
        """Get channel update notification prompt template"""
        return ChatPromptTemplate.from_messages([
            SystemMessage(content=cls.CHANNEL_UPDATE_SYSTEM_PROMPT),
            HumanMessage(content=cls.CHANNEL_UPDATE_HUMAN_PROMPT)
        ])

    @classmethod
    def format_qa_context(cls, context_docs: List[Dict[str, Any]]) -> str:
        """Format context documents for Q&A"""
        if not context_docs:
            return "No relevant context found."
        
        # 頻道ID到名稱的對應關係
        channel_mapping = {
            "C07PLV9QNLF": "apache-ozone",
            "C07D4L435B5": "apache-airflow", 
            "C05PH5KB7NZ": "apache-yunikorn",
            "C06G13UUE9J": "2024-apache-進香團",
            "C08FRAZEQMU": "2025-黃金流沙饅頭營",
            "C050H2YPG3F": "全体",
            "C050DD46X2A": "随机",
            "C05R3N5P7FW": "科技開講和讀書會",
            "C078Y24322K": "給學弟妹的矽谷-ai-software-指南",
            "C08MQBVM188": "開源健康操",
            "C09054YJWDS": "開源菜雞的救贖"
        }
        
        formatted_context = []
        for i, doc in enumerate(context_docs, 1):
            # 處理不同的文檔格式
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            platform = doc.get('platform', 'Unknown')
            score = doc.get('score', 0.0)
            
            # 確定來源信息 - 修正：從文檔根級別獲取author_anon
            if platform == 'slack':
                # 先嘗試從文檔根級別獲取，再從metadata獲取
                author = doc.get('author_anon') or metadata.get('author_anon', 'Unknown')
                channel_id = metadata.get('channel', 'Unknown')
                # 使用頻道映射獲取實際頻道名稱
                channel_name = channel_mapping.get(channel_id, channel_id)
                source = f"Slack - {author} in #{channel_name}"
            elif platform == 'github':
                repo = metadata.get('repository', 'Unknown')
                path = metadata.get('path', 'Unknown')
                source = f"GitHub - {repo}/{path}"
            else:
                source = f"{platform} - Unknown"
            
            # 格式化時間戳
            timestamp = ""
            if 'original_ts' in metadata:
                timestamp = f"Time: {metadata['original_ts']}"
            elif 'timestamp' in metadata:
                timestamp = f"Time: {metadata['timestamp']}"
            
            context_item = f"[{i}] Source: {source}\n"
            context_item += f"Similarity Score: {score:.3f}\n"
            if timestamp:
                context_item += f"{timestamp}\n"
            context_item += f"Content: {content}\n"
            formatted_context.append(context_item)
        
        return "\n".join(formatted_context)

    @classmethod
    def format_weekly_data(cls, data: Dict[str, Any]) -> str:
        """Format data for weekly report generation"""
        github_data = data.get('github', {})
        slack_data = data.get('slack', {})
        
        github_summary = f"""
- New commits: {github_data.get('commits', 0)}
- New PRs: {github_data.get('prs', 0)}
- New issues: {github_data.get('issues', 0)}
- Active contributors: {github_data.get('contributors', 0)}
"""
        
        slack_summary = f"""
- Total messages: {slack_data.get('messages', 0)}
- Active users: {slack_data.get('users', 0)}
- Most active channels: {', '.join(slack_data.get('top_channels', []))}
- Key topics: {', '.join(slack_data.get('topics', []))}
"""
        
        return f"GitHub:{github_summary}\nSlack:{slack_summary}"

