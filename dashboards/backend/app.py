from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv

from models.issue import (
    IssueAnalysis, AnalysisRequest, AnalysisResponse,
    IssueLabel, SimilarIssue, RootCauseCommit, ComponentCategory
)
from models.pull_request import (
    PRAnalysisResult, FlakyTestAnalysis, PRReviewSuggestion,
    AnalyzePRRequest, AnalyzePRResponse, PullRequest, QualityScore,
    ReviewComment, FlakyTest, PRTestAnalysis
)
from services.github_service import GitHubService
from services.ai_analyzer import AIAnalyzer
from services.git_tracer import GitTracer
from services.pr_analyzer import PRAnalyzer
from services.flaky_test_detector import FlakyTestDetector
from services.pr_review_generator import PRReviewGenerator
from services.ci_analyzer import CIAnalyzer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ROCm Sentinel - Triaging and Analysis Platform",
    description="AI-powered issue triaging, analysis and root cause detection for ROCm/TheRock repository",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
github_service = None
ai_analyzer = None
git_tracer = None
pr_analyzer = None
flaky_test_detector = None
pr_review_generator = None
ci_analyzer = None


def get_services():
    """Lazy initialization of services"""
    global github_service, ai_analyzer, git_tracer, pr_analyzer, flaky_test_detector, pr_review_generator

    if github_service is None:
        github_service = GitHubService()
        logger.info("GitHub service initialized")

    if ai_analyzer is None:
        ai_analyzer = AIAnalyzer()
        logger.info("AI analyzer initialized")

    if git_tracer is None:
        git_tracer = GitTracer()
        logger.info("Git tracer initialized")
    
    if pr_analyzer is None:
        pr_analyzer = PRAnalyzer()
        logger.info("PR analyzer initialized")
    
    if flaky_test_detector is None:
        flaky_test_detector = FlakyTestDetector()
        logger.info("Flaky test detector initialized")
    
    if pr_review_generator is None:
        pr_review_generator = PRReviewGenerator()
        logger.info("PR review generator initialized")

    return github_service, ai_analyzer, git_tracer, pr_analyzer, flaky_test_detector, pr_review_generator


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ROCm Sentinel - Triaging and Analysis Platform",
        "version": "2.0.0",
        "description": "AI-powered triaging, monitoring and analysis for ROCm/TheRock repository",
        "endpoints": {
            "issues": "/api/issues",
            "issue_details": "/api/issues/{issue_number}",
            "analyze": "/api/analyze",
            "analyze_single": "/api/analyze/issue/{issue_number}",
            "issue_comments": "/api/issues/{issue_number}/comments",
            "pull_requests": "/api/prs",
            "pr_details": "/api/prs/{pr_number}",
            "pr_files": "/api/prs/{pr_number}/files",
            "pr_commits": "/api/prs/{pr_number}/commits",
            "analyze_pr": "/api/prs/{pr_number}/analyze (POST)",
            "flaky_tests": "/api/flaky-tests",
            "record_test": "/api/flaky-tests/record (POST)",
            "test_history": "/api/flaky-tests/{test_name}/history",
            "chat": "/api/chat (POST)",
            "health": "/api/health",
            "cache_status": "/api/cache/status",
            "rate_limit": "/api/rate-limit",
            "clear_cache": "/api/cache/clear (POST)",
            "load_new_issues": "/api/issues/refresh (POST)"
        }
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint with rate limit info"""
    # Only initialize GitHub service for health check (avoid GitTracer for now)
    global github_service
    if github_service is None:
        github_service = GitHubService()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "github": os.getenv("GITHUB_TOKEN") is not None,
            "anthropic": os.getenv("ANTHROPIC_API_KEY") is not None
        },
        "rate_limit": github_service.get_rate_limit_status(),
        "cache": github_service.get_cache_stats()
    }


@app.get("/api/issues", response_model=List[Dict[str, Any]])
async def get_issues(
    limit: int = 20, 
    state: str = "open",
    since_days: Optional[int] = None,
    until_days: Optional[int] = None,
    labels: Optional[str] = None
):
    """
    Get issues from the repository with optional filtering
    
    Args:
        limit: Maximum number of issues to return
        state: 'open' or 'closed'
        since_days: Get issues created/updated in the last N days (e.g., 7, 30, 90)
        until_days: Get issues created up to N days ago (for open issues only)
        labels: Comma-separated list of labels to filter by (e.g., "bug,enhancement")
    """
    try:
        # Only initialize GitHub service (avoid GitTracer)
        global github_service
        if github_service is None:
            github_service = GitHubService()

        # Parse labels if provided
        label_list = [l.strip() for l in labels.split(',')] if labels else None

        if state == "open":
            # For open issues, use the new filtering options
            issues = github_service.get_open_issues(
                limit=limit, 
                since_days=since_days,
                labels=label_list
            )
        elif state == "closed":
            # For closed issues, use days parameter
            days = since_days if since_days else 180
            issues = github_service.get_closed_issues(
                days=days,
                limit=limit,
                labels=label_list
            )
        else:
            raise HTTPException(status_code=400, detail="State must be 'open' or 'closed'")

        # Apply client-side until_days filtering if specified (for open issues only)
        if state == "open" and until_days is not None:
            filtered_issues = []
            now = datetime.now()
            
            for issue in issues:
                created_at = issue['created_at']
                # Convert to naive datetime if timezone-aware
                if hasattr(created_at, 'replace') and created_at.tzinfo is not None:
                    created_at = created_at.replace(tzinfo=None)
                
                days_old = (now - created_at).days
                
                # Keep issues older than until_days
                if days_old >= until_days:
                    filtered_issues.append(issue)
            
            return filtered_issues
        
        # Apply client-side since_days filtering for backward compatibility
        # (now handled by API, but keeping for edge cases)
        if since_days is not None and state == "open":
            filtered_issues = []
            now = datetime.now()
            
            for issue in issues:
                created_at = issue['created_at']
                # Convert to naive datetime if timezone-aware
                if hasattr(created_at, 'replace') and created_at.tzinfo is not None:
                    created_at = created_at.replace(tzinfo=None)
                
                days_old = (now - created_at).days
                
                # Check if issue falls within date range
                if days_old <= since_days:
                    filtered_issues.append(issue)
            
            return filtered_issues
        
        return issues

    except Exception as e:
        logger.error(f"Error fetching issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/issues/{issue_number}")
async def get_issue(issue_number: int):
    """Get a specific issue by number"""
    try:
        # Only initialize GitHub service (avoid GitTracer)
        global github_service
        if github_service is None:
            github_service = GitHubService()
        
        issue = github_service.get_issue_by_number(issue_number)
        return issue

    except Exception as e:
        logger.error(f"Error fetching issue #{issue_number}: {e}")
        raise HTTPException(status_code=404, detail=f"Issue #{issue_number} not found")


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_issues(request: AnalysisRequest):
    """
    Analyze issues using AI
    - Categorize by ROCm component
    - Find similar historical issues
    - Identify root cause commits
    - Generate fix suggestions
    """
    try:
        # Initialize only GitHub and AI services (skip GitTracer for now)
        global github_service, ai_analyzer
        
        if github_service is None:
            github_service = GitHubService()
            logger.info("GitHub service initialized")
        
        if ai_analyzer is None:
            ai_analyzer = AIAnalyzer()
            logger.info("AI analyzer initialized")

        # Fetch issues to analyze
        if request.analyze_all_open:
            issues = github_service.get_open_issues(limit=request.limit)
        elif request.issue_numbers:
            issues = [github_service.get_issue_by_number(num) for num in request.issue_numbers]
        else:
            raise HTTPException(status_code=400, detail="Must specify issue_numbers or analyze_all_open=true")

        # Fetch closed issues for similarity matching
        logger.info("Fetching closed issues for similarity matching...")
        closed_issues = github_service.get_closed_issues(days=180, limit=200)

        # Fetch recent commits for root cause analysis
        logger.info("Fetching recent commits for root cause analysis...")
        recent_commits = []
        try:
            since_date = datetime.now()
            if issues:
                # Use oldest issue creation date
                issue_dates = [issue['created_at'] for issue in issues]
                # Handle both datetime objects and datetime with timezone
                since_date = min(issue_dates)
                # Convert to naive datetime if needed (GitHub API returns timezone-aware)
                if hasattr(since_date, 'replace') and since_date.tzinfo is not None:
                    since_date = since_date.replace(tzinfo=None)

            recent_commits = github_service.get_commits_since(since_date)
        except Exception as e:
            logger.warning(f"Could not fetch commits for root cause analysis: {e}")
            # Continue without commits - analysis will still work

        # Analyze each issue
        analyses = []
        for issue in issues:
            logger.info(f"Analyzing issue #{issue['number']}: {issue['title']}")

            try:
                # Perform AI analysis
                analysis_result = ai_analyzer.analyze_issue(issue, closed_issues, recent_commits)

                # Build IssueAnalysis object
                issue_analysis = IssueAnalysis(
                    issue_number=issue['number'],
                    title=issue['title'],
                    body=issue['body'],
                    created_at=issue['created_at'],
                    state=issue['state'],
                    url=issue['url'],
                    labels=[
                        IssueLabel(
                            name=label['name'],
                            color=label['color'],
                            description=label.get('description')
                        ) for label in issue['labels']
                    ],
                    component_categories=[
                        ComponentCategory(**cat) for cat in analysis_result['component_categories']
                    ],
                    similar_issues=[
                        SimilarIssue(**sim) for sim in analysis_result['similar_issues']
                    ],
                    root_cause_commits=[
                        RootCauseCommit(**commit) for commit in analysis_result['root_cause_commits']
                    ],
                    suggested_labels=analysis_result['suggested_labels'],
                    fix_suggestions=analysis_result['fix_suggestions'],
                    analysis_summary=analysis_result['analysis_summary'],
                    severity=analysis_result['severity']
                )

                analyses.append(issue_analysis)

            except Exception as e:
                logger.error(f"Error analyzing issue #{issue['number']}: {e}")
                continue

        response = AnalysisResponse(
            analyses=analyses,
            total_analyzed=len(analyses),
            timestamp=datetime.now()
        )

        return response

    except Exception as e:
        logger.error(f"Error in analyze endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/issues/{issue_number}/add-labels")
async def add_labels_to_issue(issue_number: int, labels: List[str]):
    """Add labels to an issue"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()

        # Create labels if they don't exist
        for label in labels:
            github_service.create_label_if_not_exists(label)

        # Add labels to issue
        for label in labels:
            github_service.add_label_to_issue(issue_number, label)

        return {"status": "success", "issue_number": issue_number, "labels_added": labels}

    except Exception as e:
        logger.error(f"Error adding labels to issue #{issue_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/commits/recent")
