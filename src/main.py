"""
Main FastAPI application for Community AI Agent
"""
import os
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import AI components
from ai.qa_system import CommunityQASystem
from ai.rag_system import CommunityRAGSystem
from ai.google_llm import GoogleLLM
from api.health_endpoint import router as health_router
from streaming.async_generator import AsyncAnswerGenerator, get_streaming
from cache.answer_cache import get_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Community AI Agent API",
    description="AI-powered community data analysis and Q&A system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include health check router
app.include_router(health_router)

# Global Q&A system instance
qa_system: Optional[CommunityQASystem] = None
async_generator: Optional[AsyncAnswerGenerator] = None

# Import collectors for initial data collection
from collectors.slack_collector import SlackCollector
from collectors.github_collector import GitHubCollector

# Pydantic models
class QuestionRequest(BaseModel):
    question: str

class QuestionResponse(BaseModel):
    answer: str
    sources: Optional[list] = []

class ClearConversationResponse(BaseModel):
    message: str

def get_qa_system() -> CommunityQASystem:
    """Get or initialize Q&A system"""
    global qa_system
    if qa_system is None:
        try:
            # Initialize RAG system
            connection_string = os.getenv(
                "DATABASE_URL", 
                f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'password')}@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'community_ai')}"
            )
            
            rag_system = CommunityRAGSystem(
                connection_string=connection_string,
                embedding_model="gemini"  # 使用 Gemini 嵌入
            )
            
            # Initialize LLM
            llm = GoogleLLM(
                google_api_key=os.getenv("GOOGLE_API_KEY"),
                model_name="gemini-2.5-pro-preview-03-25",
                temperature=0.7,
                max_tokens=8192
            )
            
            # Initialize Q&A system
            qa_system = CommunityQASystem(rag_system=rag_system, llm=llm)
            
            # Initialize async generator
            async_generator = AsyncAnswerGenerator(qa_system)
            
            logger.info("Q&A system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Q&A system: {e}")
            raise HTTPException(status_code=500, detail=f"Q&A system initialization failed: {str(e)}")
    
    return qa_system

async def check_if_initial_collection_needed() -> bool:
    """檢查是否需要進行初始數據收集"""
    try:
        from storage.connection_pool import get_db_connection, return_db_connection
        from psycopg2.extras import RealDictCursor
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 檢查是否已有數據
        cur.execute("SELECT COUNT(*) as count FROM community_data")
        result = cur.fetchone()
        data_count = result['count'] if result else 0
        
        # 檢查是否有 Slack 數據
        cur.execute("SELECT COUNT(*) as count FROM community_data WHERE platform = 'slack'")
        result = cur.fetchone()
        slack_data_count = result['count'] if result else 0
        
        # 檢查是否有初始化標記（如果表存在）
        try:
            cur.execute("SELECT COUNT(*) as count FROM system_flags WHERE flag_name = 'initial_collection_completed'")
            result = cur.fetchone()
            flag_count = result['count'] if result else 0
        except Exception:
            # 如果 system_flags 表不存在，則 flag_count = 0
            flag_count = 0
        
        cur.close()
        return_db_connection(conn)
        
        # 如果有初始化標記，表示已經完成過初始收集，不需要重複收集
        if flag_count > 0:
            logger.info("檢測到初始化完成標記，跳過數據收集")
            return False
        
        # 如果沒有數據且沒有初始化標記，則需要收集
        if data_count == 0:
            logger.info("沒有檢測到任何數據，需要進行初始收集")
            return True
        
        # 如果有數據但沒有初始化標記，可能是舊的數據，需要設置標記
        logger.info(f"檢測到 {data_count} 條現有數據，但沒有初始化標記，將設置標記並跳過收集")
        return False
        
    except Exception as e:
        logger.error(f"檢查初始收集狀態失敗: {e}")
        # 如果檢查失敗，為了安全起見，不進行收集
        return False

