"""
PostgreSQL儲存模組
實現資料插入、向量相似度搜索、連接池管理
"""
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import numpy as np
import faiss
from utils.logging_config import structured_logger
from storage.connection_pool import get_db_connection, return_db_connection
from collectors.data_merger import StandardizedRecord

class PostgreSQLStorage:
    """PostgreSQL儲存器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 統計信息
        self.stats = {
            'records_inserted': 0,
            'records_updated': 0,
            'records_deleted': 0,
            'searches_performed': 0,
            'errors': 0
        }
        
        # FAISS 索引相關
        self.embedding_dim = None  # 動態檢測嵌入維度
        self.faiss_index = None
        self.record_ids = []  # 記錄對應的 ID
        self._initialize_faiss_index()
    
    def _initialize_faiss_index(self):
        """初始化 FAISS 索引"""
        try:
            # 先檢測嵌入維度
            self._detect_embedding_dimension()
            
            if self.embedding_dim is None:
                self.logger.warning("無法檢測嵌入維度，使用默認值 384")
                self.embedding_dim = 384
            
            # 創建 FAISS 索引 (使用 L2 距離)
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)  # Inner Product for cosine similarity
            self.logger.info(f"FAISS 索引初始化完成，維度: {self.embedding_dim}")
            
            # 自動重建索引
            self._rebuild_faiss_index()
            
        except Exception as e:
            self.logger.error(f"FAISS 索引初始化失敗: {e}")
    
    def _detect_embedding_dimension(self):
        """檢測嵌入維度"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 查找第一個非空的嵌入記錄
            cursor.execute("""
                SELECT embedding FROM community_data 
                WHERE embedding IS NOT NULL AND embedding != '' 
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result and result[0]:
                embedding_data = result[0]
                parsed_embedding = self._parse_embedding(embedding_data)
                if parsed_embedding:
                    self.embedding_dim = len(parsed_embedding)
                    self.logger.info(f"檢測到嵌入維度: {self.embedding_dim}")
                else:
                    self.logger.warning("無法解析嵌入數據")
            else:
                # 如果沒有嵌入數據，使用Gemini embedding的維度
                from ai.gemini_embedding_generator import GeminiEmbeddingGenerator
                try:
                    generator = GeminiEmbeddingGenerator()
                    test_embedding = generator.generate_embedding("test")
                    if test_embedding:
                        self.embedding_dim = len(test_embedding)
                        self.logger.info(f"使用Gemini embedding維度: {self.embedding_dim}")
                    else:
                        self.embedding_dim = 768  # Gemini text-embedding-004的默認維度
                        self.logger.info(f"使用默認Gemini embedding維度: {self.embedding_dim}")
                except Exception as e:
                    self.embedding_dim = 768  # Gemini text-embedding-004的默認維度
                    self.logger.info(f"無法獲取Gemini embedding維度，使用默認維度: {self.embedding_dim}")
            
            return_db_connection(conn)
            
        except Exception as e:
            self.logger.error(f"檢測嵌入維度失敗: {e}")
            self.faiss_index = None
    
    def get_faiss_status(self) -> Dict[str, Any]:
        """獲取 FAISS 索引狀態"""
        return {
            "index_exists": self.faiss_index is not None,
            "total_vectors": self.faiss_index.ntotal if self.faiss_index else 0,
            "record_ids_count": len(self.record_ids),
            "embedding_dim": self.embedding_dim
        }
    
    def _parse_embedding(self, embedding_data) -> Optional[List[float]]:
        """解析嵌入向量數據"""
        try:
            if isinstance(embedding_data, str):
                # 嘗試解析 JSON 格式
                if embedding_data.startswith('[') and embedding_data.endswith(']'):
                    return json.loads(embedding_data)
                else:
                    # 嘗試解析逗號分隔的格式
                    return [float(x.strip()) for x in embedding_data.split(',')]
            elif isinstance(embedding_data, list):
                return embedding_data
            elif isinstance(embedding_data, (tuple, np.ndarray)):
                return list(embedding_data)
            elif isinstance(embedding_data, dict):
                # 如果已經是 dict，可能是從資料庫查詢結果
                self.logger.warning(f"嵌入向量是 dict 格式，跳過: {type(embedding_data)}")
                return None
            else:
                # 嘗試轉換為字串再解析
                try:
                    embedding_str = str(embedding_data)
                    if embedding_str.startswith('[') and embedding_str.endswith(']'):
                        return json.loads(embedding_str)
                except:
                    pass
                self.logger.warning(f"不支援的嵌入向量格式: {type(embedding_data)}")
                return None
        except Exception as e:
            self.logger.error(f"解析嵌入向量失敗: {e}")
            return None
    
    def _rebuild_faiss_index(self):
        """重建 FAISS 索引"""
        try:
            # 從資料庫載入所有嵌入向量
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT id, embedding FROM community_data WHERE embedding IS NOT NULL")
            results = cur.fetchall()
            
            if not results:
                self.logger.info("沒有嵌入向量資料，跳過索引重建")
                return
            
            # 重建索引 (使用cosine similarity)
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)  # Inner Product for cosine similarity
            self.record_ids = []
            
            embeddings = []
            for record_id, embedding_str in results:
                try:
                    # 解析嵌入向量 (支援多種格式)
                    embedding = self._parse_embedding(embedding_str)
                    
                    if embedding and len(embedding) == self.embedding_dim:
                        embeddings.append(embedding)
                        self.record_ids.append(record_id)
                    else:
                        self.logger.warning(f"嵌入向量維度不正確 {record_id}: {len(embedding) if embedding else 'None'}")
                except Exception as e:
                    self.logger.warning(f"解析嵌入向量失敗 {record_id}: {e}")
                    continue
            
            if embeddings:
                embeddings_array = np.array(embeddings, dtype=np.float32)
                # 正規化每個向量以支持cosine similarity
                embeddings_norm = embeddings_array / np.linalg.norm(embeddings_array, axis=1, keepdims=True)
                self.faiss_index.add(embeddings_norm)
                self.logger.info(f"FAISS 索引重建完成，載入 {len(embeddings)} 個向量")
            
            cur.close()
            return_db_connection(conn)
            
        except Exception as e:
            self.logger.error(f"重建 FAISS 索引失敗: {e}")
    
    def insert_record(self, record: StandardizedRecord) -> bool:
        """
        插入單個記錄
        
        Args:
            record: 標準化記錄
            
        Returns:
            是否成功
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 檢查記錄是否已存在
            cur.execute("SELECT id FROM community_data WHERE id = %s", (record.id,))
            if cur.fetchone():
                # 更新現有記錄
                return self._update_record(record, conn, cur)
            else:
                # 插入新記錄
                return self._insert_new_record(record, conn, cur)
                
        except Exception as e:
            self.logger.error(f"插入記錄失敗: {e}")
            self.stats['errors'] += 1
            return False
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                return_db_connection(conn)
    
    def _insert_new_record(self, record: StandardizedRecord, conn, cur) -> bool:
        """插入新記錄"""
        try:
            # 準備嵌入向量 (改為 JSON 格式)
            embedding_vector = None
            if record.embedding:
                embedding_vector = json.dumps(record.embedding)
            
            # 插入記錄
            cur.execute("""
                INSERT INTO community_data (
                    id, platform, content, author_anon, timestamp, source_url, 
                    metadata, embedding, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                record.id,
                record.platform,
                record.content,
                record.author,
                record.timestamp,
                record.source_url,
                json.dumps(record.metadata),
                embedding_vector,
                record.created_at or datetime.now(),
                record.updated_at or datetime.now()
            ))
            
            conn.commit()
            self.stats['records_inserted'] += 1
            
            # 更新 FAISS 索引
            if record.embedding and self.faiss_index:
                try:
                    embedding_array = np.array([record.embedding], dtype=np.float32)
                    self.faiss_index.add(embedding_array)
                    self.record_ids.append(record.id)
                except Exception as e:
                    self.logger.warning(f"更新 FAISS 索引失敗: {e}")
            
            return True
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"插入新記錄失敗: {e}")
            return False
    
    def _update_record(self, record: StandardizedRecord, conn, cur) -> bool:
        """更新現有記錄"""
        try:
            # 準備嵌入向量 (改為 JSON 格式)
            embedding_vector = None
            if record.embedding:
                embedding_vector = json.dumps(record.embedding)
            
            # 更新記錄
            cur.execute("""
                UPDATE community_data SET
                    content = %s,
                    author_anon = %s,
                    timestamp = %s,
                    source_url = %s,
                    metadata = %s,
                    embedding = %s,
                    updated_at = %s
                WHERE id = %s
            """, (
                record.content,
                record.author,
                record.timestamp,
                record.source_url,
                json.dumps(record.metadata),
                embedding_vector,
                record.updated_at or datetime.now(),
                record.id
            ))
            
            conn.commit()
            self.stats['records_updated'] += 1
            return True
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"更新記錄失敗: {e}")
            return False
    
    def insert_records_batch(self, records: List[StandardizedRecord]) -> int:
        """
        批量插入記錄
        
        Args:
            records: 記錄列表
            
        Returns:
            成功插入的記錄數
        """
        if not records:
            return 0
        
        success_count = 0
        start_time = datetime.now()
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            for record in records:
                try:
                    # 檢查記錄是否已存在
                    cur.execute("SELECT id FROM community_data WHERE id = %s", (record.id,))
                    if cur.fetchone():
                        # 更新現有記錄
                        if self._update_record(record, conn, cur):
                            success_count += 1
                    else:
                        # 插入新記錄
                        if self._insert_new_record(record, conn, cur):
                            success_count += 1
                            
                except Exception as e:
                    self.logger.error(f"處理記錄 {record.id} 失敗: {e}")
                    continue
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # 記錄統計
            structured_logger.log_performance(
                operation='batch_insert_records',
                duration=duration,
                metrics={
                    'total_records': len(records),
                    'successful_records': success_count,
                    'failed_records': len(records) - success_count
                }
            )
            
            self.logger.info(f"批量插入完成，成功 {success_count}/{len(records)} 條記錄")
            
        except Exception as e:
            self.logger.error(f"批量插入失敗: {e}")
            self.stats['errors'] += 1
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                return_db_connection(conn)
        
        return success_count
    
    def search_similar_records(self, query_embedding: List[float], 
                             limit: int = 10, 
                             threshold: float = 0.7,
                             platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索相似記錄 (使用 FAISS)
        
        Args:
            query_embedding: 查詢嵌入向量
            limit: 返回記錄數限制
            threshold: 相似度閾值
            platform: 平台過濾
            
        Returns:
            相似記錄列表
        """
        try:
            if not self.faiss_index or self.faiss_index.ntotal == 0:
                self.logger.warning("FAISS 索引為空，重建索引")
                self._rebuild_faiss_index()
                if not self.faiss_index or self.faiss_index.ntotal == 0:
                    return []
            
            # 使用 FAISS 搜索 (cosine similarity)
            query_array = np.array([query_embedding], dtype=np.float32)
            
            # 正規化查詢向量
            query_norm = query_array / np.linalg.norm(query_array)
            
            # 使用FAISS的內積搜索
            similarities, indices = self.faiss_index.search(query_norm, min(limit * 2, self.faiss_index.ntotal))
            similarities = similarities[0]  # 獲取第一個查詢的結果
            indices = indices[0]
            
            # 動態調整閾值 (如果沒有結果，降低閾值)
            adjusted_threshold = threshold
            if np.max(similarities) < threshold:
                adjusted_threshold = max(0.1, np.max(similarities) * 0.8)  # 降低到 0.1
                self.logger.info(f"調整相似度閾值: {threshold} -> {adjusted_threshold}")
            
            # 獲取相似度最高的記錄
            similar_ids = []
            for i, idx in enumerate(indices):
                if idx >= 0 and idx < len(self.record_ids):
                    similarity = float(similarities[i])
                    if similarity >= adjusted_threshold:
                        similar_ids.append((self.record_ids[idx], similarity))
            
            if not similar_ids:
                return []
            
            # 從資料庫獲取完整記錄
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 構建 IN 查詢
            ids = [record_id for record_id, _ in similar_ids]
            placeholders = ','.join(['%s'] * len(ids))
            
            base_query = f"""
                SELECT id, platform, content, author_anon, timestamp, source_url, metadata
                FROM community_data
                WHERE id IN ({placeholders})
            """
            
            params = ids
            
            if platform:
                base_query += " AND platform = %s"
                params.append(platform)
            
            cur.execute(base_query, params)
            results = cur.fetchall()
            
            # 轉換為字典列表並添加相似度
            similarity_map = {record_id: similarity for record_id, similarity in similar_ids}
            records = []
            for row in results:
                record = dict(row)
                record['similarity'] = similarity_map.get(record['id'], 0)
                # 解析元資料
                if record['metadata']:
                    if isinstance(record['metadata'], str):
                        record['metadata'] = json.loads(record['metadata'])
                    # 如果已經是 dict，則不需要解析
                records.append(record)
            
            # 按相似度排序
            records.sort(key=lambda x: x['similarity'], reverse=True)
            records = records[:limit]
            
            self.stats['searches_performed'] += 1
            self.logger.info(f"FAISS 相似度搜索完成，找到 {len(records)} 條記錄")
            
            return records
            
        except Exception as e:
            self.logger.error(f"FAISS 相似度搜索失敗: {e}")
            self.stats['errors'] += 1
            return []
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                return_db_connection(conn)
    
    def search_by_content(self, query: str, 
                         limit: int = 10, 
                         platform: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        按內容搜索記錄
        
        Args:
            query: 查詢文本
            limit: 返回記錄數限制
            platform: 平台過濾
            
        Returns:
            匹配記錄列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # 構建全文搜索查詢
            base_query = """
                SELECT id, platform, content, author_anon, timestamp, source_url, 
                       metadata, ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) as rank
                FROM community_data
                WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s)
            """
            
            params = [query, query]
            
            if platform:
                base_query += " AND platform = %s"
                params.append(platform)
            
            base_query += " ORDER BY rank DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(base_query, params)
            results = cur.fetchall()
            
            # 轉換為字典列表
            records = []
            for row in results:
                record = dict(row)
                # 解析元資料
                if record['metadata']:
                    record['metadata'] = json.loads(record['metadata'])
                records.append(record)
            
            self.logger.info(f"內容搜索完成，找到 {len(records)} 條記錄")
            return records
            
        except Exception as e:
            self.logger.error(f"內容搜索失敗: {e}")
            self.stats['errors'] += 1
            return []
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_records_by_platform(self, platform: str, 
                               limit: int = 100, 
                               offset: int = 0) -> List[Dict[str, Any]]:
        """
        按平台獲取記錄
        
        Args:
            platform: 平台名稱
            limit: 返回記錄數限制
            offset: 偏移量
            
        Returns:
            記錄列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT id, platform, content, author_anon, timestamp, source_url, 
                       metadata, created_at, updated_at
                FROM community_data
                WHERE platform = %s
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            """, (platform, limit, offset))
            
            results = cur.fetchall()
            
            # 轉換為字典列表
            records = []
            for row in results:
                record = dict(row)
                # 解析元資料
                if record['metadata']:
                    record['metadata'] = json.loads(record['metadata'])
                records.append(record)
            
            self.logger.info(f"獲取 {platform} 記錄完成，共 {len(records)} 條")
            return records
            
        except Exception as e:
            self.logger.error(f"獲取記錄失敗: {e}")
            self.stats['errors'] += 1
            return []
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_records_by_time_range(self, start_time: datetime, 
                                 end_time: datetime,
                                 platform: Optional[str] = None,
                                 limit: int = 1000) -> List[Dict[str, Any]]:
        """
        按時間範圍獲取記錄
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            platform: 平台過濾
            limit: 返回記錄數限制
            
        Returns:
            記錄列表
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            base_query = """
                SELECT id, platform, content, author_anon, timestamp, source_url, 
                       metadata, created_at, updated_at
                FROM community_data
                WHERE timestamp BETWEEN %s AND %s
            """
            
            params = [start_time, end_time]
            
            if platform:
                base_query += " AND platform = %s"
                params.append(platform)
            
            base_query += " ORDER BY timestamp DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(base_query, params)
            results = cur.fetchall()
            
            # 轉換為字典列表
            records = []
            for row in results:
                record = dict(row)
                # 解析元資料
                if record['metadata']:
                    record['metadata'] = json.loads(record['metadata'])
                records.append(record)
            
            self.logger.info(f"時間範圍查詢完成，找到 {len(records)} 條記錄")
            return records
            
        except Exception as e:
            self.logger.error(f"時間範圍查詢失敗: {e}")
            self.stats['errors'] += 1
            return []
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                return_db_connection(conn)
    
    def delete_record(self, record_id: str) -> bool:
        """
        刪除記錄
        
        Args:
            record_id: 記錄ID
            
        Returns:
            是否成功
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("DELETE FROM community_data WHERE id = %s", (record_id,))
            conn.commit()
            
            if cur.rowcount > 0:
                self.stats['records_deleted'] += 1
                self.logger.info(f"刪除記錄 {record_id} 成功")
                return True
            else:
                self.logger.warning(f"記錄 {record_id} 不存在")
                return False
                
        except Exception as e:
            self.logger.error(f"刪除記錄失敗: {e}")
            self.stats['errors'] += 1
            return False
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_record_count(self, platform: Optional[str] = None) -> int:
        """
        獲取記錄總數
        
        Args:
            platform: 平台過濾
            
        Returns:
            記錄總數
        """
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            if platform:
                cur.execute("SELECT COUNT(*) FROM community_data WHERE platform = %s", (platform,))
            else:
                cur.execute("SELECT COUNT(*) FROM community_data")
            
            count = cur.fetchone()[0]
            return count
            
        except Exception as e:
            self.logger.error(f"獲取記錄總數失敗: {e}")
            return 0
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                return_db_connection(conn)
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        stats = self.stats.copy()
        
        # 添加記錄總數
        stats['total_records'] = self.get_record_count()
        stats['slack_records'] = self.get_record_count('slack')
        stats['github_records'] = self.get_record_count('github')
        stats['facebook_records'] = self.get_record_count('facebook')
        
        return stats
