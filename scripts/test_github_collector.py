#!/usr/bin/env python3
"""
測試GitHub收集器的README收集和分塊功能
"""
import os
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from collectors.github_collector import GitHubCollector

def test_github_collector():
    """測試GitHub收集器"""
    # 設置日誌
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # 獲取GitHub token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        logger.error("請設置 GITHUB_TOKEN 環境變量")
        return
    
    # 初始化收集器
    collector = GitHubCollector(token)
    
    # 測試收集特定倉庫的文件
    test_repos = [
        'opensource4you/readme',  # 完整收集策略
        'apache/yunikorn-core',   # 簡化收集策略
        'apache/kafka'            # 簡化收集策略
    ]
    
    for repo_name in test_repos:
        logger.info(f"\n=== 測試收集倉庫: {repo_name} ===")
        
        try:
            # 收集文件
            files = collector.collect_repository_files(repo_name)
            
            # 統計結果
            readme_files = [f for f in files if 'readme' in f.name.lower()]
            md_files = [f for f in files if f.name.lower().endswith('.md')]
            chunks = [f for f in files if f.metadata.get('is_chunk', False)]
            
            logger.info(f"總文件數: {len(files)}")
            logger.info(f"README文件: {len(readme_files)}")
            logger.info(f"Markdown文件: {len(md_files)}")
            logger.info(f"分塊文件: {len(chunks)}")
            
            # 顯示README文件內容預覽
            for readme_file in readme_files[:2]:  # 只顯示前2個README文件
                logger.info(f"\n--- {readme_file.path} ---")
                content_preview = readme_file.content[:300] + "..." if len(readme_file.content) > 300 else readme_file.content
                logger.info(f"內容預覽: {content_preview}")
                
                if readme_file.metadata.get('is_chunk'):
                    logger.info(f"分塊信息: 第{readme_file.metadata.get('chunk_index', '?')}個，共{readme_file.metadata.get('total_chunks', '?')}個")
                    logger.info(f"分塊類型: {readme_file.metadata.get('split_type', 'unknown')}")
            
        except Exception as e:
            logger.error(f"收集倉庫 {repo_name} 失敗: {e}")

if __name__ == "__main__":
    test_github_collector()

測試GitHub收集器的README收集和分塊功能
"""
import os
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from collectors.github_collector import GitHubCollector

def test_github_collector():
    """測試GitHub收集器"""
    # 設置日誌
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # 獲取GitHub token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        logger.error("請設置 GITHUB_TOKEN 環境變量")
        return
    
    # 初始化收集器
    collector = GitHubCollector(token)
    
    # 測試收集特定倉庫的文件
    test_repos = [
        'opensource4you/readme',  # 完整收集策略
        'apache/yunikorn-core',   # 簡化收集策略
        'apache/kafka'            # 簡化收集策略
    ]
    
    for repo_name in test_repos:
        logger.info(f"\n=== 測試收集倉庫: {repo_name} ===")
        
        try:
            # 收集文件
            files = collector.collect_repository_files(repo_name)
            
            # 統計結果
            readme_files = [f for f in files if 'readme' in f.name.lower()]
            md_files = [f for f in files if f.name.lower().endswith('.md')]
            chunks = [f for f in files if f.metadata.get('is_chunk', False)]
            
            logger.info(f"總文件數: {len(files)}")
            logger.info(f"README文件: {len(readme_files)}")
            logger.info(f"Markdown文件: {len(md_files)}")
            logger.info(f"分塊文件: {len(chunks)}")
            
            # 顯示README文件內容預覽
            for readme_file in readme_files[:2]:  # 只顯示前2個README文件
                logger.info(f"\n--- {readme_file.path} ---")
                content_preview = readme_file.content[:300] + "..." if len(readme_file.content) > 300 else readme_file.content
                logger.info(f"內容預覽: {content_preview}")
                
                if readme_file.metadata.get('is_chunk'):
                    logger.info(f"分塊信息: 第{readme_file.metadata.get('chunk_index', '?')}個，共{readme_file.metadata.get('total_chunks', '?')}個")
                    logger.info(f"分塊類型: {readme_file.metadata.get('split_type', 'unknown')}")
            
        except Exception as e:
            logger.error(f"收集倉庫 {repo_name} 失敗: {e}")

if __name__ == "__main__":
    test_github_collector()
