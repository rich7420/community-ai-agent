"""
Health check module for monitoring application status
"""
import os
import logging
from typing import Dict, Any
from datetime import datetime
import psycopg2
import redis
import requests

logger = logging.getLogger(__name__)

class HealthChecker:
    """Health check service for monitoring application components"""
    
    def __init__(self):
        # Construct database URL from individual components if DATABASE_URL not set
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            db_host = os.getenv("POSTGRES_HOST", "postgres")
            db_port = os.getenv("POSTGRES_PORT", "5432")
            db_name = os.getenv("POSTGRES_DB", "community_ai")
            db_user = os.getenv("POSTGRES_USER", "postgres")
            db_password = os.getenv("POSTGRES_PASSWORD", "password")
            self.database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Construct Redis URL from individual components
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_password = os.getenv("REDIS_PASSWORD", "")
        redis_db = os.getenv("REDIS_DB", "0")
        
        if redis_password:
            self.redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        else:
            self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
            
        self.minio_endpoint = os.getenv("MINIO_ENDPOINT")
        
    def check_database(self) -> Dict[str, Any]:
        """Check PostgreSQL database health"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def check_redis(self) -> Dict[str, Any]:
        """Check Redis cache health"""
        try:
            r = redis.from_url(self.redis_url)
            r.ping()
            
            return {
                "status": "healthy",
                "message": "Redis connection successful",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"Redis connection failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def check_minio(self) -> Dict[str, Any]:
        """Check MinIO health"""
        try:
            minio_endpoint = os.getenv("MINIO_ENDPOINT")
            if not minio_endpoint:
                return {
                    "status": "disabled",
                    "message": "MinIO endpoint not configured",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            response = requests.get(f"{minio_endpoint}/minio/health/live", timeout=5)
            response.raise_for_status()
            
            return {
                "status": "healthy",
                "message": "MinIO connection successful",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": f"MinIO connection failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def check_external_apis(self) -> Dict[str, Any]:
        """Check external API health"""
        results = {}
        
        # Check Slack API
        try:
            slack_token = os.getenv("SLACK_BOT_TOKEN")
            if slack_token and slack_token.strip() and not slack_token.startswith("your-"):
                response = requests.get(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {slack_token}"},
                    timeout=5
                )
                results["slack"] = {
                    "status": "healthy" if response.json().get("ok") else "unhealthy",
                    "message": "Slack API accessible"
                }
            else:
                results["slack"] = {
                    "status": "disabled",
                    "message": "Slack token not configured"
                }
        except Exception as e:
            results["slack"] = {
                "status": "unhealthy",
                "message": f"Slack API check failed: {str(e)}"
            }
        
        # Check GitHub API
        try:
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token and github_token.strip() and not github_token.startswith("your-"):
                response = requests.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"token {github_token}"},
                    timeout=5
                )
                results["github"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "message": "GitHub API accessible"
                }
            else:
                results["github"] = {
                    "status": "disabled",
                    "message": "GitHub token not configured"
                }
        except Exception as e:
            results["github"] = {
                "status": "unhealthy",
                "message": f"GitHub API check failed: {str(e)}"
            }
        
        # Check OpenRouter API
        try:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if openrouter_key and openrouter_key.strip() and not openrouter_key.startswith("your-"):
                response = requests.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {openrouter_key}"},
                    timeout=5
                )
                results["openrouter"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "message": "OpenRouter API accessible"
                }
            else:
                results["openrouter"] = {
                    "status": "disabled",
                    "message": "OpenRouter API key not configured"
                }
        except Exception as e:
            results["openrouter"] = {
                "status": "unhealthy",
                "message": f"OpenRouter API check failed: {str(e)}"
            }
        
        return results
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall application health status"""
        checks = {
            "database": self.check_database(),
            "redis": self.check_redis(),
            "minio": self.check_minio(),
            "external_apis": self.check_external_apis()
        }
        
        # Determine overall status
        unhealthy_components = []
        for component, result in checks.items():
            if component == "external_apis":
                for api, api_result in result.items():
                    if api_result["status"] == "unhealthy":
                        unhealthy_components.append(f"{component}.{api}")
            elif result["status"] == "unhealthy":
                unhealthy_components.append(component)
        
        overall_status = "healthy" if not unhealthy_components else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": checks,
            "unhealthy_components": unhealthy_components,
            "version": os.getenv("APP_VERSION", "1.0.0")
        }