async def check_and_set_initial_flag_if_needed():
    """檢查並設置初始化標記（如果有數據但沒有標記）"""
    try:
        from storage.connection_pool import get_db_connection, return_db_connection
        from psycopg2.extras import RealDictCursor
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 檢查是否已有數據
        cur.execute("SELECT COUNT(*) as count FROM community_data")
        result = cur.fetchone()
        data_count = result['count'] if result else 0
        
        # 檢查是否有初始化標記
        try:
            cur.execute("SELECT COUNT(*) as count FROM system_flags WHERE flag_name = 'initial_collection_completed'")
            result = cur.fetchone()
            flag_count = result['count'] if result else 0
        except Exception:
            flag_count = 0
        
        cur.close()
        return_db_connection(conn)
        
        # 如果有數據但沒有標記，設置標記
        if data_count > 0 and flag_count == 0:
            logger.info(f"檢測到 {data_count} 條現有數據但沒有初始化標記，設置標記")
            await set_initial_collection_completed()
        
    except Exception as e:
        logger.error(f"檢查並設置初始化標記失敗: {e}")

@app.on_event("startup")
async def startup_event():
    """應用程序啟動時的事件處理"""
    logger.info("應用程序啟動中...")
    
    # 檢查是否需要進行初始數據收集
    should_collect = await check_if_initial_collection_needed()
    
    if should_collect:
        # 啟動後台數據收集任務
        import asyncio
        asyncio.create_task(background_data_collection())
        logger.info("後台數據收集任務已啟動")
    else:
        # 檢查是否需要設置初始化標記（有數據但沒有標記的情況）
        await check_and_set_initial_flag_if_needed()
        logger.info("跳過初始數據收集，系統已初始化")

async def background_data_collection():
    """後台數據收集任務"""
    import asyncio
    
    # 等待5秒讓API服務完全啟動
    await asyncio.sleep(5)
    
    try:
        await initial_data_collection()
        logger.info("後台數據收集完成")
    except Exception as e:
        logger.error(f"後台數據收集失敗: {e}")

