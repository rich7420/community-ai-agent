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
from src.ai.qa_system import CommunityQASystem
from src.ai.rag_system import CommunityRAGSystem
from src.ai.grok_llm import GrokLLM
from src.api.health_endpoint import router as health_router
from src.streaming.async_generator import AsyncAnswerGenerator, get_streaming
from src.cache.answer_cache import get_cache

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
            llm = GrokLLM.from_environment()
            
            # Initialize Q&A system
            qa_system = CommunityQASystem(rag_system=rag_system, llm=llm)
            
            # Initialize async generator
            async_generator = AsyncAnswerGenerator(qa_system)
            
            logger.info("Q&A system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Q&A system: {e}")
            raise HTTPException(status_code=500, detail=f"Q&A system initialization failed: {str(e)}")
    
    return qa_system

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
