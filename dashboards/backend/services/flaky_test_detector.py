import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


class FlakyTestDetector:
    """
    Flaky Test Detection Service - Track test pass/fail patterns across runs:
    1. Track test pass/fail patterns across runs on identical commits
    2. Calculate flakiness score per test (% failure rate)
    3. Identify newly introduced flaky tests in PRs
    4. Suggest fixes: add retries, increase timeouts, fix race conditions
    """

    def __init__(self):
        # In-memory storage for test results
        # In production, this would use a database
        self.test_results = []  # List of test run results
        self.flaky_tests = {}   # Dict of test_name -> flakiness_score
        
    def record_test_result(
        self,
        test_name: str,
        status: str,  # 'passed', 'failed', 'skipped'
        commit_sha: str,
        run_id: str,
        duration_ms: Optional[float] = None,
        error_message: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """Record a test result for tracking"""
        
        result = {
            'test_name': test_name,
            'status': status,
            'commit_sha': commit_sha,
            'run_id': run_id,
            'duration_ms': duration_ms,
            'error_message': error_message,
            'timestamp': timestamp or datetime.now()
        }
        
        self.test_results.append(result)
        
        # Update flakiness score
        self._update_flakiness_score(test_name)
        
        return result

    def _update_flakiness_score(self, test_name: str):
        """Calculate and update flakiness score for a test"""
        
        # Get all results for this test on the same commit
        test_runs = defaultdict(list)  # commit_sha -> [results]
        
        for result in self.test_results:
            if result['test_name'] == test_name:
                test_runs[result['commit_sha']].append(result)
        
        # Calculate flakiness score
        flaky_count = 0
        total_commits = 0
        
        for commit_sha, runs in test_runs.items():
            if len(runs) < 2:  # Need at least 2 runs to detect flakiness
                continue
            
            total_commits += 1
            
            # Check if results differ on same commit
            statuses = [r['status'] for r in runs]
            if len(set(statuses)) > 1:  # Mixed results
                flaky_count += 1
        
        if total_commits > 0:
            flakiness_score = flaky_count / total_commits
            
            self.flaky_tests[test_name] = {
                'test_name': test_name,
                'flakiness_score': round(flakiness_score, 3),
                'total_runs': len([r for r in self.test_results if r['test_name'] == test_name]),
                'flaky_commits': flaky_count,
                'total_commits': total_commits,
                'last_updated': datetime.now(),
                'severity': self._get_severity(flakiness_score)
            }

    def get_flaky_tests(
        self,
        min_score: float = 0.1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get list of flaky tests sorted by flakiness score"""
        
        flaky = [
            test for test in self.flaky_tests.values()
            if test['flakiness_score'] >= min_score
        ]
        
        # Sort by flakiness score (highest first)
        flaky.sort(key=lambda x: x['flakiness_score'], reverse=True)
        
        return flaky[:limit]

    def analyze_test_results(
        self,
        test_results: List[Dict[str, Any]],
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze a batch of test results to identify flaky tests
        
        Args:
            test_results: List of test results with structure:
                {
                    'test_name': str,
                    'status': 'passed'|'failed'|'skipped',
                    'commit_sha': str,
                    'run_id': str,
                    'duration_ms': float,
                    'error_message': str,
                    'timestamp': datetime
                }
            time_window_days: Only consider results from last N days
        """
        
        # Filter by time window
        cutoff_date = datetime.now() - timedelta(days=time_window_days)
        recent_results = [
            r for r in test_results
            if r.get('timestamp', datetime.now()) >= cutoff_date
        ]
        
        # Group by test name and commit
        test_by_commit = defaultdict(lambda: defaultdict(list))
        
        for result in recent_results:
            test_name = result['test_name']
            commit_sha = result['commit_sha']
            test_by_commit[test_name][commit_sha].append(result)
        
        # Analyze each test
        flaky_tests = []
        stable_tests = []
        
        for test_name, commits in test_by_commit.items():
            analysis = self._analyze_single_test(test_name, commits)
            
            if analysis['is_flaky']:
                flaky_tests.append(analysis)
            else:
                stable_tests.append(analysis)
        
        # Sort flaky tests by score
        flaky_tests.sort(key=lambda x: x['flakiness_score'], reverse=True)
        
        return {
            'flaky_tests': flaky_tests,
            'stable_tests': stable_tests,
            'total_tests': len(test_by_commit),
            'flaky_count': len(flaky_tests),
            'stable_count': len(stable_tests),
            'time_window_days': time_window_days,
            'analyzed_at': datetime.now()
        }

    def _analyze_single_test(
        self,
        test_name: str,
        commits: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Analyze a single test across multiple commits/runs"""
        
        total_runs = 0
        passed_runs = 0
        failed_runs = 0
        flaky_commits = 0
        total_commits = len(commits)
        
        durations = []
        error_patterns = defaultdict(int)
        
        for commit_sha, runs in commits.items():
            total_runs += len(runs)
            
            # Check if this commit has inconsistent results
            statuses = [r['status'] for r in runs]
            
            if 'passed' in statuses and 'failed' in statuses:
                flaky_commits += 1
            
            # Count passes and failures
            for run in runs:
                if run['status'] == 'passed':
                    passed_runs += 1
                elif run['status'] == 'failed':
                    failed_runs += 1
                
                # Track duration
                if run.get('duration_ms'):
                    durations.append(run['duration_ms'])
                
                # Track error patterns
                if run.get('error_message'):
                    # Extract error type
                    error_type = self._extract_error_type(run['error_message'])
                    error_patterns[error_type] += 1
        
        # Calculate metrics
        failure_rate = failed_runs / total_runs if total_runs > 0 else 0
        flakiness_score = flaky_commits / total_commits if total_commits > 0 else 0
        
        is_flaky = flakiness_score > 0.1 or (0.05 < failure_rate < 0.95 and total_runs >= 5)
        
        # Calculate duration statistics
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        # Suggest fixes
        fixes = self._suggest_fixes(
            test_name, flakiness_score, durations, error_patterns
        )
        
        return {
            'test_name': test_name,
            'is_flaky': is_flaky,
            'flakiness_score': round(flakiness_score, 3),
            'failure_rate': round(failure_rate, 3),
            'total_runs': total_runs,
            'passed_runs': passed_runs,
            'failed_runs': failed_runs,
            'flaky_commits': flaky_commits,
            'total_commits': total_commits,
            'avg_duration_ms': round(avg_duration, 2),
            'max_duration_ms': round(max_duration, 2),
            'min_duration_ms': round(min_duration, 2),
            'common_errors': dict(sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:3]),
            'suggested_fixes': fixes,
            'severity': self._get_severity(flakiness_score)
        }

    def _extract_error_type(self, error_message: str) -> str:
        """Extract error type from error message"""
        
        if not error_message:
            return 'unknown'
        
        # Common error patterns
        patterns = {
            'timeout': r'timeout|timed out|time limit',
            'assertion': r'assert|assertion failed',
            'segfault': r'segmentation fault|sigsegv',
            'memory': r'out of memory|memory error|cuda.*memory',
            'connection': r'connection.*refused|connection.*reset|connection.*timeout',
            'race_condition': r'race condition|deadlock',
            'null_pointer': r'null pointer|nullptr',
            'cuda_error': r'cuda.*error|hip.*error',
        }
        
        error_lower = error_message.lower()
        
        for error_type, pattern in patterns.items():
            if re.search(pattern, error_lower):
                return error_type
        
        return 'other'

    def _suggest_fixes(
        self,
        test_name: str,
        flakiness_score: float,
        durations: List[float],
        error_patterns: Dict[str, int]
    ) -> List[str]:
        """Suggest fixes for flaky tests based on analysis"""
        
        fixes = []
        
        if flakiness_score < 0.1:
            return []  # Not flaky enough to suggest fixes
        
        # Analyze common errors
        if error_patterns:
            most_common_error = max(error_patterns.items(), key=lambda x: x[1])[0]
            
            if most_common_error == 'timeout':
                fixes.append("Increase test timeout - test may need more time on slower hardware")
                fixes.append("Check for deadlocks or infinite loops in test code")
            
            elif most_common_error == 'race_condition':
                fixes.append("Add synchronization primitives (barriers, locks) to eliminate race conditions")
                fixes.append("Use hipDeviceSynchronize() or hipStreamSynchronize() after kernel launches")
            
            elif most_common_error == 'memory':
                fixes.append("Add proper memory cleanup (hipFree) after allocations")
                fixes.append("Reduce memory allocation size or split into smaller chunks")
                fixes.append("Check for memory leaks using ROCm profiling tools")
            
            elif most_common_error == 'assertion':
                fixes.append("Add retry logic with exponential backoff")
                fixes.append("Review assertion conditions - may be too strict")
            
            elif most_common_error == 'connection':
                fixes.append("Add retry logic for network operations")
                fixes.append("Increase connection timeout values")
            
            elif most_common_error == 'cuda_error':
                fixes.append("Add proper error checking after each CUDA/HIP call")
                fixes.append("Ensure correct GPU device selection and initialization")
        
        # Analyze duration variance
        if len(durations) > 5:
            avg = sum(durations) / len(durations)
            variance = sum((d - avg) ** 2 for d in durations) / len(durations)
            std_dev = variance ** 0.5
            
            if std_dev > avg * 0.5:  # High variance
                fixes.append("Test duration is highly variable - consider splitting into smaller, more focused tests")
                fixes.append("Add warm-up iterations to reduce timing variance")
        
        # General recommendations
        if flakiness_score > 0.3:
            fixes.append("Consider marking as @pytest.mark.flaky with max_runs=3")
            fixes.append("Add detailed logging to diagnose intermittent failures")
        
        # If no specific fixes, provide generic advice
        if not fixes:
            fixes.append("Add retry logic with max 3 attempts")
            fixes.append("Review test for race conditions, timing dependencies, or shared state")
            fixes.append("Ensure proper test isolation and cleanup")
        
        return fixes

    def _get_severity(self, flakiness_score: float) -> str:
        """Determine severity level based on flakiness score"""
        if flakiness_score >= 0.5:
            return 'critical'
        elif flakiness_score >= 0.3:
            return 'high'
        elif flakiness_score >= 0.1:
            return 'medium'
        else:
            return 'low'

    def detect_newly_flaky_tests(
        self,
        pr_number: int,
        pr_test_results: List[Dict[str, Any]],
        baseline_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect tests that became flaky in a PR
        
        Args:
            pr_number: PR number
            pr_test_results: Test results from PR CI runs
            baseline_results: Test results from main branch
        """
        
        # Analyze both sets
        pr_analysis = self.analyze_test_results(pr_test_results, time_window_days=7)
        baseline_analysis = self.analyze_test_results(baseline_results, time_window_days=30)
        
        # Find tests that are flaky in PR but not in baseline
        baseline_flaky = {t['test_name'] for t in baseline_analysis['flaky_tests']}
        pr_flaky = {t['test_name'] for t in pr_analysis['flaky_tests']}
        
        newly_flaky = pr_flaky - baseline_flaky
        
        # Get details for newly flaky tests
        newly_flaky_details = [
            t for t in pr_analysis['flaky_tests']
            if t['test_name'] in newly_flaky
        ]
        
        return {
            'pr_number': pr_number,
            'newly_flaky_tests': newly_flaky_details,
            'newly_flaky_count': len(newly_flaky),
            'pr_flaky_count': len(pr_flaky),
            'baseline_flaky_count': len(baseline_flaky),
            'warning': len(newly_flaky) > 0,
            'recommendation': self._get_flaky_recommendation(len(newly_flaky))
        }

    def _get_flaky_recommendation(self, newly_flaky_count: int) -> str:
        """Get recommendation based on newly flaky test count"""
        if newly_flaky_count == 0:
            return "No new flaky tests detected - safe to merge"
        elif newly_flaky_count <= 2:
            return "Few new flaky tests - review and fix before merge"
        else:
            return "Multiple new flaky tests detected - requires investigation before merge"

    def get_test_history(
        self,
        test_name: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get historical results for a specific test"""
        
        results = [
            r for r in self.test_results
            if r['test_name'] == test_name
        ]
        
        # Sort by timestamp (most recent first)
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return results[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall flaky test statistics"""
        
        total_tests = len(self.flaky_tests)
        flaky_count = len([t for t in self.flaky_tests.values() if t['flakiness_score'] > 0.1])
        
        # Severity breakdown
        severity_counts = defaultdict(int)
        for test in self.flaky_tests.values():
            if test['flakiness_score'] > 0.1:  # Only count actual flaky tests
                severity_counts[test['severity']] += 1
        
        return {
            'total_tests_tracked': total_tests,
            'flaky_tests_count': flaky_count,
            'flaky_percentage': round(flaky_count / total_tests * 100, 2) if total_tests > 0 else 0,
            'severity_breakdown': dict(severity_counts),
            'total_test_results': len(self.test_results),
            'last_updated': datetime.now()
        }



