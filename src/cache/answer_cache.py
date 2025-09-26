"""
Answer caching system for common questions
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import redis
import os

logger = logging.getLogger(__name__)

@dataclass
class CachedAnswer:
    """Cached answer data structure"""
    question_hash: str
    answer: str
    sources: list
    timestamp: datetime
    expires_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'question_hash': self.question_hash,
            'answer': self.answer,
            'sources': self.sources,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CachedAnswer':
        """Create from dictionary"""
        return cls(
            question_hash=data['question_hash'],
            answer=data['answer'],
            sources=data['sources'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            expires_at=datetime.fromisoformat(data['expires_at'])
        )

class AnswerCache:
    """Answer caching system using Redis"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize cache with Redis backend
        
        Args:
            redis_url: Redis connection URL, defaults to localhost
        """
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.cache_ttl = int(os.getenv('CACHE_TTL_HOURS', '24')) * 3600  # Default 24 hours
        self.max_cache_size = int(os.getenv('MAX_CACHE_SIZE', '1000'))
        
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis cache initialized: {self.redis_url}")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.redis_client = None
            self._memory_cache: Dict[str, CachedAnswer] = {}
    
    def _generate_question_hash(self, question: str) -> str:
        """Generate hash for question normalization"""
        # Normalize question: lowercase, remove extra spaces, remove punctuation
        normalized = question.lower().strip()
        normalized = ' '.join(normalized.split())  # Remove extra spaces
        
        # Remove common punctuation
        punctuation = '.,!?;:'
        for p in punctuation:
            normalized = normalized.replace(p, '')
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _is_common_question(self, question: str) -> bool:
        """Check if question is common enough to cache"""
        common_patterns = [
            '嘉平', '蔡嘉平', 'jiapin', 'boss', '老大',
            '最活躍', '活躍', '使用者', '用戶',
            'apache', 'kafka', 'yunikorn',
            '社群', 'community', '源來適你',
            'github', 'slack', '開源'
        ]
        
        question_lower = question.lower()
        return any(pattern in question_lower for pattern in common_patterns)
    
    def get_cached_answer(self, question: str) -> Optional[Dict[str, Any]]:
        """
        Get cached answer for question
        
        Args:
            question: The question to look up
            
        Returns:
            Cached answer data or None if not found/expired
        """
        if not self._is_common_question(question):
            return None
            
        question_hash = self._generate_question_hash(question)
        
        try:
            if self.redis_client:
                cached_data = self.redis_client.get(f"answer_cache:{question_hash}")
                if cached_data:
                    cached_answer = CachedAnswer.from_dict(json.loads(cached_data))
                    if cached_answer.expires_at > datetime.now():
                        logger.info(f"Cache hit for question hash: {question_hash}")
                        return {
                            'answer': cached_answer.answer,
                            'sources': cached_answer.sources,
                            'cached': True,
                            'cache_timestamp': cached_answer.timestamp.isoformat()
                        }
                    else:
                        # Expired, remove from cache
                        self.redis_client.delete(f"answer_cache:{question_hash}")
            else:
                # In-memory cache
                if question_hash in self._memory_cache:
                    cached_answer = self._memory_cache[question_hash]
                    if cached_answer.expires_at > datetime.now():
                        logger.info(f"Memory cache hit for question hash: {question_hash}")
                        return {
                            'answer': cached_answer.answer,
                            'sources': cached_answer.sources,
                            'cached': True,
                            'cache_timestamp': cached_answer.timestamp.isoformat()
                        }
                    else:
                        # Expired, remove from cache
                        del self._memory_cache[question_hash]
        except Exception as e:
            logger.error(f"Error getting cached answer: {e}")
        
        return None
    
    def cache_answer(self, question: str, answer: str, sources: list) -> bool:
        """
        Cache answer for question
        
        Args:
            question: The question
            answer: The answer text
            sources: List of sources used
            
        Returns:
            True if cached successfully
        """
        if not self._is_common_question(question):
            return False
            
        question_hash = self._generate_question_hash(question)
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.cache_ttl)
        
        cached_answer = CachedAnswer(
            question_hash=question_hash,
            answer=answer,
            sources=sources,
            timestamp=now,
            expires_at=expires_at
        )
        
        try:
            if self.redis_client:
                # Use Redis
                self.redis_client.setex(
                    f"answer_cache:{question_hash}",
                    self.cache_ttl,
                    json.dumps(cached_answer.to_dict())
                )
                logger.info(f"Cached answer in Redis for question hash: {question_hash}")
            else:
                # Use in-memory cache
                if len(self._memory_cache) >= self.max_cache_size:
                    # Remove oldest entries
                    oldest_keys = sorted(
                        self._memory_cache.keys(),
                        key=lambda k: self._memory_cache[k].timestamp
                    )[:len(self._memory_cache) - self.max_cache_size + 1]
                    for key in oldest_keys:
                        del self._memory_cache[key]
                
                self._memory_cache[question_hash] = cached_answer
                logger.info(f"Cached answer in memory for question hash: {question_hash}")
            
            return True
        except Exception as e:
            logger.error(f"Error caching answer: {e}")
            return False
    
    def clear_cache(self) -> bool:
        """Clear all cached answers"""
        try:
            if self.redis_client:
                # Clear Redis cache
                keys = self.redis_client.keys("answer_cache:*")
                if keys:
                    self.redis_client.delete(*keys)
                logger.info("Cleared Redis cache")
            else:
                # Clear memory cache
                self._memory_cache.clear()
                logger.info("Cleared memory cache")
            
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys("answer_cache:*")
                return {
                    'backend': 'redis',
                    'total_entries': len(keys),
                    'redis_url': self.redis_url
                }
            else:
                return {
                    'backend': 'memory',
                    'total_entries': len(self._memory_cache),
                    'max_size': self.max_cache_size
                }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'backend': 'error', 'error': str(e)}

# Global cache instance
_cache_instance: Optional[AnswerCache] = None

def get_cache() -> AnswerCache:
    """Get global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AnswerCache()
    return _cache_instance
