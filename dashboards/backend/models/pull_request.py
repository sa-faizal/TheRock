from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PRFile(BaseModel):
    """Represents a file changed in a PR"""
    filename: str
    additions: int
    deletions: int
    changes: int
    status: str  # 'added', 'removed', 'modified', 'renamed'
    patch: Optional[str] = None
    previous_filename: Optional[str] = None


class PRCommit(BaseModel):
    """Represents a commit in a PR"""
    sha: str
    message: str
    author: str
    date: datetime
    url: str


class PullRequest(BaseModel):
    """Represents a GitHub Pull Request"""
    number: int
    title: str
    body: str
    state: str  # 'open', 'closed', 'merged'
    created_at: datetime
    updated_at: datetime
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    url: str
    author: str
    assignees: List[str]
    labels: List[str]
    draft: bool
    mergeable: Optional[bool] = None
    commits: int
    additions: int
    deletions: int
    changed_files: int


class QualityScore(BaseModel):
    """Quality score for a PR"""
    score: int  # 0-100
    grade: str  # 'A', 'B', 'C', 'D'
    color: str  # 'green', 'yellow', 'orange', 'red'
    issues: List[str]
    recommendation: str


class ReviewComment(BaseModel):
    """A review comment for a PR"""
    type: str  # 'missing_tests', 'test_only', 'flaky_test', 'high_risk', 'failure_history', 'test_suggestions'
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    title: str
    message: str
    files: List[str]


class PRAnalysisResult(BaseModel):
    """Complete analysis result for a PR"""
    pr_number: int
    pr_title: str
    quality_score: QualityScore
    
    # File analysis
    total_files: int
    code_files_count: int
    test_files_count: int
    config_files_count: int
    doc_files_count: int
    
    # Test coverage
    missing_tests: bool
    new_code_lines: int
    new_test_lines: int
    test_coverage_ratio: float
    untested_files: List[str]
    
    # Flags
    is_test_only_pr: bool
    has_high_risk_changes: bool
    has_flaky_test_changes: bool
    has_risky_files: bool
    
    # Details
    flaky_test_changes: List[Dict[str, Any]]
    high_risk_changes: List[Dict[str, Any]]
    risky_files: List[Dict[str, Any]]
    test_suggestions: List[str]
    review_comments: List[ReviewComment]
    
    analyzed_at: datetime


class FlakyTest(BaseModel):
    """Represents a flaky test"""
    test_name: str
    flakiness_score: float  # 0.0 to 1.0
    failure_rate: float     # 0.0 to 1.0
    total_runs: int
    passed_runs: int
    failed_runs: int
    flaky_commits: int
    total_commits: int
    avg_duration_ms: float
    max_duration_ms: float
    min_duration_ms: float
    common_errors: Dict[str, int]
    suggested_fixes: List[str]
    severity: str  # 'critical', 'high', 'medium', 'low'
    last_failure: Optional[datetime] = None


class TestResult(BaseModel):
    """Represents a single test result"""
    test_name: str
    status: str  # 'passed', 'failed', 'skipped'
    commit_sha: str
    run_id: str
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None
    timestamp: datetime


class FlakyTestAnalysis(BaseModel):
    """Analysis results for flaky tests"""
    flaky_tests: List[FlakyTest]
    stable_tests_count: int
    total_tests: int
    flaky_count: int
    time_window_days: int
    analyzed_at: datetime


class PRTestAnalysis(BaseModel):
    """Test analysis specific to a PR"""
    pr_number: int
    newly_flaky_tests: List[FlakyTest]
    newly_flaky_count: int
    pr_flaky_count: int
    baseline_flaky_count: int
    warning: bool
    recommendation: str


class PRReviewSuggestion(BaseModel):
    """AI-generated review suggestions for a PR"""
    pr_number: int
    pr_title: str
    overall_assessment: str
    
    # Suggested actions
    should_approve: bool
    should_request_changes: bool
    blocking_issues: List[str]
    non_blocking_issues: List[str]
    
    # Reviewer suggestions
    suggested_reviewers: List[Dict[str, Any]]  # name, expertise, reason
    
    # Test recommendations
    required_tests: List[str]
    recommended_tests: List[str]
    
    # Risk assessment
    risk_level: str  # 'low', 'medium', 'high', 'critical'
    risk_factors: List[str]
    
    # Comments to post
    inline_comments: List[Dict[str, Any]]  # file, line, comment
    summary_comment: str
    
    generated_at: datetime


class AnalyzePRRequest(BaseModel):
    """Request to analyze a PR"""
    pr_number: int
    include_test_analysis: bool = True
    include_review_suggestions: bool = True


class AnalyzePRResponse(BaseModel):
    """Response from PR analysis"""
    pr: PullRequest
    analysis: PRAnalysisResult
    flaky_test_analysis: Optional[PRTestAnalysis] = None
    review_suggestion: Optional[PRReviewSuggestion] = None