async def initial_data_collection():
    """初始數據收集，建立用戶映射"""
    try:
        # 檢查是否需要進行初始收集
        from storage.connection_pool import get_db_connection, return_db_connection
        from psycopg2.extras import RealDictCursor
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 檢查是否已有用戶映射數據（如果表存在）
        try:
            cur.execute("SELECT COUNT(*) as count FROM user_name_mappings")
            result = cur.fetchone()
            user_mapping_count = result['count'] if result else 0
        except Exception:
            # 如果 user_name_mappings 表不存在，則 user_mapping_count = 0
            user_mapping_count = 0
        
        # 檢查是否已有 Slack 數據
        cur.execute("SELECT COUNT(*) as count FROM community_data WHERE platform = 'slack'")
        result = cur.fetchone()
        slack_data_count = result['count'] if result else 0
        
        cur.close()
        return_db_connection(conn)
        
        logger.info(f"檢測到用戶映射記錄 {user_mapping_count} 條，Slack 數據 {slack_data_count} 條")
        
        # 初始化收集器
        slack_collector = None
        github_collector = None
        calendar_collector = None
        
        # 初始化Slack收集器（只有在沒有 Slack 數據時才初始化）
        if slack_data_count == 0:
            slack_bot_token = os.getenv('SLACK_BOT_TOKEN')
            slack_app_token = os.getenv('SLACK_APP_TOKEN')
            if slack_bot_token and slack_app_token:
                try:
                    slack_collector = SlackCollector(slack_bot_token, slack_app_token)
                    logger.info("Slack收集器初始化成功")
                except Exception as e:
                    logger.error(f"Slack收集器初始化失敗: {e}")
        else:
            logger.info(f"檢測到 {slack_data_count} 條 Slack 數據，跳過 Slack 收集")
        
        # 初始化GitHub收集器
        github_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            try:
                github_collector = GitHubCollector(github_token)
                logger.info("GitHub收集器初始化成功")
            except Exception as e:
                logger.error(f"GitHub收集器初始化失敗: {e}")
        
        # 初始化Google Calendar收集器
        calendar_service_account_file = os.getenv('GOOGLE_CALENDAR_SERVICE_ACCOUNT_FILE')
        if calendar_service_account_file:
            try:
                from collectors.google_calendar_collector import GoogleCalendarCollector
                calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
                calendar_collector = GoogleCalendarCollector(calendar_service_account_file, calendar_id)
                logger.info("Google Calendar收集器初始化成功")
            except Exception as e:
                logger.error(f"Google Calendar收集器初始化失敗: {e}")
        
        # 收集Slack數據以建立用戶映射（只有在沒有 Slack 數據時才收集）
        if slack_collector:
            try:
                logger.info("開始收集Slack數據以建立用戶映射...")
                # 收集最近90天的數據
                slack_messages = slack_collector.collect_bot_channels(days_back=90)
                logger.info(f"Slack數據收集完成，共 {len(slack_messages)} 條訊息")
                
                # 將Slack數據保存到數據庫
                if slack_messages:
                    from collectors.data_merger import DataMerger
                    from storage.postgres_storage import PostgreSQLStorage
                    from ai.gemini_embedding_generator import GeminiEmbeddingGenerator
                    
                    logger.info("開始處理Slack數據並保存到數據庫...")
                    data_merger = DataMerger()
                    slack_records = data_merger.merge_slack_data(slack_messages)
                    
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
                            
                            if processed_count % 10 == 0:
                                logger.info(f"已處理 {processed_count}/{len(slack_records)} 條Slack記錄")
                                
                        except Exception as e:
                            logger.error(f"處理Slack記錄失敗: {e}")
                    
                    logger.info(f"Slack數據保存完成，共處理 {processed_count} 條記錄")
                
            except Exception as e:
                logger.error(f"Slack數據收集失敗: {e}")
        
        # 收集GitHub數據
        if github_collector:
            try:
                logger.info("開始收集GitHub數據...")
                github_data = github_collector.collect_all_repositories(days_back=90)
                logger.info(f"GitHub數據收集完成")
                
                # 將GitHub數據保存到數據庫
                if github_data:
                    from collectors.data_merger import DataMerger
                    from storage.postgres_storage import PostgreSQLStorage
                    from ai.gemini_embedding_generator import GeminiEmbeddingGenerator
                    
                    logger.info("開始處理GitHub數據並保存到數據庫...")
                    data_merger = DataMerger()
                    github_records = data_merger.merge_github_data(
                        github_data.get('issues', []),
                        github_data.get('prs', []),
                        github_data.get('commits', []),
                        github_data.get('files', [])
                    )
                    
                    # 生成嵌入並保存到數據庫
                    db_storage = PostgreSQLStorage()
                    embedding_generator = GeminiEmbeddingGenerator()
                    
                    processed_count = 0
                    for record in github_records:
                        try:
                            # 生成嵌入
                            embedding = embedding_generator.generate_embedding(record.content)
                            record.embedding = embedding
                            
                            # 保存到數據庫
                            db_storage.insert_record(record)
                            processed_count += 1
                            
                            if processed_count % 10 == 0:
                                logger.info(f"已處理 {processed_count}/{len(github_records)} 條GitHub記錄")
                                
                        except Exception as e:
                            logger.error(f"處理GitHub記錄失敗: {e}")
                    
                    logger.info(f"GitHub數據保存完成，共處理 {processed_count} 條記錄")
                
            except Exception as e:
                logger.error(f"GitHub數據收集失敗: {e}")
        
        # 收集Google Calendar數據
        if calendar_collector:
            try:
                logger.info("開始收集Google Calendar數據...")
                calendar_data = calendar_collector.collect_all_calendars(days_back=90)
                logger.info(f"Google Calendar數據收集完成")
                
                # 將Calendar數據保存到數據庫
                if calendar_data.get('events'):
                    from collectors.data_merger import DataMerger
                    from storage.postgres_storage import PostgreSQLStorage
                    from ai.gemini_embedding_generator import GeminiEmbeddingGenerator
                    
                    logger.info("開始處理Google Calendar數據並保存到數據庫...")
                    data_merger = DataMerger()
                    calendar_records = data_merger.merge_google_calendar_data(calendar_data['events'])
                    
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
                            
                            if processed_count % 10 == 0:
                                logger.info(f"已處理 {processed_count}/{len(calendar_records)} 條Calendar記錄")
                                
                        except Exception as e:
                            logger.error(f"處理Calendar記錄失敗: {e}")
                    
                    logger.info(f"Google Calendar數據保存完成，共處理 {processed_count} 條記錄")
                
                # 保存日曆信息到數據庫
                if calendar_data.get('calendars'):
                    calendar_collector.save_calendars_to_db(calendar_data['calendars'])
                
            except Exception as e:
                logger.error(f"Google Calendar數據收集失敗: {e}")
        
        logger.info("初始數據收集完成")
        
        # 設置初始化完成標記
        await set_initial_collection_completed()
        
    except Exception as e:
        logger.error(f"初始數據收集過程中發生錯誤: {e}")

