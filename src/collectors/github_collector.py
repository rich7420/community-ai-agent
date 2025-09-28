"""
GitHub資料收集器
基於GitPulse實現GitHub資料收集功能
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from github import Github
from github.GithubException import GithubException
import yaml
from utils.logging_config import structured_logger
from utils.pii_filter import PIIFilter
from langchain.text_splitter import RecursiveCharacterTextSplitter

@dataclass
class GitHubIssue:
    """GitHub Issue資料結構"""
    number: int
    title: str
    body: str
    state: str
    author: str
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]
    labels: List[str]
    assignees: List[str]
    comments_count: int
    url: str
    metadata: Dict[str, Any]

@dataclass
class GitHubPR:
    """GitHub Pull Request資料結構"""
    number: int
    title: str
    body: str
    state: str
    author: str
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime]
    closed_at: Optional[datetime]
    labels: List[str]
    assignees: List[str]
    reviewers: List[str]
    comments_count: int
    review_comments_count: int
    commits_count: int
    additions: int
    deletions: int
    url: str
    metadata: Dict[str, Any]

@dataclass
class GitHubCommit:
    """GitHub Commit資料結構"""
    sha: str
    message: str
    author: str
    committer: str
    created_at: datetime
    url: str
    additions: int
    deletions: int
    files_changed: List[str]
    metadata: Dict[str, Any]

@dataclass
class GitHubFile:
    """GitHub 文件資料結構"""
    path: str
    name: str
    content: str
    size: int
    sha: str
    url: str
    download_url: str
    type: str  # file, dir
    encoding: str
    author: str
    last_modified: datetime
    metadata: Dict[str, Any]

class GitHubCollector:
    """GitHub資料收集器"""
    
    def __init__(self, token: str):
        """
        初始化GitHub收集器
        
        Args:
            token: GitHub Personal Access Token
        """
        self.github = Github(token)
        self.pii_filter = PIIFilter()
        self.logger = logging.getLogger(__name__)
        
        # 載入配置
        self.config = self._load_config()
        self.repositories = self.config.get('github', {}).get('repositories', [])
        
        # 收集統計
        self.stats = {
            'issues_collected': 0,
            'prs_collected': 0,
            'commits_collected': 0,
            'repositories_processed': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """載入配置"""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'data_sources.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"載入配置失敗: {e}")
            return {}
    
    def collect_repository_issues(self, repo_name: str, days_back: int = 30) -> List[GitHubIssue]:
        """
        收集指定倉庫的Issues
        
        Args:
            repo_name: 倉庫名稱 (owner/repo)
            days_back: 回溯天數
            
        Returns:
            Issues列表
        """
        issues = []
        start_time = time.time()
        
        try:
            repo = self.github.get_repo(repo_name)
            self.logger.info(f"開始收集倉庫 {repo_name} 的Issues")
            
            # 計算時間範圍
            since = datetime.now() - timedelta(days=days_back)
            
            # 獲取所有issues
            for issue in repo.get_issues(state='all', since=since):
                if issue.pull_request:
                    continue  # 跳過PR
                
                github_issue = self._parse_issue(issue)
                if github_issue:
                    issues.append(github_issue)
                
                # 避免API限制
                time.sleep(0.1)
            
            duration = time.time() - start_time
            self.logger.info(f"倉庫 {repo_name} Issues收集完成，共 {len(issues)} 個，耗時 {duration:.2f} 秒")
            
            # 記錄統計
            structured_logger.log_data_collection(
                platform='github',
                records_count=len(issues),
                duration=duration,
                repository=repo_name,
                data_type='issues'
            )
            
        except GithubException as e:
            if e.status == 403:  # API限制
                wait_time = 60
                self.logger.warning(f"API限制，等待 {wait_time} 秒")
                time.sleep(wait_time)
            else:
                self.logger.error(f"GitHub API錯誤: {e}")
                self.stats['errors'] += 1
        except Exception as e:
            self.logger.error(f"收集Issues失敗: {e}")
            self.stats['errors'] += 1
        
        return issues
    
    def collect_repository_prs(self, repo_name: str, days_back: int = 30) -> List[GitHubPR]:
        """
        收集指定倉庫的Pull Requests
        
        Args:
            repo_name: 倉庫名稱 (owner/repo)
            days_back: 回溯天數
            
        Returns:
            PRs列表
        """
        prs = []
        start_time = time.time()
        
        try:
            repo = self.github.get_repo(repo_name)
            self.logger.info(f"開始收集倉庫 {repo_name} 的Pull Requests")
            
            # 計算時間範圍
            since = datetime.now() - timedelta(days=days_back)
            
            # 獲取所有PRs
            for pr in repo.get_pulls(state='all', sort='created', direction='desc'):
                if pr.created_at < since:
                    break
                
                github_pr = self._parse_pr(pr)
                if github_pr:
                    prs.append(github_pr)
                
                # 避免API限制
                time.sleep(0.1)
            
            duration = time.time() - start_time
            self.logger.info(f"倉庫 {repo_name} PRs收集完成，共 {len(prs)} 個，耗時 {duration:.2f} 秒")
            
            # 記錄統計
            structured_logger.log_data_collection(
                platform='github',
                records_count=len(prs),
                duration=duration,
                repository=repo_name,
                data_type='pull_requests'
            )
            
        except GithubException as e:
            if e.status == 403:  # API限制
                wait_time = 60
                self.logger.warning(f"API限制，等待 {wait_time} 秒")
                time.sleep(wait_time)
            else:
                self.logger.error(f"GitHub API錯誤: {e}")
                self.stats['errors'] += 1
        except Exception as e:
            self.logger.error(f"收集PRs失敗: {e}")
            self.stats['errors'] += 1
        
        return prs
    
    def collect_repository_commits(self, repo_name: str, days_back: int = 30) -> List[GitHubCommit]:
        """
        收集指定倉庫的Commits
        
        Args:
            repo_name: 倉庫名稱 (owner/repo)
            days_back: 回溯天數
            
        Returns:
            Commits列表
        """
        commits = []
        start_time = time.time()
        
        try:
            repo = self.github.get_repo(repo_name)
            self.logger.info(f"開始收集倉庫 {repo_name} 的Commits")
            
            # 計算時間範圍
            since = datetime.now() - timedelta(days=days_back)
            
            # 獲取所有commits
            for commit in repo.get_commits(since=since):
                github_commit = self._parse_commit(commit)
                if github_commit:
                    commits.append(github_commit)
                
                # 避免API限制
                time.sleep(0.1)
            
            duration = time.time() - start_time
            self.logger.info(f"倉庫 {repo_name} Commits收集完成，共 {len(commits)} 個，耗時 {duration:.2f} 秒")
            
            # 記錄統計
            structured_logger.log_data_collection(
                platform='github',
                records_count=len(commits),
                duration=duration,
                repository=repo_name,
                data_type='commits'
            )
            
        except GithubException as e:
            if e.status == 403:  # API限制
                wait_time = 60
                self.logger.warning(f"API限制，等待 {wait_time} 秒")
                time.sleep(wait_time)
            else:
                self.logger.error(f"GitHub API錯誤: {e}")
                self.stats['errors'] += 1
        except Exception as e:
            self.logger.error(f"收集Commits失敗: {e}")
            self.stats['errors'] += 1
        
        return commits
    
    def _parse_issue(self, issue) -> Optional[GitHubIssue]:
        """解析GitHub Issue"""
        try:
            # 匿名化作者
            author = self.pii_filter.anonymize_user(issue.user.login, issue.user.name or '')
            
            # 匿名化標題和內容
            title = self.pii_filter.anonymize_text(issue.title)
            body = self.pii_filter.anonymize_text(issue.body or '')
            
            # 收集標籤
            labels = [label.name for label in issue.labels]
            
            # 收集指派人
            assignees = [self.pii_filter.anonymize_user(assignee.login) for assignee in issue.assignees]
            
            return GitHubIssue(
                number=issue.number,
                title=title,
                body=body,
                state=issue.state,
                author=author,
                created_at=issue.created_at,
                updated_at=issue.updated_at,
                closed_at=issue.closed_at,
                labels=labels,
                assignees=assignees,
                comments_count=issue.comments,
                url=issue.html_url,
                metadata={
                    'original_author': issue.user.login,
                    'original_title': issue.title,
                    'original_body': issue.body,
                    'milestone': issue.milestone.title if issue.milestone else None,
                    'locked': issue.locked,
                    'pull_request': issue.pull_request is not None
                }
            )
            
        except Exception as e:
            self.logger.error(f"解析Issue失敗: {e}")
            return None
    
    def _parse_pr(self, pr) -> Optional[GitHubPR]:
        """解析GitHub Pull Request"""
        try:
            # 匿名化作者
            author = self.pii_filter.anonymize_user(pr.user.login, pr.user.name or '')
            
            # 匿名化標題和內容
            title = self.pii_filter.anonymize_text(pr.title)
            body = self.pii_filter.anonymize_text(pr.body or '')
            
            # 收集標籤
            labels = [label.name for label in pr.labels]
            
            # 收集指派人
            assignees = [self.pii_filter.anonymize_user(assignee.login) for assignee in pr.assignees]
            
            # 收集審查者
            reviewers = [self.pii_filter.anonymize_user(reviewer.login) for reviewer in pr.requested_reviewers]
            
            return GitHubPR(
                number=pr.number,
                title=title,
                body=body,
                state=pr.state,
                author=author,
                created_at=pr.created_at,
                updated_at=pr.updated_at,
                merged_at=pr.merged_at,
                closed_at=pr.closed_at,
                labels=labels,
                assignees=assignees,
                reviewers=reviewers,
                comments_count=pr.comments,
                review_comments_count=pr.review_comments,
                commits_count=pr.commits,
                additions=pr.additions,
                deletions=pr.deletions,
                url=pr.html_url,
                metadata={
                    'original_author': pr.user.login,
                    'original_title': pr.title,
                    'original_body': pr.body,
                    'draft': pr.draft,
                    'mergeable': pr.mergeable,
                    'mergeable_state': pr.mergeable_state,
                    'merged_by': pr.merged_by.login if pr.merged_by else None,
                    'head_branch': pr.head.ref,
                    'base_branch': pr.base.ref
                }
            )
            
        except Exception as e:
            self.logger.error(f"解析PR失敗: {e}")
            return None
    
    def _parse_commit(self, commit) -> Optional[GitHubCommit]:
        """解析GitHub Commit"""
        try:
            # 匿名化作者和提交者
            author = self.pii_filter.anonymize_user(commit.author.login, commit.author.name or '')
            committer = self.pii_filter.anonymize_user(commit.committer.login, commit.committer.name or '')
            
            # 匿名化提交訊息
            message = self.pii_filter.anonymize_text(commit.commit.message)
            
            # 收集修改的文件
            files_changed = []
            try:
                for file in commit.files:
                    files_changed.append(file.filename)
            except:
                pass  # 如果無法獲取文件列表，跳過
            
            return GitHubCommit(
                sha=commit.sha,
                message=message,
                author=author,
                committer=committer,
                created_at=commit.commit.author.date,
                url=commit.html_url,
                additions=commit.stats.additions if commit.stats else 0,
                deletions=commit.stats.deletions if commit.stats else 0,
                files_changed=files_changed,
                metadata={
                    'original_author': commit.author.login,
                    'original_committer': commit.committer.login,
                    'original_message': commit.commit.message,
                    'verification': commit.commit.verification.verified if commit.commit.verification else False,
                    'comment_count': commit.commit.comment_count
                }
            )
            
        except Exception as e:
            self.logger.error(f"解析Commit失敗: {e}")
            return None
    
    def collect_all_repositories(self, days_back: int = 30) -> Dict[str, Any]:
        """收集所有配置倉庫的資料"""
        all_data = {
            'issues': [],
            'pull_requests': [],
            'commits': [],
            'files': []
        }
        
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"開始收集所有倉庫資料，回溯 {days_back} 天")
        
        for repo in self.repositories:
            repo_name = repo.get('name')
            if not repo_name:
                self.logger.warning(f"倉庫配置缺少名稱，跳過")
                continue
            
            try:
                self.logger.info(f"收集倉庫 {repo_name}")
                
                # 只有 opensource4you/readme 倉庫才收集 issues, PRs, commits
                if repo_name == "opensource4you/readme":
                    # 收集Issues
                    issues = self.collect_repository_issues(repo_name, days_back)
                    all_data['issues'].extend(issues)
                    self.stats['issues_collected'] += len(issues)
                    
                    # 收集PRs
                    prs = self.collect_repository_prs(repo_name, days_back)
                    all_data['pull_requests'].extend(prs)
                    self.stats['prs_collected'] += len(prs)
                    
                    # 收集Commits
                    commits = self.collect_repository_commits(repo_name, days_back)
                    all_data['commits'].extend(commits)
                    self.stats['commits_collected'] += len(commits)
                else:
                    self.logger.info(f"跳過 {repo_name} 的 issues, PRs, commits 收集（只收集文件）")
                
                # 收集文件內容（所有倉庫都需要）
                files = self.collect_repository_files(repo_name)
                all_data['files'].extend(files)
                self.stats['files_collected'] = getattr(self.stats, 'files_collected', 0) + len(files)
                
                self.stats['repositories_processed'] += 1
                
                # 避免API限制
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"收集倉庫 {repo_name} 失敗: {e}")
                self.stats['errors'] += 1
        
        self.stats['end_time'] = datetime.now()
        self.logger.info(f"所有倉庫收集完成，Issues: {len(all_data['issues'])}, PRs: {len(all_data['pull_requests'])}, Commits: {len(all_data['commits'])}, Files: {len(all_data['files'])}")
        
        return all_data
    
    def collect_repository_files(self, repo_name: str) -> List[GitHubFile]:
        """收集倉庫文件內容（支持分塊）"""
        files = []
        
        try:
            repo = self.github.get_repo(repo_name)
            self.logger.info(f"開始收集倉庫 {repo_name} 的文件內容")
            
            # 先掃描所有文件和資料夾
            all_items = self._scan_repository_structure(repo, "", repo_name)
            self.logger.info(f"掃描完成，發現 {len(all_items['files'])} 個文件，{len(all_items['dirs'])} 個資料夾")
            
            # 根據策略決定收集哪些文件
            files_to_collect = self._select_files_to_collect(all_items['files'], repo_name)
            self.logger.info(f"選擇收集 {len(files_to_collect)} 個重要文件")
            
            # 收集選定的文件
            for file_info in files_to_collect:
                try:
                    file_data = self._collect_single_file(repo, file_info, repo_name)
                    if file_data:
                        # 根據文件類型決定是否分塊
                        should_chunk = self._should_chunk_file(file_data)
                        if should_chunk:
                            chunks = self._split_file_content(file_data)
                            files.extend(chunks)
                            self.logger.info(f"文件 {file_data.path} 已分塊為 {len(chunks)} 個片段")
                        else:
                            files.append(file_data)
                except Exception as e:
                    self.logger.warning(f"無法收集文件 {file_info['path']}: {e}")
                    continue
            
            self.logger.info(f"倉庫 {repo_name} 文件收集完成，共 {len(files)} 個文件/片段")
            
        except Exception as e:
            self.logger.error(f"收集倉庫 {repo_name} 文件失敗: {e}")
            
        return files
    
    def _split_file_content(self, file_data: GitHubFile) -> List[GitHubFile]:
        """將文件內容分塊，使用多層次智能分割策略"""
        chunks = []
        
        try:
            content = file_data.content
            content_length = len(content)
            file_name = file_data.name.lower()
            
            # README文件特殊處理
            if 'readme' in file_name:
                return self._split_readme_file(file_data, content)
            
            # 根據文件大小採用不同策略
            if content_length <= 1000:
                # 小文件不分塊
                return [file_data]
            elif content_length <= 3000:
                # 中等文件：簡單分塊
                return self._split_medium_file(file_data, content)
            else:
                # 大文件：多層次分塊
                return self._split_large_file(file_data, content)
            
        except Exception as e:
            self.logger.error(f"分塊文件 {file_data.path} 失敗: {e}")
            return [file_data]  # 如果失敗，返回原始文件
    
    def _split_readme_file(self, file_data: GitHubFile, content: str) -> List[GitHubFile]:
        """README文件專用分塊策略，保持語義完整性"""
        chunks = []
        
        try:
            # 首先嘗試按標題分割
            title_chunks = self._split_by_headers(content)
            if len(title_chunks) > 1:
                self.logger.info(f"README文件 {file_data.path} 按標題分為 {len(title_chunks)} 個區塊")
                
                for i, title_chunk in enumerate(title_chunks):
                    if len(title_chunk.strip()) > 100:  # 只保留有意義的塊
                        chunk_data = GitHubFile(
                            path=file_data.path,
                            name=file_data.name,
                            content=title_chunk.strip(),
                            size=len(title_chunk),
                            sha=f"{file_data.sha}_readme_title_{i}",
                            url=file_data.url,
                            download_url=file_data.download_url,
                            type=file_data.type,
                            encoding=file_data.encoding,
                            author=file_data.author,
                            last_modified=file_data.last_modified,
                            metadata={
                                **file_data.metadata,
                                'chunk_index': i,
                                'total_chunks': len(title_chunks),
                                'is_chunk': True,
                                'original_sha': file_data.sha,
                                'split_type': 'readme_title',
                                'title_index': i
                            }
                        )
                        chunks.append(chunk_data)
                
                return chunks
            
            # 如果沒有標題，嘗試按段落分割
            paragraph_chunks = self._split_by_paragraphs(content, max_chunk_size=600)
            if len(paragraph_chunks) > 1:
                self.logger.info(f"README文件 {file_data.path} 按段落分為 {len(paragraph_chunks)} 個區塊")
                return self._create_chunks_from_texts(file_data, paragraph_chunks, "readme_paragraph")
            
            # 最後使用LangChain分割器，針對README優化
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,  # README使用較小的塊
                chunk_overlap=100,  # 增加重疊以保持上下文
                length_function=len,
                separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],
                keep_separator=True
            )
            
            split_texts = text_splitter.split_text(content)
            chunks = self._create_chunks_from_texts(file_data, split_texts, "readme_langchain")
            self.logger.info(f"README文件 {file_data.path} 已使用 LangChain 分塊為 {len(chunks)} 個片段")
            return chunks
            
        except Exception as e:
            self.logger.error(f"README文件分塊失敗 {file_data.path}: {e}")
            return [file_data]  # 如果失敗，返回原始文件
    
    def _split_medium_file(self, file_data: GitHubFile, content: str) -> List[GitHubFile]:
        """中等文件分塊策略"""
        # 按段落分割
        paragraph_chunks = self._split_by_paragraphs(content, max_chunk_size=800)
        if len(paragraph_chunks) > 1:
            chunks = self._create_chunks_from_texts(file_data, paragraph_chunks, "paragraph")
            self.logger.info(f"中等文件 {file_data.path} 已按段落分塊為 {len(chunks)} 個片段")
            return chunks
        
        # 使用 LangChain 分割器
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""],
            keep_separator=True
        )
        
        split_texts = text_splitter.split_text(content)
        chunks = self._create_chunks_from_texts(file_data, split_texts, "langchain")
        self.logger.info(f"中等文件 {file_data.path} 已使用 LangChain 分塊為 {len(chunks)} 個片段")
        return chunks
    
    def _split_large_file(self, file_data: GitHubFile, content: str) -> List[GitHubFile]:
        """大文件多層次分塊策略"""
        chunks = []
        
        # 第一層：按標題分割（保持語義完整性）
        title_chunks = self._split_by_headers(content)
        if len(title_chunks) > 1:
            self.logger.info(f"大文件 {file_data.path} 按標題分為 {len(title_chunks)} 個主要區塊")
            
            # 第二層：對每個標題區塊進行細分
            for i, title_chunk in enumerate(title_chunks):
                if len(title_chunk) > 1000:
                    # 對大區塊進行進一步分割
                    sub_chunks = self._split_by_paragraphs(title_chunk, max_chunk_size=500)
                    for j, sub_chunk in enumerate(sub_chunks):
                        if len(sub_chunk.strip()) > 100:
                            chunk_data = GitHubFile(
                                path=file_data.path,
                                name=file_data.name,
                                content=sub_chunk.strip(),
                                size=len(sub_chunk),
                                sha=f"{file_data.sha}_title_{i}_sub_{j}",
                                url=file_data.url,
                                download_url=file_data.download_url,
                                type=file_data.type,
                                encoding=file_data.encoding,
                                author=file_data.author,
                                last_modified=file_data.last_modified,
                                metadata={
                                    **file_data.metadata,
                                    'chunk_index': len(chunks),
                                    'total_chunks': 0,  # 稍後更新
                                    'is_chunk': True,
                                    'original_sha': file_data.sha,
                                    'split_type': 'title_sub',
                                    'title_index': i,
                                    'sub_index': j
                                }
                            )
                            chunks.append(chunk_data)
                else:
                    # 小區塊直接使用
                    if len(title_chunk.strip()) > 100:
                        chunk_data = GitHubFile(
                            path=file_data.path,
                            name=file_data.name,
                            content=title_chunk.strip(),
                            size=len(title_chunk),
                            sha=f"{file_data.sha}_title_{i}",
                            url=file_data.url,
                            download_url=file_data.download_url,
                            type=file_data.type,
                            encoding=file_data.encoding,
                            author=file_data.author,
                            last_modified=file_data.last_modified,
                            metadata={
                                **file_data.metadata,
                                'chunk_index': len(chunks),
                                'total_chunks': 0,
                                'is_chunk': True,
                                'original_sha': file_data.sha,
                                'split_type': 'title',
                                'title_index': i
                            }
                        )
                        chunks.append(chunk_data)
            
            # 更新總數
            for chunk in chunks:
                chunk.metadata['total_chunks'] = len(chunks)
            
            self.logger.info(f"大文件 {file_data.path} 已多層次分塊為 {len(chunks)} 個片段")
            return chunks
        
        # 如果沒有標題，使用段落分割
        paragraph_chunks = self._split_by_paragraphs(content, max_chunk_size=400)
        if len(paragraph_chunks) > 1:
            chunks = self._create_chunks_from_texts(file_data, paragraph_chunks, "paragraph")
            self.logger.info(f"大文件 {file_data.path} 已按段落分塊為 {len(chunks)} 個片段")
            return chunks
        
        # 最後使用 LangChain 分割器
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,  # 更小的塊
            chunk_overlap=80,  # 增加重疊
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "，", " ", ""],  # 增加更多分隔符
            keep_separator=True
        )
        
        split_texts = text_splitter.split_text(content)
        chunks = self._create_chunks_from_texts(file_data, split_texts, "langchain")
        self.logger.info(f"大文件 {file_data.path} 已使用 LangChain 分塊為 {len(chunks)} 個片段")
        return chunks
    
    def _should_chunk_file(self, file_data: GitHubFile) -> bool:
        """判斷文件是否需要分塊"""
        content_length = len(file_data.content)
        file_name = file_data.name.lower()
        file_path = file_data.path.lower()
        
        # README文件：即使較短也要分塊，以便更好地檢索
        if 'readme' in file_name:
            return content_length > 500  # README文件超過500字元就分塊
        
        # Markdown文件：優先分塊
        if file_name.endswith('.md'):
            return content_length > 800  # Markdown文件超過800字元就分塊
        
        # 文檔目錄中的文件：優先分塊
        if 'docs' in file_path or 'doc' in file_path:
            return content_length > 1000  # 文檔文件超過1000字元就分塊
        
        # 其他文件：按原策略
        return content_length > 2000  # 其他文件超過2000字元才分塊
    
    def _split_by_headers(self, content: str) -> List[str]:
        """按標題分割內容"""
        import re
        
        # 匹配 Markdown 標題
        header_pattern = r'^(#{1,6}\s+.+)$'
        lines = content.split('\n')
        
        chunks = []
        current_chunk = []
        
        for line in lines:
            if re.match(header_pattern, line.strip()):
                # 遇到新標題，保存當前塊
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if len(chunk_text) > 100:  # 只保留有意義的塊
                        chunks.append(chunk_text)
                    current_chunk = []
            
            current_chunk.append(line)
        
        # 處理最後一個塊
        if current_chunk:
            chunk_text = '\n'.join(current_chunk).strip()
            if len(chunk_text) > 100:
                chunks.append(chunk_text)
        
        return chunks if len(chunks) > 1 else [content]
    
    def _split_by_paragraphs(self, content: str, max_chunk_size: int = 1200) -> List[str]:
        """按段落分割內容"""
        # 按雙換行符分割
        paragraphs = content.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # 如果當前塊加上新段落會超過限制
            if current_length + len(paragraph) > max_chunk_size and current_chunk:
                # 保存當前塊
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(chunk_text)
                current_chunk = [paragraph]
                current_length = len(paragraph)
            else:
                current_chunk.append(paragraph)
                current_length += len(paragraph)
        
        # 處理最後一個塊
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(chunk_text)
        
        return chunks if len(chunks) > 1 else [content]
    
    def _create_chunks_from_texts(self, file_data: GitHubFile, texts: List[str], split_type: str) -> List[GitHubFile]:
        """從文本列表創建 GitHubFile 塊"""
        chunks = []
        
        for idx, text in enumerate(texts):
            if len(text.strip()) < 50:  # 跳過太短的塊
                continue
                
            chunk_data = GitHubFile(
                path=file_data.path,
                name=file_data.name,
                content=text.strip(),
                size=len(text),
                sha=f"{file_data.sha}_chunk_{idx}",
                url=file_data.url,
                download_url=file_data.download_url,
                type=file_data.type,
                encoding=file_data.encoding,
                author=file_data.author,
                last_modified=file_data.last_modified,
                metadata={
                    **file_data.metadata,
                    'chunk_index': idx,
                    'total_chunks': len(texts),
                    'is_chunk': True,
                    'original_sha': file_data.sha,
                    'split_type': split_type
                }
            )
            chunks.append(chunk_data)
        
        return chunks
    
    def _scan_repository_structure(self, repo, path: str, repo_name: str = "") -> Dict[str, List[Dict]]:
        """掃描倉庫結構，獲取所有文件和資料夾信息"""
        all_items = {'files': [], 'dirs': []}
        
        try:
            contents = repo.get_contents(path)
            
            for content in contents:
                item_info = {
                    'path': content.path,
                    'name': content.name,
                    'size': content.size,
                    'sha': content.sha,
                    'url': content.html_url,
                    'download_url': content.download_url,
                    'type': content.type,
                    'encoding': getattr(content, 'encoding', 'utf-8'),
                    'last_modified': getattr(content, 'last_modified', None)
                }
                
                if content.type == "file":
                    # 分析文件類型
                    file_ext = content.name.split('.')[-1] if '.' in content.name else ''
                    item_info.update({
                        'extension': file_ext,
                        'is_binary': self._is_binary_file(content.name, file_ext),
                        'importance_score': self._calculate_file_importance(content.name, file_ext, content.size)
                    })
                    all_items['files'].append(item_info)
                    
                elif content.type == "dir":
                    all_items['dirs'].append(item_info)
                    
                    # 只有 opensource4you/readme 倉庫才遞歸掃描子目錄
                    if repo_name == "opensource4you/readme":
                        sub_items = self._scan_repository_structure(repo, content.path, repo_name)
                        all_items['files'].extend(sub_items['files'])
                        all_items['dirs'].extend(sub_items['dirs'])
                    else:
                        # 其他倉庫不掃描子目錄
                        self.logger.info(f"跳過子目錄 {content.path} (非 opensource4you/readme 倉庫)")
                    
        except Exception as e:
            self.logger.warning(f"掃描路徑 {path} 失敗: {e}")
            
        return all_items
    
    def _is_binary_file(self, filename: str, extension: str) -> bool:
        """判斷是否為二進制文件"""
        binary_extensions = {'.exe', '.dll', '.so', '.dylib', '.bin', '.img', '.iso', 
                           '.zip', '.tar', '.gz', '.rar', '.7z', '.pdf', '.doc', '.docx',
                           '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', 
                           '.gif', '.bmp', '.ico', '.svg', '.mp3', '.mp4', '.avi', '.mov'}
        return extension.lower() in binary_extensions
    
    def _calculate_file_importance(self, filename: str, extension: str, size: int) -> int:
        """計算文件重要性分數 (0-100)"""
        score = 0
        
        # 文件名重要性
        important_names = ['readme', 'contributing', 'license', 'changelog', 'history', 
                         'sponsor', 'code_of_conduct', 'security', 'authors', 'maintainers']
        if any(name in filename.lower() for name in important_names):
            score += 40
        
        # 文件擴展名重要性
        important_extensions = {'.md': 30, '.rst': 25, '.txt': 20, '.yml': 15, '.yaml': 15,
                              '.json': 10, '.py': 10, '.js': 8, '.html': 8, '.css': 5}
        score += important_extensions.get(extension.lower(), 0)
        
        # 文件大小調整 (太大或太小都會降低分數)
        if size > 5 * 1024 * 1024:  # 大於5MB
            score -= 20
        elif size < 100:  # 小於100字節
            score -= 10
        elif size > 1024 * 1024:  # 大於1MB
            score -= 10
            
        # 路徑重要性
        if filename.lower() == 'readme.md':
            score += 20
        elif 'docs' in filename.lower() or 'doc' in filename.lower():
            score += 15
        elif filename.startswith('.'):
            score -= 5  # 隱藏文件降低分數
            
        return max(0, min(100, score))
    
    def _select_files_to_collect(self, all_files: List[Dict], repo_name: str = "") -> List[Dict]:
        """根據策略選擇要收集的文件，根據倉庫類型使用不同策略"""
        # 按重要性分數排序
        sorted_files = sorted(all_files, key=lambda x: x['importance_score'], reverse=True)
        
        # 收集策略
        selected_files = []
        
        if repo_name == "opensource4you/readme":
            # opensource4you/readme 倉庫：收集所有文件
            self.logger.info("使用完整收集策略 (opensource4you/readme 倉庫)")
            
            # 1. 收集所有 README 相關文件 (最高優先級)
            readme_files = [f for f in sorted_files if 'readme' in f['name'].lower()]
            selected_files.extend(readme_files)
            self.logger.info(f"選擇收集所有 README 檔案: {len(readme_files)} 個")
            
            # 2. 收集所有 .md 檔案 (第二優先級)
            md_files = [f for f in sorted_files if f['name'].lower().endswith('.md') and 'readme' not in f['name'].lower()]
            selected_files.extend(md_files)
            self.logger.info(f"選擇收集其他 .md 檔案: {len(md_files)} 個")
            
            # 3. 收集文檔目錄中的重要文件
            doc_files = [f for f in sorted_files if ('docs' in f['path'].lower() or 'doc' in f['path'].lower()) 
                        and f['importance_score'] >= 30 and not f['name'].lower().endswith('.md')]
            selected_files.extend(doc_files)
            self.logger.info(f"選擇收集文檔目錄文件: {len(doc_files)} 個")
            
            # 4. 收集其他高分文件 (分數 >= 50)
            high_score_files = [f for f in sorted_files if f['importance_score'] >= 50 
                               and not f['name'].lower().endswith('.md') 
                               and 'readme' not in f['name'].lower()
                               and not ('docs' in f['path'].lower() or 'doc' in f['path'].lower())]
            selected_files.extend(high_score_files)
            self.logger.info(f"選擇收集其他高分文件: {len(high_score_files)} 個")
            
            # 5. 限制總文件數，但確保所有 README 和 .md 檔案都被包含
            max_files = 200  # 增加限制以容納更多文件
            if len(selected_files) > max_files:
                # 優先保留 README 和 .md 檔案
                readme_and_md_files = [f for f in selected_files if f['name'].lower().endswith('.md') or 'readme' in f['name'].lower()]
                other_files = [f for f in selected_files if not (f['name'].lower().endswith('.md') or 'readme' in f['name'].lower())]
                
                # 保留所有 README 和 .md 檔案 + 其他高分檔案
                remaining_slots = max_files - len(readme_and_md_files)
                selected_files = readme_and_md_files + other_files[:remaining_slots]
        
        else:
            # 其他倉庫：只收集最外層的README文件
            self.logger.info("使用簡化收集策略 (只收集最外層README文件)")
            
            # 只收集根目錄的README文件
            readme_files = [f for f in sorted_files if 'readme' in f['name'].lower() and '/' not in f['path']]
            selected_files.extend(readme_files)
            self.logger.info(f"選擇收集根目錄 README 檔案: {len(readme_files)} 個")
            
            # 如果沒有README，收集根目錄的.md文件
            if not readme_files:
                md_files = [f for f in sorted_files if f['name'].lower().endswith('.md') and '/' not in f['path']]
                selected_files.extend(md_files)
                self.logger.info(f"選擇收集根目錄 .md 檔案: {len(md_files)} 個")
        
        # 去重
        seen_paths = set()
        unique_files = []
        for file_info in selected_files:
            if file_info['path'] not in seen_paths:
                unique_files.append(file_info)
                seen_paths.add(file_info['path'])
        
        readme_count = len([f for f in unique_files if 'readme' in f['name'].lower()])
        md_count = len([f for f in unique_files if f['name'].lower().endswith('.md')])
        self.logger.info(f"最終選擇收集 {len(unique_files)} 個檔案，其中 README: {readme_count} 個，.md 檔案: {md_count} 個")
        
        return unique_files
    
    def _collect_single_file(self, repo, file_info: Dict, repo_name: str) -> Optional[GitHubFile]:
        """收集單個文件"""
        try:
            # 獲取文件內容
            content = repo.get_contents(file_info['path'])
            
            if content.size > 2 * 1024 * 1024:  # 限制文件大小為2MB
                self.logger.warning(f"文件 {file_info['path']} 太大 ({content.size} bytes)，跳過")
                return None
            
            file_content = content.decoded_content.decode('utf-8')
            
            file_data = GitHubFile(
                path=file_info['path'],
                name=file_info['name'],
                content=file_content,
                size=file_info['size'],
                sha=file_info['sha'],
                url=file_info['url'],
                download_url=file_info['download_url'],
                type=file_info['type'],
                encoding=file_info['encoding'],
                author=getattr(content, 'author', {}).get('login', 'unknown') if hasattr(content, 'author') else 'unknown',
                last_modified=file_info['last_modified'] or datetime.now(),
                metadata={
                    'repository': repo_name,
                    'file_type': file_info.get('extension', 'unknown'),
                    'importance_score': file_info['importance_score'],
                    'is_binary': file_info['is_binary'],
                    'directory': '/'.join(file_info['path'].split('/')[:-1]) if '/' in file_info['path'] else 'root'
                }
            )
            
            self.logger.info(f"收集文件: {file_info['path']} (重要性: {file_info['importance_score']})")
            return file_data
            
        except Exception as e:
            self.logger.warning(f"無法收集文件 {file_info['path']}: {e}")
            return None
    
    def _collect_files_recursively(self, repo, path: str, important_extensions: List[str], 
                                  important_files: List[str], repo_name: str) -> List[GitHubFile]:
        """遞歸收集文件"""
        files = []
        
        try:
            contents = repo.get_contents(path)
            
            for content in contents:
                if content.type == "file":
                    # 檢查是否為重要文件
                    is_important = (
                        any(important_file in content.name.lower() for important_file in important_files) or
                        any(content.name.endswith(ext) for ext in important_extensions)
                    )
                    
                    if is_important:
                        try:
                            # 獲取文件內容
                            if content.size < 2 * 1024 * 1024:  # 限制文件大小為2MB
                                file_content = content.decoded_content.decode('utf-8')
                                
                                file_data = GitHubFile(
                                    path=content.path,
                                    name=content.name,
                                    content=file_content,
                                    size=content.size,
                                    sha=content.sha,
                                    url=content.html_url,
                                    download_url=content.download_url,
                                    type=content.type,
                                    encoding=getattr(content, 'encoding', 'utf-8'),
                                    author=getattr(content, 'author', {}).get('login', 'unknown') if hasattr(content, 'author') else 'unknown',
                                    last_modified=getattr(content, 'last_modified', datetime.now()),
                                    metadata={
                                        'repository': repo_name,
                                        'file_type': content.name.split('.')[-1] if '.' in content.name else 'unknown',
                                        'is_important': True,
                                        'directory': path if path else 'root'
                                    }
                                )
                                files.append(file_data)
                                self.logger.info(f"收集文件: {content.path}")
                                
                        except Exception as e:
                            self.logger.warning(f"無法讀取文件 {content.path}: {e}")
                            continue
                            
                elif content.type == "dir":
                    # 遞歸收集子目錄
                    try:
                        sub_files = self._collect_files_recursively(repo, content.path, important_extensions, important_files, repo_name)
                        files.extend(sub_files)
                    except Exception as e:
                        self.logger.warning(f"無法訪問目錄 {content.path}: {e}")
                        continue
                        
        except Exception as e:
            self.logger.warning(f"無法訪問路徑 {path}: {e}")
            
        return files
    
    def get_contributors_stats(self, repo_name: str) -> Dict[str, Any]:
        """獲取貢獻者統計"""
        try:
            repo = self.github.get_repo(repo_name)
            contributors = repo.get_contributors()
            
            stats = {}
            for contributor in contributors:
                user_id = contributor.login
                anon_user = self.pii_filter.anonymize_user(user_id, contributor.name or '')
                
                stats[anon_user] = {
                    'contributions': contributor.contributions,
                    'original_id': user_id,
                    'name': contributor.name or '',
                    'avatar_url': contributor.avatar_url
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"獲取貢獻者統計失敗: {e}")
            return {}
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """獲取收集統計"""
        return self.stats.copy()
