"""
Q&A System combining RAG and LLM
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import json

from langchain.chains import LLMChain
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler

from ai.google_llm import GoogleLLM
from ai.rag_system import CommunityRAGSystem
from ai.prompts import CommunityPrompts
from utils.user_display_helper import UserDisplayHelper
from utils.logging_config import structured_logger
from mcp.user_stats_mcp import get_slack_user_stats, get_slack_activity_summary
from mcp.calendar_mcp_fixed import CalendarMCPFixed
from cache.answer_cache import get_cache

logger = logging.getLogger(__name__)


class CommunityQASystem:
    """Q&A system for community data using RAG + LLM"""
    
    def __init__(
        self,
        rag_system: CommunityRAGSystem,
        llm: GoogleLLM,
        memory_size: int = 10,
        max_context_length: int = 4000
    ):
        """
        Initialize Q&A system
        
        Args:
            rag_system: RAG system for document retrieval
            llm: Language model for generation
            memory_size: Number of conversation turns to remember
            max_context_length: Maximum context length for LLM
        """
        self.rag_system = rag_system
        self.llm = llm
        self.max_context_length = max_context_length
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Initialize cache
        self.cache = get_cache()
        
        # Initialize MCP services
        self.calendar_mcp = CalendarMCPFixed()
        self.user_display_helper = UserDisplayHelper()
        
        # Initialize prompt templates
        self.qa_prompt = CommunityPrompts.get_qa_prompt()
        
        # Initialize LLM chain
        self.qa_chain = LLMChain(
            llm=llm,
            prompt=self.qa_prompt,
            memory=self.memory,
            verbose=True
        )
        
        structured_logger.info("Q&A system initialized", extra={
            "memory_size": memory_size,
            "max_context_length": max_context_length
        })

    def ask_question(
        self,
        question: str,
        k: int = 5,  # 增加到5個文檔
        score_threshold: float = 0.5,
        source_filter: Optional[str] = None,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """
        Ask a question and get an answer using RAG
        
        Args:
            question: The question to ask
            k: Number of documents to retrieve
            score_threshold: Minimum similarity score for documents
            source_filter: Optional source type filter (slack, github, etc.)
            include_sources: Whether to include source information
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        try:
            # Check cache first
            cached_result = self.cache.get_cached_answer(question)
            if cached_result:
                structured_logger.info("Using cached answer", extra={
                    "question": question[:50] + "..." if len(question) > 50 else question,
                    "cached": True
                })
                return {
                    "question": question,
                    "answer": cached_result["answer"],
                    "sources": cached_result["sources"],
                    "timestamp": datetime.now().isoformat(),
                    "sources_used": len(cached_result["sources"]),
                    "context_length": len(cached_result["answer"]),
                    "cached": True,
                    "cache_timestamp": cached_result["cache_timestamp"]
                }
            
            # 檢查是否為統計類問題
            if self._is_stats_question(question):
                return self._handle_stats_question(question)
            
            # 檢查是否為用戶活躍度查詢
            if self._is_user_activity_query(question):
                return self._handle_user_activity_query(question)
            
            # 檢查是否為日曆查詢
            if self._is_calendar_query(question):
                return self._handle_calendar_query(question)
            
            # Prepare filter for RAG
            filter_dict = None
            if source_filter:
                filter_dict = {"source_type": source_filter}
            
            # Retrieve enhanced context including project descriptions
            context = self.rag_system.get_enhanced_context(
                query=question,
                k=k
            )
            
            # Also get relevant documents for sources if needed
            relevant_docs = self.rag_system.get_relevant_documents(
                query=question,
                k=k,
                score_threshold=score_threshold,
                filter=filter_dict
            )
            
            # Prepare input for LLM
            chain_input = {
                "question": question,
                "context": context
            }
            
            # Generate answer
            try:
                # Direct LLM call (simplified approach)
                prompt = f"{CommunityPrompts.QA_SYSTEM_PROMPT}\n\n{CommunityPrompts.QA_HUMAN_PROMPT}".format(
                    context=context,
                    question=question
                )
                answer = self.llm._call(prompt)
                if hasattr(answer, 'content'):
                    answer = answer.content
                else:
                    answer = str(answer)
                
                # 反匿名化用戶名稱並解析用戶引用
                from utils.pii_filter import PIIFilter
                pii_filter = PIIFilter()
                answer = pii_filter.resolve_user_references(answer)
                
            except Exception as direct_error:
                logger.error(f"Direct LLM call failed: {direct_error}")
                answer = "I apologize, but I'm experiencing technical difficulties. Please try again later."
            
            # Prepare response
            result = {
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "sources_used": len(relevant_docs),
                "context_length": len(context)
            }
            
            if include_sources:
                sources = [
                    {
                        "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                        "metadata": doc["metadata"],
                        "score": doc["score"]
                    }
                    for doc in relevant_docs
                ]
                result["sources"] = sources
                
                # Cache the answer for future use
                self.cache.cache_answer(question, answer, sources)
            
            structured_logger.info("Question answered", extra={
                "question": question,
                "answer_length": len(answer),
                "sources_used": len(relevant_docs),
                "source_filter": source_filter
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            return {
                "question": question,
                "answer": f"Sorry, I encountered an error while processing your question: {str(e)}",
                "error": True,
                "timestamp": datetime.now().isoformat()
            }
    
    def _is_stats_question(self, question: str) -> bool:
        """檢查是否為統計類問題"""
        stats_keywords = [
            "最活躍", "活躍", "前三個", "前幾名", "最多", "統計", 
            "發訊息", "回覆", "emoji", "使用次數", "活動量"
        ]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in stats_keywords)
    
    def _is_user_activity_query(self, question: str) -> bool:
        """檢查是否為用戶活躍度查詢"""
        # 更精確的用戶查詢模式
        user_query_patterns = [
            r'(.+?)是誰[？?]?$',  # "XXX是誰？"
            r'(.+?)的活躍度',     # "XXX的活躍度"
            r'(.+?)的討論',       # "XXX的討論"
            r'(.+?)的參與',       # "XXX的參與"
            r'(.+?)發了多少',     # "XXX發了多少"
            r'(.+?)的訊息',       # "XXX的訊息"
            r'(.+?)的貢獻',       # "XXX的貢獻"
        ]
        
        import re
        for pattern in user_query_patterns:
            if re.search(pattern, question):
                return True
        
        # 檢查是否包含具體的用戶名稱（中文姓名、英文姓名、已知的mentor名稱）
        known_users = [
            "蔡嘉平", "嘉平", "Jesse", "莊偉赳", "偉赳", "劉哲佑", "Jason", 
            "大神", "大佬", "mentor", "mentors"
        ]
        
        question_lower = question.lower()
        for user in known_users:
            if user in question and any(keyword in question for keyword in ["是誰", "活躍", "討論", "參與", "貢獻", "訊息"]):
                return True
        
        return False
    
    def _handle_user_activity_query(self, question: str) -> Dict[str, Any]:
        """處理用戶活躍度查詢 - 改進版本，提供詳細的用戶分析"""
        try:
            import re
            import signal
            import time
            
            # 提取用戶名稱 - 改進的模式匹配
            user_name_patterns = [
                r'([^？?]+)(?:是誰|活躍|討論|參與|發過什麼|的訊息|的內容)',
                r'(?:誰是|介紹|分析|查詢)\s*([^？?]+)',
                r'([^？?]+)\s*(?:的活躍度|的討論|的參與|的訊息|的內容)',
                r'用戶\s*([^？?]+)',
                r'([^？?]+)\s*發過什麼',
                r'([^？?]+)\s*的訊息內容'
            ]
            
            user_name = None
            for pattern in user_name_patterns:
                match = re.search(pattern, question)
                if match:
                    user_name = match.group(1).strip()
                    # 清理用戶名稱
                    user_name = re.sub(r'[的誰是？?]', '', user_name).strip()
                    if user_name:
                        break
            
            if not user_name:
                return {
                    "question": question,
                    "answer": "抱歉，我無法從您的問題中識別出要查詢的用戶名稱。請提供更具體的用戶名稱，例如：'Jesse是誰？' 或 'Jesse發過什麼訊息？'",
                    "timestamp": datetime.now().isoformat(),
                    "sources_used": 0,
                    "context_length": 0
                }
            
            # 設置查詢超時（15秒）
            def timeout_handler(signum, frame):
                raise TimeoutError("用戶查詢超時")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(15)  # 15秒超時
            
            try:
                start_time = time.time()
                # 使用改進的用戶分析
                user_analysis = self._get_detailed_user_analysis(user_name)
                query_time = time.time() - start_time
                
                signal.alarm(0)  # 取消超時
                
            except TimeoutError:
                signal.alarm(0)
                return {
                    "question": question,
                    "answer": f"查詢用戶 {user_name} 的資訊超時，請稍後再試或聯繫管理員。",
                    "timestamp": datetime.now().isoformat(),
                    "sources_used": 0,
                    "context_length": 0,
                    "timeout": True
                }
            
            if not user_analysis.get("user_found", False):
                return {
                    "question": question,
                    "answer": f"抱歉，我沒有找到用戶 '{user_name}' 的相關信息。請確認用戶名稱是否正確。",
                    "timestamp": datetime.now().isoformat(),
                    "sources_used": 0,
                    "context_length": 0,
                    "query_time": query_time
                }
            
            # 生成詳細的用戶分析報告
            answer = self._generate_detailed_user_report(user_analysis)
            
            return {
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "sources_used": 1,
                "context_length": len(answer),
                "user_analysis": user_analysis
            }
            
        except Exception as e:
            logger.error(f"處理用戶活躍度查詢失敗: {e}")
            return {
                "question": question,
                "answer": f"抱歉，處理用戶活躍度查詢時發生錯誤：{str(e)}",
                "timestamp": datetime.now().isoformat(),
                "sources_used": 0,
                "context_length": 0
            }
    
    def _get_detailed_user_analysis(self, user_name: str) -> Dict[str, Any]:
        """獲取詳細的用戶分析信息"""
        try:
            from src.storage.connection_pool import get_db_connection, return_db_connection
            from psycopg2.extras import RealDictCursor
            import time
            
            start_time = time.time()
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 查找用戶映射 - 選擇有最多數據的用戶
            cur.execute("""
                WITH user_candidates AS (
                    SELECT 
                        unm.anonymized_id, 
                        unm.display_name, 
                        unm.real_name, 
                        unm.aliases, 
                        unm.group_terms,
                        COUNT(cd.id) as message_count
                    FROM user_name_mappings unm
                    LEFT JOIN community_data cd ON cd.author_anon = unm.anonymized_id AND cd.platform = 'slack'
                    WHERE unm.display_name ILIKE %s OR unm.real_name ILIKE %s 
                       OR %s = ANY(unm.aliases) OR %s = ANY(unm.group_terms)
                    GROUP BY unm.anonymized_id, unm.display_name, unm.real_name, unm.aliases, unm.group_terms
                    ORDER BY message_count DESC
                    LIMIT 1
                )
                SELECT anonymized_id, display_name, real_name, aliases, group_terms
                FROM user_candidates
            """, (f"%{user_name}%", f"%{user_name}%", user_name, user_name))
            
            user_result = cur.fetchone()
            if not user_result:
                cur.close()
                return_db_connection(conn)
                return {
                    "user_found": False,
                    "message": f"未找到用戶 {user_name}",
                    "query_time": time.time() - start_time
                }
            
            anonymized_id = user_result['anonymized_id']
            display_name = user_result['display_name']
            real_name = user_result['real_name']
            
            # 獲取用戶統計信息
            cur.execute("""
                SELECT 
                    COUNT(*) as message_count,
                    COUNT(CASE WHEN metadata->>'thread_ts' IS NOT NULL THEN 1 END) as reply_count,
                    COUNT(CASE WHEN metadata->>'thread_ts' IS NULL OR metadata->>'thread_ts' = '' THEN 1 END) as main_message_count,
                    COUNT(DISTINCT metadata->>'channel') as channel_count,
                    MIN(timestamp) as first_activity,
                    MAX(timestamp) as last_activity,
                    COUNT(CASE WHEN metadata->>'emoji' IS NOT NULL THEN 1 END) as emoji_count
                FROM community_data 
                WHERE author_anon = %s AND platform = 'slack'
            """, (anonymized_id,))
            
            stats = cur.fetchone()
            
            # 獲取頻道活躍度
            cur.execute("""
                SELECT 
                    metadata->>'channel' as channel_id,
                    metadata->>'channel_name' as channel_name,
                    COUNT(*) as message_count
                FROM community_data 
                WHERE author_anon = %s AND platform = 'slack'
                GROUP BY metadata->>'channel', metadata->>'channel_name'
                ORDER BY message_count DESC
                LIMIT 5
            """, (anonymized_id,))
            
            channel_stats = cur.fetchall()
            
            # 獲取最近的訊息內容
            cur.execute("""
                SELECT 
                    content,
                    timestamp,
                    metadata->>'channel_name' as channel_name
                FROM community_data 
                WHERE author_anon = %s AND platform = 'slack'
                ORDER BY timestamp DESC
                LIMIT 10
            """, (anonymized_id,))
            
            recent_messages = cur.fetchall()
            
            cur.close()
            return_db_connection(conn)
            
            query_time = time.time() - start_time
            
            return {
                "user_found": True,
                "display_name": display_name,
                "real_name": real_name,
                "anonymized_id": anonymized_id,
                "message_count": stats['message_count'],
                "reply_count": stats['reply_count'],
                "main_message_count": stats['main_message_count'],
                "channel_count": stats['channel_count'],
                "emoji_count": stats['emoji_count'],
                "first_activity": stats['first_activity'].isoformat() if stats['first_activity'] else None,
                "last_activity": stats['last_activity'].isoformat() if stats['last_activity'] else None,
                "channel_stats": [
                    {
                        "channel_id": ch['channel_id'],
                        "channel_name": ch['channel_name'],
                        "message_count": ch['message_count']
                    } for ch in channel_stats
                ],
                "recent_messages": [
                    {
                        "content": msg['content'],
                        "timestamp": msg['timestamp'].isoformat(),
                        "channel_name": msg['channel_name']
                    } for msg in recent_messages
                ],
                "query_time": query_time
            }
            
        except Exception as e:
            logger.error(f"獲取詳細用戶分析失敗: {e}")
            return {
                "user_found": False,
                "error": str(e),
                "query_time": time.time() - start_time if 'start_time' in locals() else 0
            }
    
    def _generate_detailed_user_report(self, user_analysis: Dict[str, Any]) -> str:
        """生成詳細的用戶分析報告"""
        try:
            display_name = user_analysis["display_name"]
            real_name = user_analysis.get("real_name", display_name)
            message_count = user_analysis["message_count"]
            reply_count = user_analysis["reply_count"]
            main_message_count = user_analysis["main_message_count"]
            channel_count = user_analysis["channel_count"]
            emoji_count = user_analysis["emoji_count"]
            last_activity = user_analysis["last_activity"]
            
            # 構建詳細報告
            report_parts = [
                f"## 🎯 {display_name} 是誰？",
                f"",
                f"**{display_name}** 是Apache Local Community Taipei社群中的一個活躍成員！",
                f""
            ]
            
            # 基本統計
            report_parts.extend([
                f"### 📊 **基本統計**",
                f"- **總訊息數**：{message_count} 條",
                f"- **回覆數**：{reply_count} 次",
                f"- **主訊息數**：{main_message_count} 條",
                f"- **參與頻道數**：{channel_count} 個",
                f"- **Emoji使用**：{emoji_count} 次",
                f"- **最後活動時間**：{last_activity[:10] if last_activity else '未知'}",
                f""
            ])
            
            # 頻道活躍度
            if user_analysis.get("channel_stats"):
                report_parts.extend([
                    f"### 🏆 **最活躍頻道**",
                ])
                for i, channel in enumerate(user_analysis["channel_stats"], 1):
                    channel_name = channel.get("channel_name", f"頻道{channel['channel_id']}")
                    message_count = channel["message_count"]
                    report_parts.append(f"{i}. **#{channel_name}**：{message_count} 條訊息")
                report_parts.append("")
            
            # 最近訊息內容
            if user_analysis.get("recent_messages"):
                report_parts.extend([
                    f"### 💬 **最近訊息內容**",
                ])
                for i, msg in enumerate(user_analysis["recent_messages"][:5], 1):
                    content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                    timestamp = msg["timestamp"][:10] if msg["timestamp"] else "未知時間"
                    channel_name = msg.get("channel_name", "未知頻道")
                    report_parts.append(f"{i}. **[{timestamp}]** 在 #{channel_name}：")
                    report_parts.append(f"   {content}")
                    report_parts.append("")
            
            # 個性特徵分析
            report_parts.extend([
                f"### 🔍 **個性特徵分析**",
            ])
            
            # 基於數據分析個性特徵
            personality_traits = []
            
            if reply_count > main_message_count:
                personality_traits.append("活躍的回覆者，喜歡參與討論")
            elif main_message_count > reply_count:
                personality_traits.append("經常發起新話題")
            
            if channel_count > 3:
                personality_traits.append("參與多個頻道，社群參與度高")
            
            if emoji_count > message_count * 0.3:
                personality_traits.append("喜歡使用表情符號，表達方式生動")
            
            if message_count > 50:
                personality_traits.append("社群中的活躍成員")
            elif message_count > 20:
                personality_traits.append("中等活躍度的參與者")
            else:
                personality_traits.append("偶爾參與討論的成員")
            
            for trait in personality_traits:
                report_parts.append(f"- {trait}")
            
            report_parts.extend([
                f"",
                f"### 📈 **活躍度排名**",
                f"根據過去30天的數據，{display_name} 在社群中的活躍度排名需要查詢整體統計來確定。",
                f"",
                f"---",
                f"*以上分析基於 {display_name} 在Slack社群中的實際活動數據*"
            ])
            
            return "\n".join(report_parts)
            
        except Exception as e:
            logger.error(f"生成詳細用戶報告失敗: {e}")
            return f"抱歉，生成用戶分析報告時發生錯誤：{str(e)}"
    
    def _handle_stats_question(self, question: str) -> Dict[str, Any]:
        """處理統計類問題"""
        try:
            # 獲取Slack用戶統計數據
            user_stats = get_slack_user_stats(days_back=30, limit=3)
            activity_summary = get_slack_activity_summary(days_back=30)
            
            if not user_stats:
                return {
                    "question": question,
                    "answer": "抱歉，目前沒有足夠的Slack活動數據來統計最活躍的使用者。",
                    "timestamp": datetime.now().isoformat(),
                    "sources_used": 0,
                    "context_length": 0
                }
            
            # 生成基於客觀數據的回答
            answer = self._generate_stats_answer(question, user_stats, activity_summary)
            
            return {
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "sources_used": len(user_stats),
                "context_length": len(str(user_stats)),
                "stats_data": user_stats
            }
            
        except Exception as e:
            logger.error(f"處理統計問題失敗: {e}")
            return {
                "question": question,
                "answer": f"抱歉，處理統計問題時發生錯誤: {str(e)}",
                "error": True,
                "timestamp": datetime.now().isoformat()
            }
    
    def _is_calendar_query(self, question: str) -> bool:
        """檢查是否為日曆查詢"""
        calendar_keywords = [
            "日曆", "行事曆", "會議", "活動", "事件", "時間", "什麼時候", "何時",
            "科技開講", "syncup", "sync up", "聚會", "講座", "工作坊",
            "今天", "明天", "本週", "下週", "這個月", "下個月"
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in calendar_keywords)
    
    def _handle_calendar_query(self, question: str) -> Dict[str, Any]:
        """處理日曆查詢"""
        try:
            import re
            from datetime import datetime, timedelta
            
            # 檢測查詢類型
            if any(keyword in question.lower() for keyword in ["科技開講", "syncup", "sync up"]):
                # 搜索特定事件
                events = self.calendar_mcp.search_events("科技開講", limit=5)
                if not events:
                    events = self.calendar_mcp.search_events("syncup", limit=5)
            elif any(keyword in question.lower() for keyword in ["今天", "今日"]):
                # 今天的事件
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow = today + timedelta(days=1)
                events = self.calendar_mcp.get_events_by_date_range(today, tomorrow, limit=10)
            elif any(keyword in question.lower() for keyword in ["明天", "明日"]):
                # 明天的事件
                tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                day_after = tomorrow + timedelta(days=1)
                events = self.calendar_mcp.get_events_by_date_range(tomorrow, day_after, limit=10)
            elif any(keyword in question.lower() for keyword in ["本週", "這週"]):
                # 本週的事件
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                week_end = today + timedelta(days=7)
                events = self.calendar_mcp.get_events_by_date_range(today, week_end, limit=20)
            elif any(keyword in question.lower() for keyword in ["下週", "下週"]):
                # 下週的事件
                next_week = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=7)
                week_after = next_week + timedelta(days=7)
                events = self.calendar_mcp.get_events_by_date_range(next_week, week_after, limit=20)
            elif any(keyword in question.lower() for keyword in ["11月", "十一月"]):
                # 11月的事件
                start_date = datetime(2025, 11, 1).replace(tzinfo=timezone.utc)
                end_date = datetime(2025, 12, 1).replace(tzinfo=timezone.utc)
                events = self.calendar_mcp.get_events_by_date_range(start_date, end_date, limit=20)
            elif any(keyword in question.lower() for keyword in ["10月", "十月"]):
                # 10月的事件
                start_date = datetime(2025, 10, 1).replace(tzinfo=timezone.utc)
                end_date = datetime(2025, 11, 1).replace(tzinfo=timezone.utc)
                events = self.calendar_mcp.get_events_by_date_range(start_date, end_date, limit=20)
            elif any(keyword in question.lower() for keyword in ["12月", "十二月"]):
                # 12月的事件
                start_date = datetime(2025, 12, 1).replace(tzinfo=timezone.utc)
                end_date = datetime(2026, 1, 1).replace(tzinfo=timezone.utc)
                events = self.calendar_mcp.get_events_by_date_range(start_date, end_date, limit=20)
            else:
                # 默認獲取未來7天的事件
                events = self.calendar_mcp.get_upcoming_events(days_ahead=7, limit=10)
            
            if not events:
                return {
                    "question": question,
                    "answer": "目前沒有找到相關的日曆事件。",
                    "timestamp": datetime.now().isoformat(),
                    "sources_used": 0,
                    "context_length": 0
                }
            
            # 格式化事件信息
            formatted_events = self.calendar_mcp.format_events_for_display(events)
            
            answer = f"📅 **日曆事件查詢結果：**\n\n{formatted_events}"
            
            return {
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "sources_used": len(events),
                "context_length": len(answer),
                "calendar_events": [event.__dict__ for event in events]
            }
            
        except Exception as e:
            logger.error(f"處理日曆查詢失敗: {e}")
            return {
                "question": question,
                "answer": f"抱歉，處理日曆查詢時發生錯誤: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "sources_used": 0,
                "context_length": 0
            }
    
    def _generate_stats_answer(self, question: str, user_stats: List[Dict], activity_summary: Dict) -> str:
        """生成基於統計數據的回答"""
        if not user_stats:
            return "目前沒有足夠的數據來回答這個問題。"
        
        # 簡潔的回答格式
        answer_parts = []
        
        # 添加摘要信息
        answer_parts.append(f"根據過去30天的客觀數據統計：")
        
        # 列出最活躍的前三名用戶
        for i, user in enumerate(user_stats[:3], 1):
            # 確保使用真實用戶名稱
            user_name = self.user_display_helper.get_display_name(user['user_name'], 'slack')
            message_count = user['message_count']
            reply_count = user['reply_count']
            emoji_given = user['emoji_given']
            
            answer_parts.append(
                f"{i}. **{user_name}** - 發送{message_count}條訊息，"
                f"回覆{reply_count}次，給出{emoji_given}個emoji"
            )
        
        # 添加總體統計
        answer_parts.append(
            f"\n總體統計：{activity_summary['total_users']}位活躍用戶，"
            f"共{activity_summary['total_messages']}條訊息，"
            f"平均每人{activity_summary['avg_messages_per_user']}條訊息。"
        )
        
        return "\n".join(answer_parts)

    def ask_follow_up_question(
        self,
        question: str,
        k: int = 5,
        score_threshold: float = 0.7,
        source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ask a follow-up question with conversation context
        
        Args:
            question: The follow-up question
            k: Number of documents to retrieve
            score_threshold: Minimum similarity score for documents
            source_filter: Optional source type filter
            
        Returns:
            Dictionary with answer and context
        """
        try:
            # Get conversation history
            chat_history = self.memory.chat_memory.messages
            
            # Build context-aware query
            context_query = self._build_context_query(question, chat_history)
            
            # Ask question with context
            result = self.ask_question(
                question=context_query,
                k=k,
                score_threshold=score_threshold,
                source_filter=source_filter
            )
            
            # Update the result with the original question
            result["original_question"] = question
            result["context_query"] = context_query
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to answer follow-up question: {e}")
            return {
                "question": question,
                "answer": f"Sorry, I encountered an error while processing your follow-up question: {str(e)}",
                "error": True,
                "timestamp": datetime.now().isoformat()
            }

    def _build_context_query(self, question: str, chat_history: List[BaseMessage]) -> str:
        """
        Build a context-aware query from question and chat history
        
        Args:
            question: Current question
            chat_history: Previous conversation messages
            
        Returns:
            Context-aware query string
        """
        if not chat_history:
            return question
        
        # Extract recent questions and answers
        recent_context = []
        for i, message in enumerate(chat_history[-6:]):  # Last 3 Q&A pairs
            if isinstance(message, HumanMessage):
                recent_context.append(f"Previous question: {message.content}")
            elif isinstance(message, SystemMessage) and "answer" in message.content.lower():
                recent_context.append(f"Previous answer: {message.content}")
        
        if recent_context:
            context_str = "\n".join(recent_context)
            return f"Context from previous conversation:\n{context_str}\n\nCurrent question: {question}"
        
        return question

    def search_community_data(
        self,
        query: str,
        source_type: Optional[str] = None,
        limit: int = 10,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Search community data without generating an answer
        
        Args:
            query: Search query
            source_type: Optional source type filter
            limit: Maximum number of results
            include_metadata: Whether to include full metadata
            
        Returns:
            Dictionary with search results
        """
        try:
            # Prepare filter
            filter_dict = None
            if source_type:
                filter_dict = {"source_type": source_type}
            
            # Perform search
            results = self.rag_system.similarity_search_with_score(
                query=query,
                k=limit,
                filter=filter_dict
            )
            
            # Format results
            search_results = []
            for doc, score in results:
                result_item = {
                    "content": doc.page_content,
                    "score": score,
                    "source_type": doc.metadata.get("source_type", "unknown")
                }
                
                if include_metadata:
                    result_item["metadata"] = doc.metadata
                
                search_results.append(result_item)
            
            return {
                "query": query,
                "results": search_results,
                "total_results": len(search_results),
                "source_filter": source_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Community data search failed: {e}")
            return {
                "query": query,
                "results": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the current conversation history
        
        Returns:
            List of conversation messages
        """
        try:
            messages = self.memory.chat_memory.messages
            history = []
            
            for i, message in enumerate(messages):
                history.append({
                    "index": i,
                    "type": type(message).__name__,
                    "content": message.content,
                    "timestamp": datetime.now().isoformat()
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    def clear_conversation(self) -> bool:
        """
        Clear the conversation history
        
        Returns:
            True if successful
        """
        try:
            self.memory.clear()
            logger.info("Conversation history cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear conversation: {e}")
            return False

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics
        
        Returns:
            Dictionary with system statistics
        """
        try:
            # Get RAG system stats
            rag_stats = self.rag_system.get_collection_stats()
            
            # Get conversation stats
            conversation_length = len(self.memory.chat_memory.messages)
            
            # Get LLM info
            llm_info = self.llm.get_model_info()
            
            return {
                "rag_system": rag_stats,
                "conversation_length": conversation_length,
                "llm_info": llm_info,
                "max_context_length": self.max_context_length,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {"error": str(e)}

    def test_system(self) -> Dict[str, Any]:
        """
        Test the Q&A system with a simple question
        
        Returns:
            Test results
        """
        try:
            test_question = "What is this community about?"
            
            # Test basic question answering
            result = self.ask_question(
                question=test_question,
                k=3,
                score_threshold=0.5
            )
            
            # Test system stats
            stats = self.get_system_stats()
            
            return {
                "test_question": test_question,
                "test_result": result,
                "system_stats": stats,
                "test_passed": not result.get("error", False),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System test failed: {e}")
            return {
                "test_question": "What is this community about?",
                "test_result": {"error": str(e)},
                "test_passed": False,
                "timestamp": datetime.now().isoformat()
            }

            reply_count = user['reply_count']
            emoji_given = user['emoji_given']
            
            answer_parts.append(
                f"{i}. **{user_name}** - 發送{message_count}條訊息，"
                f"回覆{reply_count}次，給出{emoji_given}個emoji"
            )
        
        # 添加總體統計
        answer_parts.append(
            f"\n總體統計：{activity_summary['total_users']}位活躍用戶，"
            f"共{activity_summary['total_messages']}條訊息，"
            f"平均每人{activity_summary['avg_messages_per_user']}條訊息。"
        )
        
        return "\n".join(answer_parts)

    def ask_follow_up_question(
        self,
        question: str,
        k: int = 5,
        score_threshold: float = 0.7,
        source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ask a follow-up question with conversation context
        
        Args:
            question: The follow-up question
            k: Number of documents to retrieve
            score_threshold: Minimum similarity score for documents
            source_filter: Optional source type filter
            
        Returns:
            Dictionary with answer and context
        """
        try:
            # Get conversation history
            chat_history = self.memory.chat_memory.messages
            
            # Build context-aware query
            context_query = self._build_context_query(question, chat_history)
            
            # Ask question with context
            result = self.ask_question(
                question=context_query,
                k=k,
                score_threshold=score_threshold,
                source_filter=source_filter
            )
            
            # Update the result with the original question
            result["original_question"] = question
            result["context_query"] = context_query
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to answer follow-up question: {e}")
            return {
                "question": question,
                "answer": f"Sorry, I encountered an error while processing your follow-up question: {str(e)}",
                "error": True,
                "timestamp": datetime.now().isoformat()
            }

    def _build_context_query(self, question: str, chat_history: List[BaseMessage]) -> str:
        """
        Build a context-aware query from question and chat history
        
        Args:
            question: Current question
            chat_history: Previous conversation messages
            
        Returns:
            Context-aware query string
        """
        if not chat_history:
            return question
        
        # Extract recent questions and answers
        recent_context = []
        for i, message in enumerate(chat_history[-6:]):  # Last 3 Q&A pairs
            if isinstance(message, HumanMessage):
                recent_context.append(f"Previous question: {message.content}")
            elif isinstance(message, SystemMessage) and "answer" in message.content.lower():
                recent_context.append(f"Previous answer: {message.content}")
        
        if recent_context:
            context_str = "\n".join(recent_context)
            return f"Context from previous conversation:\n{context_str}\n\nCurrent question: {question}"
        
        return question

    def search_community_data(
        self,
        query: str,
        source_type: Optional[str] = None,
        limit: int = 10,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Search community data without generating an answer
        
        Args:
            query: Search query
            source_type: Optional source type filter
            limit: Maximum number of results
            include_metadata: Whether to include full metadata
            
        Returns:
            Dictionary with search results
        """
        try:
            # Prepare filter
            filter_dict = None
            if source_type:
                filter_dict = {"source_type": source_type}
            
            # Perform search
            results = self.rag_system.similarity_search_with_score(
                query=query,
                k=limit,
                filter=filter_dict
            )
            
            # Format results
            search_results = []
            for doc, score in results:
                result_item = {
                    "content": doc.page_content,
                    "score": score,
                    "source_type": doc.metadata.get("source_type", "unknown")
                }
                
                if include_metadata:
                    result_item["metadata"] = doc.metadata
                
                search_results.append(result_item)
            
            return {
                "query": query,
                "results": search_results,
                "total_results": len(search_results),
                "source_filter": source_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Community data search failed: {e}")
            return {
                "query": query,
                "results": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """
        Get the current conversation history
        
        Returns:
            List of conversation messages
        """
        try:
            messages = self.memory.chat_memory.messages
            history = []
            
            for i, message in enumerate(messages):
                history.append({
                    "index": i,
                    "type": type(message).__name__,
                    "content": message.content,
                    "timestamp": datetime.now().isoformat()
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    def clear_conversation(self) -> bool:
        """
        Clear the conversation history
        
        Returns:
            True if successful
        """
        try:
            self.memory.clear()
            logger.info("Conversation history cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear conversation: {e}")
            return False

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics
        
        Returns:
            Dictionary with system statistics
        """
        try:
            # Get RAG system stats
            rag_stats = self.rag_system.get_collection_stats()
            
            # Get conversation stats
            conversation_length = len(self.memory.chat_memory.messages)
            
            # Get LLM info
            llm_info = self.llm.get_model_info()
            
            return {
                "rag_system": rag_stats,
                "conversation_length": conversation_length,
                "llm_info": llm_info,
                "max_context_length": self.max_context_length,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {"error": str(e)}

    def test_system(self) -> Dict[str, Any]:
        """
        Test the Q&A system with a simple question
        
        Returns:
            Test results
        """
        try:
            test_question = "What is this community about?"
            
            # Test basic question answering
            result = self.ask_question(
                question=test_question,
                k=3,
                score_threshold=0.5
            )
            
            # Test system stats
            stats = self.get_system_stats()
            
            return {
                "test_question": test_question,
                "test_result": result,
                "system_stats": stats,
                "test_passed": not result.get("error", False),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System test failed: {e}")
            return {
                "test_question": "What is this community about?",
                "test_result": {"error": str(e)},
                "test_passed": False,
                "timestamp": datetime.now().isoformat()
            }
