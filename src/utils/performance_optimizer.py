import logging
from typing import Dict, Any, Optional
from functools import wraps
import time
import redis
from ai.qa_system import CommunityQASystem

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)  # Configure from env
        self.cache_ttl = 3600  # 1 hour

    def cache_query_result(self, query: str, result: Any) -> None:
        try:
            self.redis_client.setex(f"query:{hash(query)}", self.cache_ttl, str(result))
        except Exception as e:
            logger.error(f"Failed to cache query result: {e}")

    def get_cached_result(self, query: str) -> Optional[Any]:
        try:
            cached = self.redis_client.get(f"query:{hash(query)}")
            return cached.decode() if cached else None
        except Exception as e:
            logger.error(f"Failed to get cached result: {e}")
            return None

    def batch_api_calls(self, calls: list) -> list:
        # Implement batching logic for API calls
        results = []
        for call in calls:
            try:
                result = call()
                results.append(result)
            except Exception as e:
                logger.error(f"Batch API call failed: {e}")
                results.append(None)
        return results

    def monitor_resource_usage(self) -> Dict[str, Any]:
        import psutil
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }

def performance_monitor(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.info(f"{func.__name__} took {end_time - start_time:.2f} seconds")
        return result
    return wrapper

