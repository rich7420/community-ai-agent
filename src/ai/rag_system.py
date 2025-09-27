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

from src.utils.logging_config import structured_logger
from src.ai.gemini_embedding_generator import GeminiEmbeddingGenerator
from src.storage.postgres_storage import PostgreSQLStorage

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