async def get_recent_commits(days: int = 30, limit: int = 50):
    """Get recent commits from the repository"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()

        since_date = datetime.now()
        commits = github_service.get_commits_since(since_date, limit=limit)

        return commits

    except Exception as e:
        logger.error(f"Error fetching commits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/blame/{file_path:path}")
async def git_blame(file_path: str):
    """Git blame for a specific file"""
    try:
        _, _, tracer = get_services()

        blame_data = tracer.blame_file(file_path)
        return blame_data

    except Exception as e:
        logger.error(f"Error running git blame on {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics with cache info"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()

        open_issues = github_service.get_open_issues(limit=100)
        closed_issues = github_service.get_closed_issues(days=30, limit=100)

        # Count issues by component (simplified)
        component_counts = {}

        return {
            "total_open_issues": len(open_issues),
            "total_closed_last_30_days": len(closed_issues),
            "cache_stats": github_service.get_cache_stats(),
            "rate_limit": github_service.get_rate_limit_status(),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cache/clear")
async def clear_cache(pattern: Optional[str] = None):
    """Clear cache entries, optionally matching a pattern"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()
        
        github_service.clear_cache(pattern)
        
        return {
            "status": "success",
            "message": f"Cache cleared{' for pattern: ' + pattern if pattern else ' (all entries)'}",
            "cache_stats": github_service.get_cache_stats()
        }
    
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rate-limit")
async def get_rate_limit():
    """Get current GitHub API rate limit status"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()
        return github_service.get_rate_limit_status()
    
    except Exception as e:
        logger.error(f"Error fetching rate limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache/status")
async def get_cache_status():
    """Get detailed cache status"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()
        return github_service.get_cache_stats()
    
    except Exception as e:
        logger.error(f"Error fetching cache status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/issues/refresh")
