"""
Grok API 嵌入生成模組
使用 Grok Fast 4 API 生成嵌入，提供更好的中文支持
"""
import os
import logging
import pickle
import hashlib
import requests
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from utils.logging_config import structured_logger

class GrokEmbeddingGenerator:
    """Grok API 嵌入生成器"""
    
    def __init__(self, api_key: str = None, cache_dir: str = 'cache/embeddings'):
        """
        初始化 Grok 嵌入生成器
        
        Args:
            api_key: OpenRouter API key
            cache_dir: 緩存目錄
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
        
        self.cache_dir = cache_dir
        self.logger = logging.getLogger(__name__)
        
        # 創建緩存目錄
        os.makedirs(cache_dir, exist_ok=True)
        
        # API 配置
        self.api_url = "https://openrouter.ai/api/v1/embeddings"
        self.model_name = "x-ai/grok-4-fast:free"
        self.max_tokens = 8192
        self.timeout = 30
        
        # 緩存配置
        self.cache_enabled = True
        self.cache_ttl = timedelta(days=30)  # 緩存30天
        
        # 批量處理配置
        self.batch_size = 10  # Grok API 限制較小
        self.max_sequence_length = 4000  # 保守估計
        
        # 統計信息
        self.stats = {
            'total_embeddings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_calls': 0,
            'error_count': 0,
            'rate_limit_hits': 0
        }
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        生成單個文本的嵌入
        
        Args:
            text: 輸入文本
            
        Returns:
            嵌入向量
        """
        if not text or not text.strip():
            return None
        
        try:
            # 檢查緩存
            if self.cache_enabled:
                cached_embedding = self._get_cached_embedding(text)
                if cached_embedding is not None:
                    self.stats['cache_hits'] += 1
                    return cached_embedding
                self.stats['cache_misses'] += 1
            
            # 生成嵌入
            embedding = self._call_grok_api([text])
            if embedding and len(embedding) > 0:
                embedding_vector = embedding[0]
                
                # 保存到緩存
                if self.cache_enabled:
                    self._cache_embedding(text, embedding_vector)
                
                self.stats['total_embeddings'] += 1
                return embedding_vector
            
            return None
            
        except Exception as e:
            self.logger.error(f"生成嵌入失敗: {e}")
            self.stats['error_count'] += 1
            return None
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        批量生成嵌入
        
        Args:
            texts: 文本列表
            
        Returns:
            嵌入向量列表
        """
        if not texts:
            return []
        
        embeddings = []
        start_time = datetime.now()
        
        try:
            # 預處理文本
            processed_texts = self._preprocess_texts(texts)
            
            # 分批處理
            for i in range(0, len(processed_texts), self.batch_size):
                batch_texts = processed_texts[i:i + self.batch_size]
                batch_embeddings = self._process_batch(batch_texts)
                embeddings.extend(batch_embeddings)
                
                # 避免速率限制
                if i + self.batch_size < len(processed_texts):
                    time.sleep(0.5)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # 記錄統計
            structured_logger.log_performance(
                operation='grok_batch_embedding_generation',
                duration=duration,
                metrics={
                    'text_count': len(texts),
                    'batch_size': self.batch_size,
                    'model_name': self.model_name
                }
            )
            
            self.logger.info(f"Grok 批量嵌入生成完成，共 {len(texts)} 個文本，耗時 {duration:.2f} 秒")
            
        except Exception as e:
            self.logger.error(f"批量生成嵌入失敗: {e}")
            self.stats['error_count'] += 1
            # 返回空嵌入列表
            embeddings = [None] * len(texts)
        
        return embeddings
    
    def _preprocess_texts(self, texts: List[str]) -> List[str]:
        """預處理文本"""
        processed = []
        
        for text in texts:
            if not text or not text.strip():
                processed.append("")
                continue
            
            # 截斷過長的文本
            if len(text) > self.max_sequence_length:
                text = text[:self.max_sequence_length]
            
            # 清理文本
            text = text.strip()
            processed.append(text)
        
        return processed
    
    def _process_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """處理單個批次"""
        try:
            # 過濾空文本
            non_empty_texts = [text for text in texts if text.strip()]
            empty_indices = [i for i, text in enumerate(texts) if not text.strip()]
            
            if not non_empty_texts:
                return [None] * len(texts)
            
            # 調用 Grok API
            embeddings = self._call_grok_api(non_empty_texts)
            
            # 重新組裝結果
            result = []
            non_empty_idx = 0
            
            for i, text in enumerate(texts):
                if i in empty_indices:
                    result.append(None)
                else:
                    if embeddings and non_empty_idx < len(embeddings):
                        result.append(embeddings[non_empty_idx])
                    else:
                        result.append(None)
                    non_empty_idx += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"處理批次失敗: {e}")
            return [None] * len(texts)
    
    def _call_grok_api(self, texts: List[str]) -> Optional[List[List[float]]]:
        """調用 Grok API 生成嵌入"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo",  # 可選
                "X-Title": "Community AI Agent"  # 可選
            }
            
            data = {
                "model": self.model_name,
                "input": texts
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            self.stats['api_calls'] += 1
            
            if response.status_code == 200:
                result = response.json()
                embeddings = []
                
                for item in result.get('data', []):
                    if 'embedding' in item:
                        embeddings.append(item['embedding'])
                
                return embeddings
                
            elif response.status_code == 429:
                # 速率限制
                self.stats['rate_limit_hits'] += 1
                self.logger.warning("Grok API 速率限制，等待 60 秒...")
                time.sleep(60)
                # 重試一次
                return self._call_grok_api(texts)
                
            else:
                self.logger.error(f"Grok API 錯誤: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("Grok API 請求超時")
            return None
        except Exception as e:
            self.logger.error(f"調用 Grok API 失敗: {e}")
            return None
    
    def _get_cache_key(self, text: str) -> str:
        """生成緩存鍵"""
        # 使用文本和模型名稱生成哈希
        content = f"grok:{self.model_name}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """從緩存獲取嵌入"""
        try:
            cache_key = self._get_cache_key(text)
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
            
            if not os.path.exists(cache_file):
                return None
            
            # 檢查文件時間
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - file_time > self.cache_ttl:
                os.remove(cache_file)
                return None
            
            # 載入緩存
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            return cache_data.get('embedding')
            
        except Exception as e:
            self.logger.warning(f"讀取緩存失敗: {e}")
            return None
    
    def _cache_embedding(self, text: str, embedding: List[float]):
        """緩存嵌入"""
        try:
            cache_key = self._get_cache_key(text)
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")
            
            cache_data = {
                'text': text,
                'embedding': embedding,
                'model_name': self.model_name,
                'created_at': datetime.now().isoformat()
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
                
        except Exception as e:
            self.logger.warning(f"保存緩存失敗: {e}")
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        計算兩個嵌入的相似度
        
        Args:
            embedding1: 第一個嵌入
            embedding2: 第二個嵌入
            
        Returns:
            相似度分數 (0-1)
        """
        try:
            # 轉換為numpy數組
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 計算餘弦相似度
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"計算相似度失敗: {e}")
            return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        stats = self.stats.copy()
        
        # 計算緩存命中率
        total_cache_requests = stats['cache_hits'] + stats['cache_misses']
        if total_cache_requests > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / total_cache_requests
        else:
            stats['cache_hit_rate'] = 0.0
        
        # 添加緩存文件數量
        try:
            cache_files = len([f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')])
            stats['cache_files'] = cache_files
        except:
            stats['cache_files'] = 0
        
        return stats
    
    def clear_cache(self, older_than_days: int = 30):
        """清理緩存"""
        try:
            cutoff_time = datetime.now() - timedelta(days=older_than_days)
            removed_count = 0
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.pkl'):
                    file_path = os.path.join(self.cache_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        removed_count += 1
            
            self.logger.info(f"緩存清理完成，移除了 {removed_count} 個文件")
            
        except Exception as e:
            self.logger.error(f"清理緩存失敗: {e}")
