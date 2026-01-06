import os
from typing import List, Optional, Dict, Any
from github import Github, GithubException
from datetime import datetime, timedelta
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


def rate_limit_handler(func):
    """Decorator to handle GitHub API rate limits with exponential backoff"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Check rate limit before making request
                rate_limit = self.github.get_rate_limit()
                if rate_limit.core.remaining < 10:
                    reset_time = rate_limit.core.reset
                    wait_time = (reset_time - datetime.now()).total_seconds() + 5
                    if wait_time > 0:
                        logger.warning(f"Rate limit low ({rate_limit.core.remaining} remaining). Waiting {wait_time}s")
                        time.sleep(min(wait_time, 60))  # Wait max 60 seconds
                
                return func(self, *args, **kwargs)
                
            except GithubException as e:
                if e.status == 403 and 'rate limit' in str(e).lower():
                    if attempt < max_retries - 1:
                        delay = base_delay ** (attempt + 1)
                        logger.warning(f"Rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        logger.error("Rate limit exceeded after all retries")
                        raise
                elif e.status == 502 or e.status == 503:
                    # Server errors - retry with backoff
                    if attempt < max_retries - 1:
                        delay = base_delay ** (attempt + 1)
                        logger.warning(f"GitHub API error {e.status}, retrying in {delay}s")
                        time.sleep(delay)
                    else:
                        raise
                else:
                    raise
        
        return func(self, *args, **kwargs)
    
    return wrapper


class GitHubService:
    """Service for interacting with GitHub API with smart caching and rate limit handling"""

    def __init__(self, token: Optional[str] = None, repo_owner: str = "ROCm", repo_name: str = "TheRock"):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github = Github(self.token)
        self.repo = self.github.get_repo(f"{repo_owner}/{repo_name}")
        
        # Multi-layer cache similar to therock-monitoring-dashboard
        self.cache = {}  # Dict[str, Dict[str, Any]] - cache_key -> {data, timestamp, ttl}
        
        # Cache durations (in seconds) - configurable via env vars
        self.CACHE_OPEN_ISSUES = int(os.getenv("CACHE_OPEN_ISSUES", 300))  # 5 minutes
        self.CACHE_CLOSED_ISSUES = int(os.getenv("CACHE_CLOSED_ISSUES", 3600))  # 1 hour
        self.CACHE_COMMITS = int(os.getenv("CACHE_COMMITS", 1800))  # 30 minutes
        self.CACHE_ISSUE_DETAILS = int(os.getenv("CACHE_ISSUE_DETAILS", 600))  # 10 minutes
        self.CACHE_COMMENTS = int(os.getenv("CACHE_COMMENTS", 900))  # 15 minutes
        
        logger.info(f"GitHubService initialized with caching enabled")
        logger.info(f"Cache durations - Open Issues: {self.CACHE_OPEN_ISSUES}s, Closed Issues: {self.CACHE_CLOSED_ISSUES}s")
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if still valid"""
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            age = time.time() - cached['timestamp']
            if age < cached['ttl']:
                logger.debug(f"Cache HIT for {cache_key} (age: {age:.1f}s, ttl: {cached['ttl']}s)")
                return cached['data']
            else:
                logger.debug(f"Cache EXPIRED for {cache_key} (age: {age:.1f}s, ttl: {cached['ttl']}s)")
                del self.cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Any, ttl: int):
        """Store data in cache with TTL"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl
        }
        logger.debug(f"Cache SET for {cache_key} (ttl: {ttl}s)")
    
    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache entries, optionally matching a pattern"""
        if pattern:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
            logger.info(f"Cleared {len(keys_to_delete)} cache entries matching '{pattern}'")
        else:
            self.cache.clear()
            logger.info("Cleared all cache entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = time.time()
        valid_entries = sum(1 for v in self.cache.values() if now - v['timestamp'] < v['ttl'])
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self.cache) - valid_entries,
            'cache_keys': list(self.cache.keys())
        }
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current GitHub API rate limit status"""
        try:
            rate_limit = self.github.get_rate_limit()
            return {
                'core': {
                    'remaining': rate_limit.core.remaining,
                    'limit': rate_limit.core.limit,
                    'reset': rate_limit.core.reset.isoformat(),
                    'used': rate_limit.core.limit - rate_limit.core.remaining
                },
                'search': {
                    'remaining': rate_limit.search.remaining,
                    'limit': rate_limit.search.limit,
                    'reset': rate_limit.search.reset.isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error fetching rate limit: {e}")
            return {}

    @rate_limit_handler
    def get_open_issues(
        self, 
        limit: int = 100, 
        since_days: Optional[int] = None,
        labels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch open issues from the repository with caching
        
        Args:
            limit: Maximum number of issues to return
            since_days: Only return issues created in the last N days (optional)
            labels: Filter by specific labels (optional)
        
        Returns:
            List of issue dictionaries
        """
        # Create cache key that includes all filter parameters
        cache_key_parts = [f"open_issues_{limit}"]
        if since_days:
            cache_key_parts.append(f"since_{since_days}")
        if labels:
            cache_key_parts.append(f"labels_{'_'.join(sorted(labels))}")
        cache_key = "_".join(cache_key_parts)
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.info(f"Returning {len(cached_data)} open issues from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching open issues from GitHub API (limit={limit}, since_days={since_days}, labels={labels})")
            
            # Build API parameters
            api_params = {
                'state': 'open',
                'sort': 'created',
                'direction': 'desc'
            }
            
            # Add since date if specified
            if since_days:
                since_date = datetime.now() - timedelta(days=since_days)
                api_params['since'] = since_date
                logger.info(f"Filtering issues since: {since_date.isoformat()}")
            
            # Add labels if specified
            if labels:
                api_params['labels'] = labels
                logger.info(f"Filtering by labels: {labels}")
            
            issues = self.repo.get_issues(**api_params)

            result = []
            # Fetch more items to account for PRs being filtered out
            # We fetch 5x the limit to ensure we get enough actual issues (PRs are common)
            fetch_limit = limit * 5
            logger.info(f"Fetching up to {fetch_limit} items from GitHub API")
            
            item_count = 0
            for issue in issues[:fetch_limit]:
                item_count += 1
                # Skip pull requests (they also appear in issues API)
                if issue.pull_request:
                    logger.debug(f"Skipping PR #{issue.number}")
                    continue

                logger.info(f"Found actual issue #{issue.number}: {issue.title}")
                result.append({
                    'number': issue.number,
                    'title': issue.title,
                    'body': issue.body or "",
                    'state': issue.state,
                    'url': issue.html_url,
                    'created_at': issue.created_at,
                    'updated_at': issue.updated_at,
                    'labels': [{'name': label.name, 'color': label.color, 'description': label.description}
                              for label in issue.labels],
                    'assignees': [assignee.login for assignee in issue.assignees],
                    'comments_count': issue.comments,
                    'author': issue.user.login if issue.user else "unknown"
                })
                
                # Stop once we have enough actual issues
                if len(result) >= limit:
                    break
            
            logger.info(f"Processed {item_count} items, found {len(result)} actual issues")

            # Cache the result
            self._set_cache(cache_key, result, self.CACHE_OPEN_ISSUES)
            
            logger.info(f"Fetched and cached {len(result)} open issues")
            return result

        except GithubException as e:
            logger.error(f"Error fetching issues: {e}")
            raise

    @rate_limit_handler
    def get_issue_by_number(self, issue_number: int) -> Dict[str, Any]:
        """Fetch a specific issue by number with caching"""
        cache_key = f"issue_{issue_number}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.debug(f"Returning issue #{issue_number} from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching issue #{issue_number} from GitHub API")
            issue = self.repo.get_issue(issue_number)

            result = {
                'number': issue.number,
                'title': issue.title,
                'body': issue.body or "",
                'state': issue.state,
                'url': issue.html_url,
                'created_at': issue.created_at,
                'updated_at': issue.updated_at,
                'labels': [{'name': label.name, 'color': label.color, 'description': label.description}
                          for label in issue.labels],
                'assignees': [assignee.login for assignee in issue.assignees],
                'comments_count': issue.comments,
                'author': issue.user.login if issue.user else "unknown"
            }
            
            # Cache the result
            self._set_cache(cache_key, result, self.CACHE_ISSUE_DETAILS)
            
            return result

        except GithubException as e:
            logger.error(f"Error fetching issue #{issue_number}: {e}")
            raise

    @rate_limit_handler
    def get_closed_issues(
        self, 
        days: int = 180, 
        limit: int = 200,
        labels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch recently closed issues for similarity matching with caching
        
        Args:
            days: Number of days to look back (default: 180)
            limit: Maximum number of issues to return (default: 200)
            labels: Filter by specific labels (optional)
        
        Returns:
            List of closed issue dictionaries
        """
        # Create cache key that includes all filter parameters
        cache_key_parts = [f"closed_issues_{days}_{limit}"]
        if labels:
            cache_key_parts.append(f"labels_{'_'.join(sorted(labels))}")
        cache_key = "_".join(cache_key_parts)
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.info(f"Returning {len(cached_data)} closed issues from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching closed issues from GitHub API (days={days}, limit={limit}, labels={labels})")
            
            # Build API parameters
            since_date = datetime.now() - timedelta(days=days)
            api_params = {
                'state': 'closed',
                'sort': 'updated',
                'direction': 'desc',
                'since': since_date
            }
            
            # Add labels if specified
            if labels:
                api_params['labels'] = labels
                logger.info(f"Filtering by labels: {labels}")
            
            issues = self.repo.get_issues(**api_params)

            result = []
            # Fetch more items to account for PRs being filtered out
            fetch_limit = limit * 5
            for issue in issues[:fetch_limit]:
                if issue.pull_request:
                    continue

                result.append({
                    'number': issue.number,
                    'title': issue.title,
                    'body': issue.body or "",
                    'state': issue.state,
                    'url': issue.html_url,
                    'created_at': issue.created_at,
                    'closed_at': issue.closed_at,
                    'labels': [label.name for label in issue.labels],
                })
                
                # Stop once we have enough actual issues
                if len(result) >= limit:
                    break

            # Cache the result (closed issues don't change often, so longer TTL)
            self._set_cache(cache_key, result, self.CACHE_CLOSED_ISSUES)
            
            logger.info(f"Fetched and cached {len(result)} closed issues from last {days} days")
            return result

        except GithubException as e:
            logger.error(f"Error fetching closed issues: {e}")
            raise

    @rate_limit_handler
    def get_commits_since(self, since_date: datetime, until_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get commits in a date range with caching"""
        # Create cache key from dates
        since_str = since_date.strftime('%Y%m%d')
        until_str = until_date.strftime('%Y%m%d') if until_date else 'now'
        cache_key = f"commits_{since_str}_{until_str}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.info(f"Returning {len(cached_data)} commits from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching commits from GitHub API (since={since_date}, until={until_date})")
            commits = self.repo.get_commits(since=since_date, until=until_date)

            result = []
            for commit in commits[:500]:  # Limit to prevent rate limiting
                result.append({
                    'sha': commit.sha,
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date,
                    'url': commit.html_url,
                    'files_changed': [f.filename for f in commit.files] if commit.files else []
                })

            # Cache the result
            self._set_cache(cache_key, result, self.CACHE_COMMITS)
            
            logger.info(f"Fetched and cached {len(result)} commits")
            return result

        except GithubException as e:
            logger.error(f"Error fetching commits: {e}")
            raise

    @rate_limit_handler
    def get_pull_request_for_commit(self, commit_sha: str) -> Optional[Dict[str, Any]]:
        """Find the PR that introduced a specific commit with caching"""
        cache_key = f"pr_commit_{commit_sha}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            # Search for PRs that contain this commit
            prs = self.repo.get_pulls(state='closed', sort='updated', direction='desc')

            result = None
            for pr in prs[:100]:  # Check last 100 PRs
                if pr.merge_commit_sha == commit_sha:
                    result = {
                        'number': pr.number,
                        'title': pr.title,
                        'url': pr.html_url,
                        'merged_at': pr.merged_at,
                        'author': pr.user.login if pr.user else "unknown"
                    }
                    break

            # Cache the result (even if None)
            self._set_cache(cache_key, result, self.CACHE_COMMITS)
            
            return result

        except GithubException as e:
            logger.error(f"Error finding PR for commit {commit_sha}: {e}")
            return None

    @rate_limit_handler
    def add_label_to_issue(self, issue_number: int, label: str) -> bool:
        """Add a label to an issue (invalidates cache for that issue)"""
        try:
            issue = self.repo.get_issue(issue_number)
            issue.add_to_labels(label)
            logger.info(f"Added label '{label}' to issue #{issue_number}")
            
            # Invalidate cache for this issue and open issues list
            self.clear_cache(f"issue_{issue_number}")
            self.clear_cache("open_issues")
            
            return True

        except GithubException as e:
            logger.error(f"Error adding label to issue #{issue_number}: {e}")
            return False

    @rate_limit_handler
    def create_label_if_not_exists(self, name: str, color: str = "0366d6", description: str = "") -> bool:
        """Create a label if it doesn't exist"""
        try:
            # Check if label exists
            try:
                self.repo.get_label(name)
                return True
            except GithubException:
                # Label doesn't exist, create it
                self.repo.create_label(name=name, color=color, description=description)
                logger.info(f"Created label '{name}'")
                return True

        except GithubException as e:
            logger.error(f"Error creating label '{name}': {e}")
            return False

    @rate_limit_handler
    def get_issue_comments(self, issue_number: int) -> List[Dict[str, Any]]:
        """Get all comments for an issue with caching"""
        cache_key = f"comments_{issue_number}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.debug(f"Returning comments for issue #{issue_number} from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching comments for issue #{issue_number} from GitHub API")
            issue = self.repo.get_issue(issue_number)
            comments = issue.get_comments()

            result = [{
                'author': comment.user.login if comment.user else "unknown",
                'body': comment.body,
                'created_at': comment.created_at
            } for comment in comments]
            
            # Cache the result
            self._set_cache(cache_key, result, self.CACHE_COMMENTS)
            
            return result

        except GithubException as e:
            logger.error(f"Error fetching comments for issue #{issue_number}: {e}")
            return []

    # ===== PR-RELATED METHODS =====
    
    @rate_limit_handler
    def get_pull_requests(
        self,
        state: str = 'open',
        limit: int = 30,
        sort: str = 'created',
        direction: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """
        Get pull requests from the repository with caching
        
        Args:
            state: 'open', 'closed', or 'all'
            limit: Maximum number of PRs to return
            sort: 'created', 'updated', 'popularity', 'long-running'
            direction: 'asc' or 'desc'
        """
        cache_key = f"prs_{state}_{limit}_{sort}_{direction}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.info(f"Returning {len(cached_data)} PRs from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching PRs from GitHub API (state={state}, limit={limit})")
            prs = self.repo.get_pulls(state=state, sort=sort, direction=direction)
            
            result = []
            for pr in prs[:limit]:
                result.append({
                    'number': pr.number,
                    'title': pr.title,
                    'body': pr.body or "",
                    'state': pr.state,
                    'created_at': pr.created_at,
                    'updated_at': pr.updated_at,
                    'merged_at': pr.merged_at,
                    'closed_at': pr.closed_at,
                    'url': pr.html_url,
                    'author': pr.user.login if pr.user else "unknown",
                    'assignees': [assignee.login for assignee in pr.assignees],
                    'labels': [label.name for label in pr.labels],
                    'draft': pr.draft,
                    'mergeable': pr.mergeable,
                    'commits': pr.commits,
                    'additions': pr.additions,
                    'deletions': pr.deletions,
                    'changed_files': pr.changed_files
                })
            
            # Cache the result
            ttl = 300 if state == 'open' else 1800  # 5 min for open, 30 min for closed
            self._set_cache(cache_key, result, ttl)
            
            logger.info(f"Fetched and cached {len(result)} PRs")
            return result
        
        except GithubException as e:
            logger.error(f"Error fetching PRs: {e}")
            raise

    @rate_limit_handler
    def get_pull_request(self, pr_number: int) -> Dict[str, Any]:
        """Get a specific pull request by number with caching"""
        cache_key = f"pr_{pr_number}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.debug(f"Returning PR #{pr_number} from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching PR #{pr_number} from GitHub API")
            pr = self.repo.get_pull(pr_number)
            
            result = {
                'number': pr.number,
                'title': pr.title,
                'body': pr.body or "",
                'state': pr.state,
                'created_at': pr.created_at,
                'updated_at': pr.updated_at,
                'merged_at': pr.merged_at,
                'closed_at': pr.closed_at,
                'url': pr.html_url,
                'author': pr.user.login if pr.user else "unknown",
                'assignees': [assignee.login for assignee in pr.assignees],
                'labels': [label.name for label in pr.labels],
                'draft': pr.draft,
                'mergeable': pr.mergeable,
                'commits': pr.commits,
                'additions': pr.additions,
                'deletions': pr.deletions,
                'changed_files': pr.changed_files
            }
            
            # Cache the result
            self._set_cache(cache_key, result, 600)  # 10 minutes
            
            return result
        
        except GithubException as e:
            logger.error(f"Error fetching PR #{pr_number}: {e}")
            raise

    @rate_limit_handler
    def get_pr_files(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get files changed in a PR with caching"""
        cache_key = f"pr_files_{pr_number}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.debug(f"Returning files for PR #{pr_number} from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching files for PR #{pr_number} from GitHub API")
            pr = self.repo.get_pull(pr_number)
            files = pr.get_files()
            
            result = []
            for file in files:
                result.append({
                    'filename': file.filename,
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'changes': file.changes,
                    'status': file.status,
                    'patch': file.patch if hasattr(file, 'patch') else None,
                    'previous_filename': file.previous_filename if hasattr(file, 'previous_filename') else None
                })
            
            # Cache the result
            self._set_cache(cache_key, result, 1800)  # 30 minutes
            
            logger.info(f"Fetched {len(result)} files for PR #{pr_number}")
            return result
        
        except GithubException as e:
            logger.error(f"Error fetching files for PR #{pr_number}: {e}")
            raise

    @rate_limit_handler
    def get_pr_commits(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get commits in a PR with caching"""
        cache_key = f"pr_commits_{pr_number}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.debug(f"Returning commits for PR #{pr_number} from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching commits for PR #{pr_number} from GitHub API")
            pr = self.repo.get_pull(pr_number)
            commits = pr.get_commits()
            
            result = []
            for commit in commits:
                result.append({
                    'sha': commit.sha,
                    'message': commit.commit.message,
                    'author': commit.commit.author.name,
                    'date': commit.commit.author.date,
                    'url': commit.html_url
                })
            
            # Cache the result
            self._set_cache(cache_key, result, 1800)  # 30 minutes
            
            logger.info(f"Fetched {len(result)} commits for PR #{pr_number}")
            return result
        
        except GithubException as e:
            logger.error(f"Error fetching commits for PR #{pr_number}: {e}")
            raise

    @rate_limit_handler
    def get_pr_reviews(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get reviews for a PR with caching"""
        cache_key = f"pr_reviews_{pr_number}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.debug(f"Returning reviews for PR #{pr_number} from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching reviews for PR #{pr_number} from GitHub API")
            pr = self.repo.get_pull(pr_number)
            reviews = pr.get_reviews()
            
            result = []
            for review in reviews:
                result.append({
                    'id': review.id,
                    'user': review.user.login if review.user else "unknown",
                    'body': review.body or "",
                    'state': review.state,
                    'submitted_at': review.submitted_at
                })
            
            # Cache the result
            self._set_cache(cache_key, result, 600)  # 10 minutes
            
            return result
        
        except GithubException as e:
            logger.error(f"Error fetching reviews for PR #{pr_number}: {e}")
            return []

    @rate_limit_handler
    def get_check_runs(self, commit_sha: str) -> List[Dict[str, Any]]:
        """
        Get check runs (CI results) for a specific commit
        
        Args:
            commit_sha: Commit SHA to get check runs for
            
        Returns:
            List of check runs with status and details
        """
        cache_key = f"check_runs_{commit_sha}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.debug(f"Returning check runs for {commit_sha[:7]} from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching check runs for commit {commit_sha[:7]} from GitHub API")
            commit = self.repo.get_commit(commit_sha)
            check_runs = commit.get_check_runs()
            
            result = []
            for run in check_runs:
                result.append({
                    'id': run.id,
                    'name': run.name,
                    'status': run.status,  # queued, in_progress, completed
                    'conclusion': run.conclusion,  # success, failure, neutral, cancelled, timed_out, action_required, skipped
                    'html_url': run.html_url,
                    'details_url': run.details_url,
                    'started_at': run.started_at.isoformat() if run.started_at else None,
                    'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                    'output': {
                        'title': run.output.title if run.output else '',
                        'summary': run.output.summary if run.output else '',
                        'text': run.output.text if run.output else '',
                        'annotations_count': run.output.annotations_count if run.output else 0
                    },
                    'app': {
                        'name': run.app.name if run.app else 'unknown',
                        'slug': run.app.slug if run.app else 'unknown'
                    }
                })
            
            # Cache the result
            self._set_cache(cache_key, result, 300)  # 5 minutes (CI results update frequently)
            
            logger.info(f"Fetched {len(result)} check runs for commit {commit_sha[:7]}")
            return result
        
        except GithubException as e:
            logger.error(f"Error fetching check runs for commit {commit_sha}: {e}")
            return []

    @rate_limit_handler
    def get_workflow_runs(
        self,
        branch: Optional[str] = None,
        limit: int = 20,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get workflow runs for the repository
        
        Args:
            branch: Filter by branch name (optional)
            limit: Maximum number of runs to return
            status: Filter by status (completed, in_progress, queued)
            
        Returns:
            List of workflow runs
        """
        cache_key_parts = [f"workflow_runs_{limit}"]
        if branch:
            cache_key_parts.append(f"branch_{branch}")
        if status:
            cache_key_parts.append(f"status_{status}")
        cache_key = "_".join(cache_key_parts)
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            logger.info(f"Returning {len(cached_data)} workflow runs from cache")
            return cached_data
        
        try:
            logger.info(f"Fetching workflow runs from GitHub API (branch={branch}, limit={limit}, status={status})")
            
            params = {}
            if branch:
                params['branch'] = branch
            if status:
                params['status'] = status
            
            runs = self.repo.get_workflow_runs(**params)
            
            result = []
            for run in runs[:limit]:
                result.append({
                    'id': run.id,
                    'name': run.name,
                    'head_branch': run.head_branch,
                    'head_sha': run.head_sha,
                    'status': run.status,
                    'conclusion': run.conclusion,
                    'workflow_id': run.workflow_id,
                    'url': run.html_url,
                    'created_at': run.created_at.isoformat() if run.created_at else None,
                    'updated_at': run.updated_at.isoformat() if run.updated_at else None,
                    'run_number': run.run_number,
                    'run_attempt': run.run_attempt,
                    'event': run.event
                })
            
            # Cache the result
            self._set_cache(cache_key, result, 300)  # 5 minutes
            
            logger.info(f"Fetched and cached {len(result)} workflow runs")
            return result
        
        except GithubException as e:
            logger.error(f"Error fetching workflow runs: {e}")
            return []

    @rate_limit_handler
    def get_pr_time_metrics(self, pr_number: int) -> Dict[str, Any]:
        """
        Get time-related metrics for a PR
        
        Args:
            pr_number: PR number
            
        Returns:
            Dictionary with time metrics
        """
        cache_key = f"pr_time_metrics_{pr_number}"
        
        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        try:
            pr = self.repo.get_pull(pr_number)
            commits = pr.get_commits()
            reviews = pr.get_reviews()
            
            # Calculate metrics
            created_at = pr.created_at
            updated_at = pr.updated_at
            # Use timezone-aware datetime
            from datetime import timezone
            now = datetime.now(timezone.utc)
            
            # Get last commit time
            last_commit_time = None
            commit_list = list(commits)
            if commit_list:
                last_commit = commit_list[-1]
                last_commit_time = last_commit.commit.author.date
            
            # Get last review time
            last_review_time = None
            review_list = list(reviews)
            if review_list:
                last_review = review_list[-1]
                last_review_time = last_review.submitted_at
            
            # Calculate durations
            time_since_opened = (now - created_at).total_seconds() / 3600  # hours
            time_since_last_commit = (now - last_commit_time).total_seconds() / 3600 if last_commit_time else None
            time_since_last_review = (now - last_review_time).total_seconds() / 3600 if last_review_time else None
            
            result = {
                'opened_at': created_at.isoformat(),
                'updated_at': updated_at.isoformat(),
                'last_commit_at': last_commit_time.isoformat() if last_commit_time else None,
                'last_review_at': last_review_time.isoformat() if last_review_time else None,
                'hours_since_opened': round(time_since_opened, 1),
                'hours_since_last_commit': round(time_since_last_commit, 1) if time_since_last_commit else None,
                'hours_since_last_review': round(time_since_last_review, 1) if time_since_last_review else None,
                'total_commits': pr.commits,
                'total_reviews': len(review_list)
            }
            
            # Cache the result
            self._set_cache(cache_key, result, 600)  # 10 minutes
            
            return result
        
        except GithubException as e:
            logger.error(f"Error fetching PR time metrics for #{pr_number}: {e}")
            return {}
