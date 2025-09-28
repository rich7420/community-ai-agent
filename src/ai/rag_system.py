"""
RAG (Retrieval-Augmented Generation) System using Gemini embeddings
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from langchain.vectorstores import VectorStore
from langchain.embeddings.base import Embeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import psycopg2
from psycopg2.extras import RealDictCursor

from utils.logging_config import structured_logger
from ai.gemini_embedding_generator import GeminiEmbeddingGenerator
from storage.postgres_storage import PostgreSQLStorage
from utils.project_description_manager import ProjectDescriptionManager

logger = logging.getLogger(__name__)


class CommunityRAGSystem:
    """RAG system for community data retrieval using Gemini embeddings"""
    
    def __init__(
        self,
        connection_string: str,
        embedding_model: str = "gemini",  # 默認使用 Gemini
        collection_name: str = "community_embeddings",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize RAG system
        
        Args:
            connection_string: PostgreSQL connection string
            embedding_model: Embedding model name ("gemini" or "sentence-transformers")
            collection_name: Name of the vector collection
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.connection_string = connection_string
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize embedding generator (always use Gemini)
        self.embedding_generator = GeminiEmbeddingGenerator()
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize storage (FAISS-backed similarity as fallback)
        self.storage = PostgreSQLStorage()
        
        # Initialize project description manager
        self.project_desc_manager = ProjectDescriptionManager()
        
        structured_logger.info("RAG system initialized with Gemini embeddings", extra={
            "embedding_model": embedding_model,
            "collection_name": collection_name,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        })

    def get_relevant_documents(
        self,
        query: str,
        k: int = 5,  # 增加到5個文檔
        score_threshold: float = 0.1,  # 保持低閾值
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relevant documents for RAG with filtering by score
        
        Args:
            query: Search query
            k: Number of results to return
            score_threshold: Minimum similarity score
            filter: Optional metadata filter
            
        Returns:
            List of relevant document dictionaries
        """
        try:
            # Generate embedding for the query
            query_embedding = self.embedding_generator.generate_embedding(query)
            
            # Use PostgreSQLStorage's search_similar_records (FAISS-backed)
            # The filter needs to be passed as 'platform' to search_similar_records
            platform_filter = filter.get('source_type') if filter and 'source_type' in filter else None
            
            results = self.storage.search_similar_records(
                query_embedding=query_embedding,
                limit=k,
                threshold=score_threshold,
                platform=platform_filter
            )
            
            # Format results to match expected output
            relevant_docs = []
            for doc in results:
                relevant_docs.append({
                    "content": doc['content'],
                    "metadata": doc['metadata'],
                    "score": doc.get('similarity', 0.0), # Use 'similarity' from search_similar_records
                    "source_url": doc.get('source_url'),
                    "platform": doc.get('platform')
                })
            
            structured_logger.info("Relevant documents retrieved", extra={
                "query": query,
                "k": k,
                "score_threshold": score_threshold,
                "relevant_count": len(relevant_docs),
                "total_results": len(results),
                "filter": filter
            })
            
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Failed to get relevant documents: {e}")
            raise

    def search_similar(
        self,
        query: str,
        k: int = 5,  # 增加到5個文檔
        score_threshold: float = 0.1,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents (alias for get_relevant_documents)
        """
        return self.get_relevant_documents(query, k, score_threshold, filter)

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents to the vector store
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of document IDs
        """
        try:
            # 使用 PostgreSQLStorage 添加文檔
            document_ids = []
            
            for doc in documents:
                # 創建 StandardizedRecord
                from collectors.data_merger import StandardizedRecord
                from datetime import datetime
                
                record = StandardizedRecord(
                    id=f"doc_{len(document_ids)}",
                    platform="document",
                    content=doc.page_content,
                    author="system",
                    timestamp=datetime.now(),
                    source_url=doc.metadata.get('source', ''),
                    metadata=doc.metadata,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                # 生成嵌入
                embedding = self.embedding_generator.generate_embedding(record.content)
                record.embedding = embedding
                
                # 存儲到資料庫
                self.storage.insert_record(record)
                document_ids.append(record.id)
            
            structured_logger.info("Documents added to vector store", extra={
                "document_count": len(documents),
                "document_ids": document_ids
            })
            
            return document_ids
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        try:
            faiss_status = self.storage.get_faiss_status()
            
            return {
                "faiss_status": faiss_status,
                "embedding_model": self.embedding_generator.model_name if hasattr(self.embedding_generator, 'model_name') else "gemini",
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    def get_project_description(self, repository: str) -> Optional[str]:
        """
        獲取項目描述，優先使用官方描述
        
        Args:
            repository: 倉庫名稱 (格式: owner/repo)
            
        Returns:
            項目描述文本
        """
        try:
            project_desc = self.project_desc_manager.get_project_description(repository)
            if project_desc and project_desc.description:
                return project_desc.description
            return None
        except Exception as e:
            logger.error(f"獲取項目描述失敗 {repository}: {e}")
            return None
    
    def get_enhanced_context(self, query: str, k: int = 5) -> str:
        """
        獲取增強的上下文，包括項目描述
        
        Args:
            query: 查詢文本
            k: 文檔數量
            
        Returns:
            增強的上下文文本
        """
        try:
            # 獲取相關文檔
            relevant_docs = self.get_relevant_documents(query, k)
            
            # 檢查是否涉及特定項目
            project_repos = self._extract_project_references(query)
            
            context_parts = []
            
            # 添加項目描述（如果有的話）
            for repo in project_repos:
                project_desc = self.get_project_description(repo)
                if project_desc:
                    context_parts.append(f"項目 {repo} 的官方描述：\n{project_desc}\n")
            
            # 添加相關文檔
            for doc in relevant_docs:
                content = doc.get('content', '')
                if content:
                    context_parts.append(content)
            
            return '\n\n'.join(context_parts)
            
        except Exception as e:
            logger.error(f"獲取增強上下文失敗: {e}")
            return ""
    
    def _extract_project_references(self, query: str) -> List[str]:
        """
        從查詢中提取項目引用
        
        Args:
            query: 查詢文本
            
        Returns:
            項目倉庫列表
        """
        import re
        
        # 項目名稱映射
        project_mapping = {
            'apache kafka': 'apache/kafka',
            'apache ozone': 'apache/ozone', 
            'apache airflow': 'apache/airflow',
            'apache gravitino': 'apache/gravitino',
            'apache yunikorn': 'apache/yunikorn-core',
            'yunikorn': 'apache/yunikorn-core',
            'apache ambari': 'apache/ambari',
            'kubray': 'ray-project/kuberay',
            'ray': 'ray-project/ray',
            'flyte': 'flyteorg/flyte',
            'liger-kernel': 'linkedin/Liger-Kernel',
            'commitizen': 'commitizen-tools/commitizen'
        }
        
        # 常見的項目名稱模式
        project_patterns = [
            r'apache\s+(kafka|ozone|airflow|gravitino|yunikorn|ambari)',
            r'kubray|ray',
            r'flyte',
            r'liger-kernel',
            r'commitizen',
            r'apache\s+[a-z]+',
            r'github\.com/[^/\s]+/[^/\s]+',
            r'[a-z]+/[a-z]+'  # owner/repo 格式
        ]
        
        projects = []
        query_lower = query.lower()
        
        # 直接檢查項目映射
        for project_name, repo_name in project_mapping.items():
            if project_name in query_lower:
                projects.append(repo_name)
        
        # 使用正則表達式匹配
        for pattern in project_patterns:
            matches = re.findall(pattern, query_lower)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                # 將匹配的項目名稱轉換為倉庫格式
                if match in project_mapping:
                    projects.append(project_mapping[match])
                else:
                    projects.append(match)
        
        # 如果查詢包含"apache"但沒有找到具體項目，返回所有Apache項目
        if 'apache' in query_lower and not projects:
            projects = [
                'apache/kafka',
                'apache/yunikorn-core', 
                'apache/ozone',
                'apache/airflow',
                'apache/gravitino',
                'apache/ambari'
            ]
        
        return list(set(projects))
    
    def get_user_activity_analysis(self, user_display_name: str) -> Dict[str, Any]:
        """
        分析用戶活躍度 - 優化版本
        
        Args:
            user_display_name: 用戶顯示名稱
            
        Returns:
            用戶活躍度分析結果
        """
        try:
            from storage.connection_pool import get_db_connection, return_db_connection
            from psycopg2.extras import RealDictCursor
            import time
            
            start_time = time.time()
            
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 優化用戶查找 - 使用更精確的查詢
            cur.execute("""
                SELECT anonymized_id, display_name, real_name, aliases, group_terms
                FROM user_name_mappings 
                WHERE display_name = %s OR real_name = %s 
                   OR %s = ANY(aliases) OR %s = ANY(group_terms)
                LIMIT 1
            """, (user_display_name, user_display_name, user_display_name, user_display_name))
            
            user_result = cur.fetchone()
            if not user_result:
                # 嘗試模糊匹配
                cur.execute("""
                    SELECT anonymized_id, display_name, real_name, aliases, group_terms
                    FROM user_name_mappings 
                    WHERE display_name ILIKE %s OR real_name ILIKE %s
                    LIMIT 1
                """, (f"%{user_display_name}%", f"%{user_display_name}%"))
                
                user_result = cur.fetchone()
                if not user_result:
                    cur.close()
                    return_db_connection(conn)
                    return {
                        "user_found": False,
                        "message": f"未找到用戶 {user_display_name}",
                        "query_time": time.time() - start_time
                    }
            
            anonymized_id = user_result['anonymized_id']
            display_name = user_result['display_name']
            
            # 優化統計查詢 - 使用單一查詢獲取所有統計
            cur.execute("""
                WITH user_stats AS (
                    SELECT 
                        COUNT(*) as total_messages,
                        COUNT(DISTINCT metadata->>'channel') as active_channels,
                        MIN(timestamp) as first_message,
                        MAX(timestamp) as last_message,
                        COUNT(CASE WHEN metadata->>'is_thread_reply' = 'true' THEN 1 END) as thread_replies,
                        COUNT(CASE WHEN metadata->>'is_thread_reply' = 'false' OR metadata->>'is_thread_reply' IS NULL THEN 1 END) as main_messages
                    FROM community_data 
                    WHERE author_anon = %s
                ),
                channel_stats AS (
                    SELECT 
                        metadata->>'channel' as channel_id,
                        metadata->>'channel_name' as channel_name,
                        COUNT(*) as message_count,
                        COUNT(CASE WHEN metadata->>'is_thread_reply' = 'true' THEN 1 END) as thread_replies,
                        COUNT(CASE WHEN metadata->>'is_thread_reply' = 'false' OR metadata->>'is_thread_reply' IS NULL THEN 1 END) as main_messages
                    FROM community_data 
                    WHERE author_anon = %s AND platform = 'slack'
                    GROUP BY metadata->>'channel', metadata->>'channel_name'
                    ORDER BY message_count DESC
                    LIMIT 10
                )
                SELECT 
                    (SELECT * FROM user_stats) as user_stats,
                    (SELECT array_agg(row_to_json(channel_stats)) FROM channel_stats) as channel_stats
            """, (anonymized_id, anonymized_id))
            
            result = cur.fetchone()
            stats_result = result['user_stats']
            channel_stats = result['channel_stats'] or []
            
            if stats_result['total_messages'] < 10:
                cur.close()
                return_db_connection(conn)
                return {
                    "user_found": True,
                    "display_name": display_name,
                    "message_count": stats_result['total_messages'],
                    "analysis_available": False,
                    "message": f"{display_name} 的訊息數量 ({stats_result['total_messages']}) 少於10條，無法進行活躍度分析",
                    "query_time": time.time() - start_time
                }
            
            # 獲取最近訊息（限制數量以提高性能）
            cur.execute("""
                SELECT content
                FROM community_data 
                WHERE author_anon = %s AND platform = 'slack'
                ORDER BY timestamp DESC
                LIMIT 20
            """, (anonymized_id,))
            
            recent_messages = cur.fetchall()
            content_text = " ".join([msg['content'] for msg in recent_messages])
            
            cur.close()
            return_db_connection(conn)
            
            query_time = time.time() - start_time
            
            return {
                "user_found": True,
                "display_name": display_name,
                "analysis_available": True,
                "total_messages": stats_result['total_messages'],
                "active_channels": stats_result['active_channels'],
                "first_message": stats_result['first_message'].isoformat() if stats_result['first_message'] else None,
                "last_message": stats_result['last_message'].isoformat() if stats_result['last_message'] else None,
                "thread_replies": stats_result['thread_replies'],
                "main_messages": stats_result['main_messages'],
                "channel_activity": [
                    {
                        "channel_id": ch['channel_id'],
                        "channel_name": ch['channel_name'],
                        "message_count": ch['message_count'],
                        "thread_replies": ch['thread_replies'],
                        "main_messages": ch['main_messages']
                    } for ch in channel_stats
                ],
                "recent_activity": content_text[:300] + "..." if len(content_text) > 300 else content_text,
                "query_time": query_time
            }
            
        except Exception as e:
            logger.error(f"用戶活躍度分析失敗: {e}")
            return {
                "user_found": False,
                "error": str(e),
                "query_time": time.time() - start_time if 'start_time' in locals() else 0
            }