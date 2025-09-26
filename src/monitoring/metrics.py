"""
Metrics collection module for monitoring application performance
"""
import time
import logging
from typing import Dict, Any, Optional
from functools import wraps
from datetime import datetime, timedelta
import psutil
import redis

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collects and stores application metrics"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.metrics_prefix = "community_ai"
        
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        try:
            key = self._build_key("counter", name, tags)
            if self.redis_client:
                self.redis_client.incrby(key, value)
                self.redis_client.expire(key, 86400)  # 24 hours
            logger.debug(f"Incremented counter {name}: +{value}")
        except Exception as e:
            logger.error(f"Failed to increment counter {name}: {e}")
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        try:
            key = self._build_key("gauge", name, tags)
            if self.redis_client:
                self.redis_client.set(key, value)
                self.redis_client.expire(key, 86400)  # 24 hours
            logger.debug(f"Set gauge {name}: {value}")
        except Exception as e:
            logger.error(f"Failed to set gauge {name}: {e}")
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric"""
        try:
            key = self._build_key("timer", name, tags)
            if self.redis_client:
                # Store as a list for calculating percentiles
                self.redis_client.lpush(key, duration)
                self.redis_client.ltrim(key, 0, 999)  # Keep last 1000 values
                self.redis_client.expire(key, 86400)  # 24 hours
            logger.debug(f"Recorded timing {name}: {duration}s")
        except Exception as e:
            logger.error(f"Failed to record timing {name}: {e}")
    
    def _build_key(self, metric_type: str, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Build Redis key for metric"""
        key_parts = [self.metrics_prefix, metric_type, name]
        if tags:
            tag_str = ",".join([f"{k}:{v}" for k, v in sorted(tags.items())])
            key_parts.append(tag_str)
        return ":".join(key_parts)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / (1024**3),
                "disk_total_gb": disk.total / (1024**3),
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    def get_application_metrics(self) -> Dict[str, Any]:
        """Get application-specific metrics"""
        try:
            metrics = {}
            
            if self.redis_client:
                # Get counter metrics
                counter_keys = self.redis_client.keys(f"{self.metrics_prefix}:counter:*")
                for key in counter_keys:
                    name = key.decode().split(":")[-1]
                    value = self.redis_client.get(key)
                    if value:
                        metrics[f"counter_{name}"] = int(value)
                
                # Get gauge metrics
                gauge_keys = self.redis_client.keys(f"{self.metrics_prefix}:gauge:*")
                for key in gauge_keys:
                    name = key.decode().split(":")[-1]
                    value = self.redis_client.get(key)
                    if value:
                        metrics[f"gauge_{name}"] = float(value)
                
                # Get timer metrics (calculate average)
                timer_keys = self.redis_client.keys(f"{self.metrics_prefix}:timer:*")
                for key in timer_keys:
                    name = key.decode().split(":")[-1]
                    values = self.redis_client.lrange(key, 0, -1)
                    if values:
                        durations = [float(v) for v in values]
                        metrics[f"timer_{name}_avg"] = sum(durations) / len(durations)
                        metrics[f"timer_{name}_count"] = len(durations)
            
            return metrics
        except Exception as e:
            logger.error(f"Failed to get application metrics: {e}")
            return {}

def timing_metric(name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to automatically record timing metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                # Try to get metrics collector from args or create a default one
                metrics_collector = None
                if args and hasattr(args[0], 'metrics_collector'):
                    metrics_collector = args[0].metrics_collector
                elif 'metrics_collector' in kwargs:
                    metrics_collector = kwargs['metrics_collector']
                
                if metrics_collector:
                    metrics_collector.record_timing(name, duration, tags)
        return wrapper
    return decorator

def counter_metric(name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
    """Decorator to automatically increment counter metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # Try to get metrics collector from args or create a default one
                metrics_collector = None
                if args and hasattr(args[0], 'metrics_collector'):
                    metrics_collector = args[0].metrics_collector
                elif 'metrics_collector' in kwargs:
                    metrics_collector = kwargs['metrics_collector']
                
                if metrics_collector:
                    metrics_collector.increment_counter(name, value, tags)
                return result
            except Exception as e:
                # Increment error counter
                if metrics_collector:
                    error_tags = tags.copy() if tags else {}
                    error_tags['error'] = 'true'
                    metrics_collector.increment_counter(f"{name}_errors", 1, error_tags)
                raise
        return wrapper
    return decorator