async def set_initial_collection_completed():
    """設置初始收集完成標記"""
    try:
        from storage.connection_pool import get_db_connection, return_db_connection
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 創建 system_flags 表（如果不存在）
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_flags (
                id SERIAL PRIMARY KEY,
                flag_name VARCHAR(255) UNIQUE NOT NULL,
                flag_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 插入或更新標記
        cur.execute("""
            INSERT INTO system_flags (flag_name, flag_value) 
            VALUES ('initial_collection_completed', 'true')
            ON CONFLICT (flag_name) 
            DO UPDATE SET flag_value = 'true', updated_at = CURRENT_TIMESTAMP
        """)
        
        conn.commit()
        cur.close()
        return_db_connection(conn)
        
        logger.info("初始收集完成標記已設置")
        
    except Exception as e:
        logger.error(f"設置初始收集完成標記失敗: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Community AI Agent API is running"}

@app.post("/ask_question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question to the AI system"""
    try:
        qa_system = get_qa_system()
        result = qa_system.ask_question(request.question)
        
        return QuestionResponse(
            answer=result.get("answer", "No answer generated"),
            sources=[]  # 不返回參考資料
        )
        
    except Exception as e:
        logger.error(f"Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.post("/clear_conversation", response_model=ClearConversationResponse)
async def clear_conversation():
    """Clear conversation history"""
    try:
        qa_system = get_qa_system()
        qa_system.clear_conversation()
        
        return ClearConversationResponse(message="Conversation history cleared successfully")
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing conversation: {str(e)}")

@app.get("/system_stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        qa_system = get_qa_system()
        stats = qa_system.get_system_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting system stats: {str(e)}")

@app.post("/ask_question_stream")
async def ask_question_stream(request: QuestionRequest, background_tasks: BackgroundTasks):
    """Ask a question with streaming response"""
    import uuid
    import json
    
    stream_id = str(uuid.uuid4())
    streaming = get_streaming()
    
    # Create stream
    stream_queue = streaming.create_stream(stream_id)
    
    # Start async generation in background
    qa_system = get_qa_system()
    async_generator = AsyncAnswerGenerator(qa_system)
    
    def generate_answer():
        async_generator.generate_answer_async(request.question, stream_id)
    
    background_tasks.add_task(generate_answer)
    
    def stream_generator():
        try:
            while True:
                try:
                    chunk = stream_queue.get(timeout=1)
                    if chunk.get("type") == "end":
                        break
                    yield f"data: {json.dumps(chunk)}\n\n"
                except:
                    continue
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            streaming.close_stream(stream_id)
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/cache_stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        cache = get_cache()
        stats = cache.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")

@app.post("/clear_cache")
async def clear_cache():
    """Clear answer cache"""
    try:
        cache = get_cache()
        success = cache.clear_cache()
        return {"message": "Cache cleared successfully" if success else "Failed to clear cache"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
