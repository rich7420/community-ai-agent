"""
Health check API endpoint
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from src.monitoring.health_check import HealthChecker
from src.monitoring.metrics import MetricsCollector
from src.storage.postgres_storage import PostgreSQLStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

# Initialize health checker and metrics collector
health_checker = HealthChecker()
metrics_collector = MetricsCollector()
storage = PostgreSQLStorage()

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""
    try:
        overall_health = health_checker.get_overall_health()
        
        # Record health check metric
        metrics_collector.increment_counter("health_checks_total")
        
        if overall_health["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=overall_health)
        
        return overall_health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        metrics_collector.increment_counter("health_checks_errors")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check for Kubernetes"""
    try:
        # Check critical components only
        database_health = health_checker.check_database()
        redis_health = health_checker.check_redis()
        
        if database_health["status"] != "healthy" or redis_health["status"] != "healthy":
            raise HTTPException(status_code=503, detail={
                "status": "not_ready",
                "database": database_health,
                "redis": redis_health
            })
        
        return {
            "status": "ready",
            "message": "Application is ready to serve traffic"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check for Kubernetes"""
    return {
        "status": "alive",
        "message": "Application is running"
    }

@router.get("/faiss")
async def faiss_status() -> Dict[str, Any]:
    """FAISS 索引狀態檢查"""
    try:
        faiss_status = storage.get_faiss_status()
        
        # 檢查索引是否正常
        if not faiss_status["index_exists"]:
            return {
                "status": "unhealthy",
                "message": "FAISS 索引不存在",
                "details": faiss_status
            }
        
        if faiss_status["total_vectors"] == 0:
            return {
                "status": "unhealthy", 
                "message": "FAISS 索引為空",
                "details": faiss_status
            }
        
        return {
            "status": "healthy",
            "message": "FAISS 索引正常",
            "details": faiss_status
        }
        
    except Exception as e:
        logger.error(f"FAISS 狀態檢查失敗: {e}")
        return {
            "status": "error",
            "message": f"FAISS 狀態檢查失敗: {str(e)}",
            "details": {}
        }

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get application metrics"""
    try:
        system_metrics = metrics_collector.get_system_metrics()
        app_metrics = metrics_collector.get_application_metrics()
        
        return {
            "system": system_metrics,
            "application": app_metrics,
            "timestamp": system_metrics.get("timestamp")
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/components")
async def get_component_health() -> Dict[str, Any]:
    """Get detailed health status of all components"""
    try:
        overall_health = health_checker.get_overall_health()
        return overall_health["components"]
    except Exception as e:
        logger.error(f"Failed to get component health: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})
