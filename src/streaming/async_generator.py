"""
Streaming response system for real-time answer generation
"""
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime
import threading
import queue
import time
from src.ai.prompts import CommunityPrompts

logger = logging.getLogger(__name__)

class StreamingResponse:
    """Handles streaming responses for real-time answer generation"""
    
    def __init__(self):
        self.active_streams: Dict[str, queue.Queue] = {}
        self.stream_timeouts: Dict[str, float] = {}
        self.max_stream_duration = 300  # 5 minutes max
        
    def create_stream(self, stream_id: str) -> queue.Queue:
        """Create a new streaming queue for a request"""
        self.active_streams[stream_id] = queue.Queue()
        self.stream_timeouts[stream_id] = time.time() + self.max_stream_duration
        logger.info(f"Created stream: {stream_id}")
        return self.active_streams[stream_id]
    
    def send_chunk(self, stream_id: str, chunk: Dict[str, Any]) -> bool:
        """Send a chunk to the stream"""
        if stream_id not in self.active_streams:
            return False
            
        try:
            self.active_streams[stream_id].put(chunk, timeout=1)
            return True
        except queue.Full:
            logger.warning(f"Stream {stream_id} queue is full")
            return False
    
    def close_stream(self, stream_id: str):
        """Close a streaming queue"""
        if stream_id in self.active_streams:
            # Send end signal
            try:
                self.active_streams[stream_id].put({"type": "end"}, timeout=1)
            except queue.Full:
                pass
            
            del self.active_streams[stream_id]
            if stream_id in self.stream_timeouts:
                del self.stream_timeouts[stream_id]
            logger.info(f"Closed stream: {stream_id}")
    
    def cleanup_expired_streams(self):
        """Clean up expired streams"""
        current_time = time.time()
        expired_streams = [
            stream_id for stream_id, timeout in self.stream_timeouts.items()
            if current_time > timeout
        ]
        
        for stream_id in expired_streams:
            logger.warning(f"Cleaning up expired stream: {stream_id}")
            self.close_stream(stream_id)
    
    def get_stream_status(self) -> Dict[str, Any]:
        """Get status of all active streams"""
        return {
            "active_streams": len(self.active_streams),
            "stream_ids": list(self.active_streams.keys())
        }

# Global streaming instance
_streaming_instance: Optional[StreamingResponse] = None

def get_streaming() -> StreamingResponse:
    """Get global streaming instance"""
    global _streaming_instance
    if _streaming_instance is None:
        _streaming_instance = StreamingResponse()
    return _streaming_instance

class AsyncAnswerGenerator:
    """Generates answers asynchronously with streaming support"""
    
    def __init__(self, qa_system):
        self.qa_system = qa_system
        self.streaming = get_streaming()
    
    def generate_answer_async(self, question: str, stream_id: str) -> None:
        """Generate answer asynchronously and stream results"""
        try:
            # Send initial status
            self.streaming.send_chunk(stream_id, {
                "type": "status",
                "message": "正在分析問題...",
                "progress": 10
            })
            
            # Check cache first
            cached_result = self.qa_system.cache.get_cached_answer(question)
            if cached_result:
                self.streaming.send_chunk(stream_id, {
                    "type": "status",
                    "message": "找到緩存答案...",
                    "progress": 20
                })
                
                # Stream cached answer
                self._stream_answer_chunks(stream_id, cached_result["answer"])
                self.streaming.send_chunk(stream_id, {
                    "type": "complete",
                    "answer": cached_result["answer"],
                    "sources": cached_result["sources"],
                    "cached": True,
                    "timestamp": datetime.now().isoformat()
                })
                return
            
            # Check if statistical question
            if self.qa_system._is_stats_question(question):
                self.streaming.send_chunk(stream_id, {
                    "type": "status",
                    "message": "正在統計數據...",
                    "progress": 30
                })
                
                stats_result = self.qa_system._handle_stats_question(question)
                self._stream_answer_chunks(stream_id, stats_result["answer"])
                self.streaming.send_chunk(stream_id, {
                    "type": "complete",
                    "answer": stats_result["answer"],
                    "sources": stats_result.get("sources", []),
                    "stats_data": stats_result.get("stats_data"),
                    "timestamp": datetime.now().isoformat()
                })
                return
            
            # RAG processing
            self.streaming.send_chunk(stream_id, {
                "type": "status",
                "message": "正在檢索相關資料...",
                "progress": 40
            })
            
            # Get relevant documents
            relevant_docs = self.qa_system.rag_system.get_relevant_documents(
                question, k=5, score_threshold=0.5
            )
            
            self.streaming.send_chunk(stream_id, {
                "type": "status",
                "message": f"找到 {len(relevant_docs)} 個相關資料，正在生成回答...",
                "progress": 60
            })
            
            # Format context
            context = CommunityPrompts.format_qa_context(relevant_docs)
            
            self.streaming.send_chunk(stream_id, {
                "type": "status",
                "message": "正在生成回答...",
                "progress": 80
            })
            
            # Generate answer
            prompt = f"{CommunityPrompts.QA_SYSTEM_PROMPT}\n\n{CommunityPrompts.QA_HUMAN_PROMPT}".format(
                context=context,
                question=question
            )
            
            answer = self.qa_system.llm._call(prompt)
            if hasattr(answer, 'content'):
                answer = answer.content
            else:
                answer = str(answer)
            
            # Stream answer chunks
            self._stream_answer_chunks(stream_id, answer)
            
            # Prepare sources
            sources = [
                {
                    "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                    "metadata": doc["metadata"],
                    "score": doc["score"]
                }
                for doc in relevant_docs
            ]
            
            # Cache the answer
            self.qa_system.cache.cache_answer(question, answer, sources)
            
            # Send completion
            self.streaming.send_chunk(stream_id, {
                "type": "complete",
                "answer": answer,
                "sources": sources,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error in async answer generation: {e}")
            self.streaming.send_chunk(stream_id, {
                "type": "error",
                "message": f"生成回答時發生錯誤: {str(e)}"
            })
        finally:
            self.streaming.close_stream(stream_id)
    
    def _stream_answer_chunks(self, stream_id: str, answer: str):
        """Stream answer in chunks for better UX"""
        # Split answer into sentences for streaming
        sentences = answer.split('。')
        if len(sentences) <= 1:
            sentences = answer.split('.')
        
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                self.streaming.send_chunk(stream_id, {
                    "type": "chunk",
                    "content": sentence.strip() + ('。' if not sentence.endswith('.') else ''),
                    "progress": 80 + (i * 20 // len(sentences))
                })
                time.sleep(0.1)  # Small delay for streaming effect