async def refresh_issues():
    """Force refresh of open issues cache - clears cache and fetches new issues"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()
        
        # Clear the open issues cache
        github_service.clear_cache("open_issues")
        
        # Fetch fresh issues
        issues = github_service.get_open_issues(limit=100)
        
        return {
            "status": "success",
            "message": "Issues cache refreshed",
            "total_issues": len(issues),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error refreshing issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze/issue/{issue_number}")
async def analyze_single_issue(issue_number: int):
    """
    Analyze a single issue by its number
    Returns detailed AI analysis for one specific issue
    """
    try:
        global github_service, ai_analyzer
        
        if github_service is None:
            github_service = GitHubService()
        
        if ai_analyzer is None:
            ai_analyzer = AIAnalyzer()
        
        logger.info(f"Analyzing single issue #{issue_number}")
        
        # Fetch the specific issue
        issue = github_service.get_issue_by_number(issue_number)
        
        # Fetch closed issues for similarity matching
        logger.info("Fetching closed issues for similarity matching...")
        closed_issues = github_service.get_closed_issues(days=180, limit=200)
        
        # Fetch recent commits
        logger.info("Fetching recent commits...")
        recent_commits = []
        try:
            created_at = issue['created_at']
            if hasattr(created_at, 'replace') and created_at.tzinfo is not None:
                created_at = created_at.replace(tzinfo=None)
            recent_commits = github_service.get_commits_since(created_at)
        except Exception as e:
            logger.warning(f"Could not fetch commits: {e}")
        
        # Perform AI analysis
        analysis_result = ai_analyzer.analyze_issue(issue, closed_issues, recent_commits)
        
        # Get comments for the issue
        comments = github_service.get_issue_comments(issue_number)
        
        # Build response
        from models.issue import IssueAnalysis, IssueLabel, ComponentCategory, SimilarIssue, RootCauseCommit
        
        issue_analysis = IssueAnalysis(
            issue_number=issue['number'],
            title=issue['title'],
            body=issue['body'],
            created_at=issue['created_at'],
            state=issue['state'],
            url=issue['url'],
            labels=[
                IssueLabel(
                    name=label['name'],
                    color=label['color'],
                    description=label.get('description')
                ) for label in issue['labels']
            ],
            component_categories=[
                ComponentCategory(**cat) for cat in analysis_result['component_categories']
            ],
            similar_issues=[
                SimilarIssue(**sim) for sim in analysis_result['similar_issues']
            ],
            root_cause_commits=[
                RootCauseCommit(**commit) for commit in analysis_result['root_cause_commits']
            ],
            suggested_labels=analysis_result['suggested_labels'],
            fix_suggestions=analysis_result['fix_suggestions'],
            analysis_summary=analysis_result['analysis_summary'],
            severity=analysis_result['severity']
        )
        
        return {
            "analysis": issue_analysis,
            "comments": comments,
            "comment_count": len(comments),
            "assignees": issue.get('assignees', []),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error analyzing issue #{issue_number}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/issues/{issue_number}/comments")
async def get_issue_comments(issue_number: int):
    """Get all comments for a specific issue"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()
        
        comments = github_service.get_issue_comments(issue_number)
        return {
            "issue_number": issue_number,
            "comments": comments,
            "total_comments": len(comments)
        }
    
    except Exception as e:
        logger.error(f"Error fetching comments for issue #{issue_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    """Request for chat-based issue query"""
    query: str = Field(..., description="Natural language query about an issue")
    issue_number: Optional[int] = Field(None, description="Specific issue number to query about")


@app.post("/api/chat")
async def chat_query(request: ChatRequest):
    """
    Chat interface for querying issue status
    Examples:
    - "What is the status of issue #123?"
    - "Is issue #456 being triaged?"
    - "Did someone comment on issue #789?"
    - "Who is assigned to issue #321?"
    """
    try:
        global github_service, ai_analyzer
        
        if github_service is None:
            github_service = GitHubService()
        
        if ai_analyzer is None:
            ai_analyzer = AIAnalyzer()
        
        query = request.query.lower()
        
        # Extract issue number from query if not provided
        issue_number = request.issue_number
        if issue_number is None:
            import re
            match = re.search(r'#?(\d+)', query)
            if match:
                issue_number = int(match.group(1))
            else:
                return {
                    "response": "Please specify an issue number in your query (e.g., #123 or 123)",
                    "success": False
                }
        
        # Fetch issue details
        try:
            issue = github_service.get_issue_by_number(issue_number)
        except Exception:
            return {
                "response": f"Issue #{issue_number} not found. Please check the issue number and try again.",
                "success": False
            }
        
        # Get comments
        comments = github_service.get_issue_comments(issue_number)
        
        # Build context for AI
        context = f"""Issue #{issue['number']}: {issue['title']}
State: {issue['state']}
Created: {issue['created_at']}
Updated: {issue['updated_at']}
Assignees: {', '.join(issue['assignees']) if issue['assignees'] else 'None'}
Labels: {', '.join([l['name'] for l in issue['labels']]) if issue['labels'] else 'None'}
Comments: {len(comments)} comments

Recent comments:
"""
        for comment in comments[-3:]:  # Last 3 comments
            context += f"\n- {comment['author']} ({comment['created_at']}): {comment['body'][:200]}"
        
        # Use Claude to answer the query
        try:
            prompt = f"""You are a helpful assistant for the ROCm/TheRock GitHub repository. 
Answer the user's question about this issue based on the following context.

{context}

User question: {request.query}

Provide a concise, helpful answer. If the information is not available in the context, say so."""

            message = ai_analyzer.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            
            return {
                "response": response_text,
                "issue_number": issue_number,
                "issue_title": issue['title'],
                "issue_state": issue['state'],
                "issue_url": issue['url'],
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            # Fallback to basic response
            return {
                "response": f"Issue #{issue_number} is currently {issue['state']}. "
                           f"It has {len(comments)} comments and "
                           f"{'is assigned to ' + ', '.join(issue['assignees']) if issue['assignees'] else 'has no assignees'}.",
                "issue_number": issue_number,
                "issue_url": issue['url'],
                "success": True
            }
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== PR ANALYSIS ENDPOINTS =====

@app.get("/api/prs", response_model=List[Dict[str, Any]])
async def get_pull_requests(
    state: str = "open",
    limit: int = 30,
    sort: str = "created",
    direction: str = "desc"
):
    """
    Get pull requests from the repository
    
    Args:
        state: 'open', 'closed', or 'all'
        limit: Maximum number of PRs to return
        sort: 'created', 'updated', 'popularity', 'long-running'
        direction: 'asc' or 'desc'
    """
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()
        
        prs = github_service.get_pull_requests(state=state, limit=limit, sort=sort, direction=direction)
        return prs
    
    except Exception as e:
        logger.error(f"Error fetching PRs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prs/{pr_number}")
async def get_pull_request(pr_number: int):
    """Get a specific pull request by number"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()
        
        pr = github_service.get_pull_request(pr_number)
        return pr
    
    except Exception as e:
        logger.error(f"Error fetching PR #{pr_number}: {e}")
        raise HTTPException(status_code=404, detail=f"PR #{pr_number} not found")


@app.get("/api/prs/{pr_number}/files")
async def get_pr_files(pr_number: int):
    """Get files changed in a pull request"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()
        
        files = github_service.get_pr_files(pr_number)
        return {"pr_number": pr_number, "files": files, "total_files": len(files)}
    
    except Exception as e:
        logger.error(f"Error fetching files for PR #{pr_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prs/{pr_number}/commits")
async def get_pr_commits(pr_number: int):
    """Get commits in a pull request"""
    try:
        global github_service
        if github_service is None:
            github_service = GitHubService()
        
        commits = github_service.get_pr_commits(pr_number)
        return {"pr_number": pr_number, "commits": commits, "total_commits": len(commits)}
    
    except Exception as e:
        logger.error(f"Error fetching commits for PR #{pr_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prs/{pr_number}/comprehensive")
async def get_comprehensive_pr_analysis(pr_number: int):
    """
    Get comprehensive PR analysis including CI status, test results, and code quality
    
    This endpoint provides:
    1. Linked issues
    2. Overall CI state (which tests pass/fail)
    3. CI job breakdown (build, unit tests, integration tests, lint, security, coverage)
    4. Failing job details (name, error summary, root cause hints, logs link)
    5. Flaky test detection (failed X/10 recent runs)
    6. Review status and timeline
    7. Code quality and risk analysis
    8. Key files modified, dependencies, config changes
    9. PR timeline metrics
    10. CI duration
    """
    try:
        global github_service, ci_analyzer
        
        if github_service is None:
            github_service = GitHubService()
        if ci_analyzer is None:
            ci_analyzer = CIAnalyzer(github_service)
        
        logger.info(f"Fetching comprehensive analysis for PR #{pr_number}")
        
        # Fetch PR details
        pr = github_service.get_pull_request(pr_number)
        files = github_service.get_pr_files(pr_number)
        reviews = github_service.get_pr_reviews(pr_number)
        
        # Get linked issues
        linked_issues = ci_analyzer.get_linked_issues(pr)
        
        # Get CI analysis
        ci_analysis = ci_analyzer.analyze_pr_ci(pr_number, include_history=True)
        
        # Get code quality risks
        quality_risks = ci_analyzer.analyze_code_quality_risks(files)
        
        # Get time metrics
        time_metrics = github_service.get_pr_time_metrics(pr_number)
        
        # Calculate review status
        review_status = {
            'total_reviews': len(reviews),
            'approved_count': sum(1 for r in reviews if r['state'] == 'APPROVED'),
            'changes_requested_count': sum(1 for r in reviews if r['state'] == 'CHANGES_REQUESTED'),
            'commented_count': sum(1 for r in reviews if r['state'] == 'COMMENTED'),
            'latest_reviews': reviews[:5] if reviews else []
        }
        
        # Categorize files
        key_files = {
            'source_files': [f for f in files if f['filename'].endswith(('.cpp', '.c', '.py', '.hip', '.cu', '.h', '.hpp'))],
            'test_files': [f for f in files if 'test' in f['filename'].lower()],
            'config_files': quality_risks['config_changes'],
            'infrastructure': quality_risks['changes_infrastructure'],
            'total_files': len(files)
        }
        
        # Build comprehensive response
        return {
            'pr_number': pr_number,
            'pr_title': pr.get('title', ''),
            'pr_author': pr.get('author', 'unknown'),
            'pr_state': pr.get('state', 'unknown'),
            'pr_url': pr.get('url', ''),
            
            # Linked issues
            'linked_issues': linked_issues,
            
            # CI Status
            'ci_state': ci_analysis['ci_state'],
            'job_analysis': ci_analysis['job_analysis'],
            'failing_jobs': ci_analysis['failing_jobs'],
            'ci_duration': ci_analysis['ci_duration'],
            
            # Flaky tests
            'flaky_tests': ci_analysis['flaky_tests'],
            
            # Review status
            'review_status': review_status,
            
            # Code quality and risks
            'code_quality_risks': quality_risks,
            
            # Files modified
            'key_files': key_files,
            
            # Time metrics
            'time_metrics': time_metrics,
            
            # History comparison
            'history_comparison': ci_analysis.get('history_comparison'),
            
            'analyzed_at': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error in comprehensive PR analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/prs/{pr_number}/analyze")
async def analyze_pr(pr_number: int, include_test_analysis: bool = True, include_review_suggestions: bool = True):
    """
    Analyze a pull request for quality issues
    
    This endpoint provides:
    1. Quality score (0-100) with grade (A-D)
    2. Missing test detection
    3. Test-only PR detection
    4. Flaky test modification detection
    5. High-risk change detection (GPU kernels, distributed training)
    6. File failure history analysis
    7. Specific test case suggestions
    8. Review comments and recommendations
    """
    try:
        global github_service, pr_analyzer, flaky_test_detector, pr_review_generator
        
        if github_service is None:
            github_service = GitHubService()
        if pr_analyzer is None:
            pr_analyzer = PRAnalyzer()
        if flaky_test_detector is None:
            flaky_test_detector = FlakyTestDetector()
        if pr_review_generator is None:
            pr_review_generator = PRReviewGenerator()
        
        logger.info(f"Analyzing PR #{pr_number}")
        
        # Fetch PR details
        pr = github_service.get_pull_request(pr_number)
        files = github_service.get_pr_files(pr_number)
        
        # Get commit history for affected files (for root cause analysis)
        commit_history = []
        try:
            # Get commits from the last 60 days for affected files
            since_date = datetime.now() - timedelta(days=60)
            commit_history = github_service.get_commits_since(since_date)
        except Exception as e:
            logger.warning(f"Could not fetch commit history: {e}")
        
        # Get known flaky tests
        flaky_tests = [t['test_name'] for t in flaky_test_detector.get_flaky_tests(min_score=0.2)]
        
        # Perform PR analysis
        logger.info(f"Running quality analysis on PR #{pr_number}")
        analysis_result = pr_analyzer.analyze_pr(pr, files, commit_history, flaky_tests)
        
        # Optional: Perform flaky test analysis
        flaky_test_analysis = None
        if include_test_analysis:
            logger.info(f"Running flaky test analysis on PR #{pr_number}")
            # This would ideally use actual CI test results
            # For now, we'll skip it or use mock data
            flaky_test_analysis = {
                'pr_number': pr_number,
                'newly_flaky_tests': [],
                'newly_flaky_count': 0,
                'pr_flaky_count': len(analysis_result.get('flaky_test_changes', [])),
                'baseline_flaky_count': len(flaky_tests),
                'warning': False,
                'recommendation': 'No new flaky tests detected based on file analysis'
            }
        
        # Optional: Generate review suggestions
        review_suggestion = None
        if include_review_suggestions:
            logger.info(f"Generating review suggestions for PR #{pr_number}")
            review_suggestion = pr_review_generator.generate_review(
                pr, analysis_result, commit_history, flaky_test_analysis
            )
        
        # Build response
        file_analysis = analysis_result['file_analysis']
        missing_tests = analysis_result['missing_tests']
        
        pr_analysis = PRAnalysisResult(
            pr_number=pr['number'],
            pr_title=pr['title'],
            quality_score=QualityScore(**analysis_result['quality_score']),
            total_files=file_analysis['total_files'],
            code_files_count=len(file_analysis['code_files']),
            test_files_count=len(file_analysis['test_files']),
            config_files_count=len(file_analysis['config_files']),
            doc_files_count=len(file_analysis['doc_files']),
            missing_tests=missing_tests['missing_tests'],
            new_code_lines=missing_tests['new_code_lines'],
            new_test_lines=missing_tests['new_test_lines'],
            test_coverage_ratio=missing_tests['test_coverage_ratio'],
            untested_files=missing_tests['untested_files'],
            is_test_only_pr=analysis_result['is_test_only_pr'],
            has_high_risk_changes=len(analysis_result['high_risk_changes']) > 0,
            has_flaky_test_changes=len(analysis_result['flaky_test_changes']) > 0,
            has_risky_files=len(analysis_result['risky_files']) > 0,
            flaky_test_changes=analysis_result['flaky_test_changes'],
            high_risk_changes=analysis_result['high_risk_changes'],
            risky_files=analysis_result['risky_files'],
            test_suggestions=analysis_result['test_suggestions'],
            review_comments=[ReviewComment(**c) for c in analysis_result['review_comments']],
            analyzed_at=datetime.now()
        )
        
        response = {
            'pr': pr,
            'analysis': pr_analysis,
            'flaky_test_analysis': flaky_test_analysis,
            'review_suggestion': review_suggestion
        }
        
        return response
    
    except Exception as e:
        logger.error(f"Error analyzing PR #{pr_number}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flaky-tests")
async def get_flaky_tests(min_score: float = 0.1, limit: int = 50):
    """
    Get list of known flaky tests
    
    Args:
        min_score: Minimum flakiness score (0.0 to 1.0)
        limit: Maximum number of tests to return
    """
    try:
        global flaky_test_detector
        if flaky_test_detector is None:
            flaky_test_detector = FlakyTestDetector()
        
        flaky_tests = flaky_test_detector.get_flaky_tests(min_score=min_score, limit=limit)
        
        return {
            'flaky_tests': flaky_tests,
            'total_count': len(flaky_tests),
            'min_score': min_score,
            'statistics': flaky_test_detector.get_statistics()
        }
    
    except Exception as e:
        logger.error(f"Error fetching flaky tests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/flaky-tests/record")
async def record_test_result(
    test_name: str,
    status: str,
    commit_sha: str,
    run_id: str,
    duration_ms: Optional[float] = None,
    error_message: Optional[str] = None
):
    """
    Record a test result for flaky test tracking
    
    Args:
        test_name: Name of the test
        status: 'passed', 'failed', or 'skipped'
        commit_sha: Commit SHA where test was run
        run_id: Unique identifier for the test run
        duration_ms: Test duration in milliseconds
        error_message: Error message if test failed
    """
    try:
        global flaky_test_detector
        if flaky_test_detector is None:
            flaky_test_detector = FlakyTestDetector()
        
        result = flaky_test_detector.record_test_result(
            test_name=test_name,
            status=status,
            commit_sha=commit_sha,
            run_id=run_id,
            duration_ms=duration_ms,
            error_message=error_message
        )
        
        return {
            'status': 'success',
            'result': result,
            'message': 'Test result recorded successfully'
        }
    
    except Exception as e:
        logger.error(f"Error recording test result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/flaky-tests/{test_name}/history")
async def get_test_history(test_name: str, limit: int = 50):
    """Get historical results for a specific test"""
    try:
        global flaky_test_detector
        if flaky_test_detector is None:
            flaky_test_detector = FlakyTestDetector()
        
        history = flaky_test_detector.get_test_history(test_name, limit=limit)
        
        return {
            'test_name': test_name,
            'history': history,
            'total_results': len(history)
        }
    
    except Exception as e:
        logger.error(f"Error fetching test history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
