import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class CIAnalyzer:
    """
    CI/CD Analysis Service - Analyzes GitHub Actions workflows and test results
    
    Provides comprehensive CI analysis including:
    1. Overall CI state (success/failure/pending)
    2. Individual test results (build, unit, integration, lint, security, coverage)
    3. Failing job details and error summaries
    4. Test failure trends and flaky test detection
    5. Comparison with last successful run
    6. CI duration metrics
    """
    
    # Job name patterns for categorization
    JOB_CATEGORIES = {
        'build': [r'build', r'compile', r'package'],
        'unit_tests': [r'unit[-_]?test', r'unittest', r'test[-_]unit'],
        'integration_tests': [r'integration[-_]?test', r'test[-_]integration', r'e2e', r'end[-_]to[-_]end'],
        'lint': [r'lint', r'format', r'style', r'flake8', r'pylint', r'eslint', r'prettier'],
        'security': [r'security', r'scan', r'vulnerability', r'cve', r'snyk', r'trivy'],
        'coverage': [r'coverage', r'codecov', r'cov[-_]'],
        'performance': [r'perf', r'benchmark', r'stress']
    }
    
    # Error patterns for root cause detection
    ERROR_PATTERNS = {
        'memory': [
            r'out of memory', r'OOM', r'memory allocation failed',
            r'hipMalloc failed', r'cuda out of memory'
        ],
        'timeout': [
            r'timeout', r'timed out', r'deadline exceeded',
            r'operation timed out'
        ],
        'gpu': [
            r'no gpu', r'gpu not found', r'hip error', r'cuda error',
            r'device not available', r'rocm error'
        ],
        'dependency': [
            r'module not found', r'import error', r'cannot find package',
            r'dependency.*failed', r'requirements.*failed'
        ],
        'compilation': [
            r'compilation failed', r'build error', r'syntax error',
            r'undefined reference', r'linker error'
        ],
        'assertion': [
            r'assertion.*failed', r'assert', r'expected.*got',
            r'test.*failed'
        ],
        'connection': [
            r'connection.*refused', r'network.*error', r'unable to connect',
            r'connection.*timeout'
        ],
        'permission': [
            r'permission denied', r'access denied', r'forbidden',
            r'authentication failed'
        ]
    }

    def __init__(self, github_service):
        """
        Initialize CI Analyzer
        
        Args:
            github_service: GitHubService instance for API calls
        """
        self.github = github_service

    def analyze_pr_ci(
        self,
        pr_number: int,
        include_history: bool = True,
        history_limit: int = 10
    ) -> Dict[str, Any]:
        """
        Perform comprehensive CI analysis for a PR
        
        Args:
            pr_number: Pull request number
            include_history: Whether to include historical comparison
            history_limit: Number of recent runs to analyze for trends
            
        Returns:
            Comprehensive CI analysis results
        """
        logger.info(f"Analyzing CI for PR #{pr_number}")
        
        try:
            # Fetch PR details
            pr = self.github.get_pull_request(pr_number)
            
            # Get CI check runs for the PR head commit
            check_runs = self._get_check_runs(pr)
            
            # Analyze overall CI state
            ci_state = self._analyze_ci_state(check_runs)
            
            # Categorize and analyze jobs
            job_analysis = self._analyze_jobs(check_runs)
            
            # Get failing job details
            failing_jobs = self._analyze_failing_jobs(check_runs)
            
            # Detect flaky tests in this PR
            flaky_tests = self._detect_flaky_tests(pr_number, check_runs)
            
            # Calculate CI duration
            ci_duration = self._calculate_ci_duration(check_runs)
            
            # Get historical comparison if requested
            history_comparison = None
            if include_history:
                history_comparison = self._compare_with_history(
                    pr, check_runs, history_limit
                )
            
            return {
                'pr_number': pr_number,
                'pr_title': pr.get('title', ''),
                'head_sha': pr.get('head', {}).get('sha', '')[:7],
                'ci_state': ci_state,
                'job_analysis': job_analysis,
                'failing_jobs': failing_jobs,
                'flaky_tests': flaky_tests,
                'ci_duration': ci_duration,
                'history_comparison': history_comparison,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing CI for PR #{pr_number}: {e}")
            raise

    def _get_check_runs(self, pr: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get check runs for a PR's head commit
        
        Args:
            pr: PR data dictionary
            
        Returns:
            List of check run results
        """
        try:
            # Get the head SHA
            head_sha = pr.get('head', {}).get('sha')
            if not head_sha:
                logger.warning("No head SHA found in PR data")
                return []
            
            # Fetch check runs from GitHub API
            check_runs = self.github.get_check_runs(head_sha)
            
            return check_runs
            
        except Exception as e:
            logger.error(f"Error fetching check runs: {e}")
            return []

    def _analyze_ci_state(self, check_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze overall CI state
        
        Returns:
            Overall CI state with counts
        """
        if not check_runs:
            return {
                'overall_status': 'unknown',
                'total_checks': 0,
                'passed': 0,
                'failed': 0,
                'pending': 0,
                'skipped': 0,
                'pass_rate': 0.0
            }
        
        status_counts = defaultdict(int)
        for run in check_runs:
            status = run.get('conclusion') or run.get('status', 'unknown')
            status_counts[status] += 1
        
        total = len(check_runs)
        passed = status_counts.get('success', 0)
        failed = (status_counts.get('failure', 0) + 
                 status_counts.get('timed_out', 0) +
                 status_counts.get('action_required', 0))
        pending = (status_counts.get('in_progress', 0) + 
                  status_counts.get('queued', 0) +
                  status_counts.get('waiting', 0))
        skipped = (status_counts.get('skipped', 0) + 
                  status_counts.get('cancelled', 0) +
                  status_counts.get('neutral', 0))
        
        # Determine overall status
        if failed > 0:
            overall_status = 'failure'
        elif pending > 0:
            overall_status = 'pending'
        elif total == passed:
            overall_status = 'success'
        else:
            overall_status = 'partial'
        
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        
        return {
            'overall_status': overall_status,
            'total_checks': total,
            'passed': passed,
            'failed': failed,
            'pending': pending,
            'skipped': skipped,
            'pass_rate': round(pass_rate, 1)
        }

    def _analyze_jobs(self, check_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Categorize jobs and analyze each category
        
        Returns:
            Job analysis by category
        """
        categorized_jobs = {
            'build': [],
            'unit_tests': [],
            'integration_tests': [],
            'lint': [],
            'security': [],
            'coverage': [],
            'performance': [],
            'other': []
        }
        
        for run in check_runs:
            name = run.get('name', '').lower()
            categorized = False
            
            # Try to categorize the job
            for category, patterns in self.JOB_CATEGORIES.items():
                if any(re.search(pattern, name, re.IGNORECASE) for pattern in patterns):
                    categorized_jobs[category].append({
                        'name': run.get('name', ''),
                        'status': run.get('conclusion') or run.get('status', 'unknown'),
                        'url': run.get('html_url', ''),
                        'duration_seconds': self._calculate_duration(run)
                    })
                    categorized = True
                    break
            
            if not categorized:
                categorized_jobs['other'].append({
                    'name': run.get('name', ''),
                    'status': run.get('conclusion') or run.get('status', 'unknown'),
                    'url': run.get('html_url', ''),
                    'duration_seconds': self._calculate_duration(run)
                })
        
        # Summarize each category
        category_summary = {}
        for category, jobs in categorized_jobs.items():
            if jobs:
                passed = sum(1 for j in jobs if j['status'] == 'success')
                failed = sum(1 for j in jobs if j['status'] in ['failure', 'timed_out'])
                pending = sum(1 for j in jobs if j['status'] in ['in_progress', 'queued'])
                
                category_summary[category] = {
                    'total': len(jobs),
                    'passed': passed,
                    'failed': failed,
                    'pending': pending,
                    'pass_rate': round((passed / len(jobs) * 100) if len(jobs) > 0 else 0, 1),
                    'jobs': jobs
                }
        
        return category_summary

    def _analyze_failing_jobs(self, check_runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze failing jobs to extract error information
        
        Returns:
            List of failing jobs with error details
        """
        failing_jobs = []
        
        for run in check_runs:
            status = run.get('conclusion') or run.get('status')
            if status not in ['failure', 'timed_out', 'action_required']:
                continue
            
            # Extract error information
            job_name = run.get('name', 'Unknown Job')
            output = run.get('output', {})
            
            # Get error summary
            error_title = output.get('title', '')
            error_summary = output.get('summary', '')
            error_text = output.get('text', '')
            
            # Detect root cause from error messages
            root_cause = self._detect_root_cause(
                f"{error_title} {error_summary} {error_text}"
            )
            
            # Get first error line
            first_error = self._extract_first_error(error_text)
            
            failing_jobs.append({
                'name': job_name,
                'status': status,
                'url': run.get('html_url', ''),
                'logs_url': run.get('logs_url', run.get('html_url', '')),
                'started_at': run.get('started_at', ''),
                'completed_at': run.get('completed_at', ''),
                'duration_seconds': self._calculate_duration(run),
                'error_summary': error_title or error_summary[:200] if error_summary else 'No error message',
                'first_error': first_error,
                'root_cause_hint': root_cause,
                'annotations': output.get('annotations_count', 0)
            })
        
        return failing_jobs

    def _detect_root_cause(self, error_text: str) -> str:
        """
        Detect root cause category from error text
        
        Args:
            error_text: Error message text
            
        Returns:
            Root cause category
        """
        error_text_lower = error_text.lower()
        
        for cause, patterns in self.ERROR_PATTERNS.items():
            if any(re.search(pattern, error_text_lower, re.IGNORECASE) 
                   for pattern in patterns):
                return cause
        
        return 'unknown'

    def _extract_first_error(self, error_text: str) -> str:
        """
        Extract the first error line from error text
        
        Args:
            error_text: Full error text
            
        Returns:
            First error line (truncated)
        """
        if not error_text:
            return ''
        
        # Split into lines and find first line with error keywords
        lines = error_text.split('\n')
        error_keywords = ['error:', 'failed:', 'exception:', 'fatal:', 'traceback']
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in error_keywords):
                return line.strip()[:200]
        
        # If no error keyword found, return first non-empty line
        for line in lines:
            if line.strip():
                return line.strip()[:200]
        
        return error_text[:200]

    def _calculate_duration(self, run: Dict[str, Any]) -> Optional[int]:
        """
        Calculate duration of a job run in seconds
        
        Args:
            run: Check run data
            
        Returns:
            Duration in seconds or None
        """
        try:
            started = run.get('started_at')
            completed = run.get('completed_at')
            
            if not started or not completed:
                return None
            
            start_dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
            complete_dt = datetime.fromisoformat(completed.replace('Z', '+00:00'))
            
            duration = (complete_dt - start_dt).total_seconds()
            return int(duration)
            
        except Exception as e:
            logger.debug(f"Could not calculate duration: {e}")
            return None

    def _detect_flaky_tests(
        self,
        pr_number: int,
        check_runs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect flaky tests by looking for multiple runs of the same test
        
        Returns:
            List of potentially flaky tests
        """
        # Group runs by job name
        job_runs = defaultdict(list)
        
        for run in check_runs:
            job_name = run.get('name', '')
            status = run.get('conclusion') or run.get('status')
            job_runs[job_name].append({
                'status': status,
                'run_id': run.get('id'),
                'attempt': run.get('run_attempt', 1),
                'completed_at': run.get('completed_at', '')
            })
        
        flaky_tests = []
        
        # Find jobs that have both pass and fail status
        for job_name, runs in job_runs.items():
            if len(runs) < 2:
                continue
            
            statuses = [r['status'] for r in runs]
            has_success = 'success' in statuses
            has_failure = any(s in ['failure', 'timed_out'] for s in statuses)
            
            if has_success and has_failure:
                # This is potentially flaky
                failure_count = sum(1 for s in statuses if s in ['failure', 'timed_out'])
                total_runs = len(runs)
                
                flaky_tests.append({
                    'test_name': job_name,
                    'total_runs': total_runs,
                    'failures': failure_count,
                    'success': total_runs - failure_count,
                    'failure_rate': round((failure_count / total_runs * 100), 1),
                    'flaky_score': round((failure_count / total_runs), 2),
                    'runs': sorted(runs, key=lambda x: x['completed_at'], reverse=True)[:5]
                })
        
        return sorted(flaky_tests, key=lambda x: x['flaky_score'], reverse=True)

    def _calculate_ci_duration(self, check_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate total CI duration metrics
        
        Returns:
            CI duration statistics
        """
        if not check_runs:
            return {
                'total_duration_seconds': 0,
                'total_duration_minutes': 0,
                'longest_job': None,
                'shortest_job': None,
                'average_job_duration': 0
            }
        
        durations = []
        job_durations = []
        
        for run in check_runs:
            duration = self._calculate_duration(run)
            if duration is not None and duration > 0:
                durations.append(duration)
                job_durations.append({
                    'name': run.get('name', ''),
                    'duration': duration
                })
        
        if not durations:
            return {
                'total_duration_seconds': 0,
                'total_duration_minutes': 0,
                'longest_job': None,
                'shortest_job': None,
                'average_job_duration': 0
            }
        
        # Total is the longest duration (parallel execution)
        total_duration = max(durations)
        
        longest_job = max(job_durations, key=lambda x: x['duration'])
        shortest_job = min(job_durations, key=lambda x: x['duration'])
        avg_duration = sum(durations) / len(durations)
        
        return {
            'total_duration_seconds': total_duration,
            'total_duration_minutes': round(total_duration / 60, 1),
            'longest_job': {
                'name': longest_job['name'],
                'duration_seconds': longest_job['duration'],
                'duration_minutes': round(longest_job['duration'] / 60, 1)
            },
            'shortest_job': {
                'name': shortest_job['name'],
                'duration_seconds': shortest_job['duration'],
                'duration_minutes': round(shortest_job['duration'] / 60, 1)
            },
            'average_job_duration_seconds': int(avg_duration),
            'average_job_duration_minutes': round(avg_duration / 60, 1)
        }

    def _compare_with_history(
        self,
        pr: Dict[str, Any],
        current_runs: List[Dict[str, Any]],
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Compare current CI run with historical runs
        
        Returns:
            Historical comparison data
        """
        try:
            # Get recent commits to the base branch
            base_branch = pr.get('base', {}).get('ref', 'main')
            
            # Get last successful run on base branch
            # This would require additional GitHub API calls
            # For now, return a placeholder structure
            
            # TODO: Implement actual historical comparison
            # This would involve:
            # 1. Fetching recent workflow runs on base branch
            # 2. Finding last successful run
            # 3. Comparing job statuses
            # 4. Detecting newly failing tests
            
            return {
                'last_successful_run': None,
                'newly_failing_jobs': [],
                'fixed_jobs': [],
                'consistent_failures': [],
                'note': 'Historical comparison requires workflow run API access'
            }
            
        except Exception as e:
            logger.error(f"Error comparing with history: {e}")
            return {}

    def get_linked_issues(self, pr: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract linked issues from PR body
        
        Args:
            pr: PR data
            
        Returns:
            List of linked issues
        """
        body = pr.get('body', '')
        if not body:
            return []
        
        # Find issue references like #123, fixes #456, closes #789
        issue_patterns = [
            r'(?:fixes|closes|resolves|addresses)\s+#(\d+)',
            r'(?:fix|close|resolve)\s+#(\d+)',
            r'#(\d+)',
        ]
        
        linked_issues = set()
        for pattern in issue_patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            linked_issues.update(matches)
        
        issues_list = []
        for issue_num in linked_issues:
            try:
                issue = self.github.get_issue_by_number(int(issue_num))
                issues_list.append({
                    'number': issue_num,
                    'title': issue.get('title', ''),
                    'url': issue.get('url', ''),
                    'state': issue.get('state', 'unknown')
                })
            except Exception as e:
                logger.warning(f"Could not fetch issue #{issue_num}: {e}")
                issues_list.append({
                    'number': issue_num,
                    'title': f"Issue #{issue_num}",
                    'url': f"https://github.com/ROCm/TheRock/issues/{issue_num}",
                    'state': 'unknown'
                })
        
        return issues_list

    def analyze_code_quality_risks(
        self,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze code quality and risk factors
        
        Args:
            files: Changed files from PR
            
        Returns:
            Risk analysis
        """
        risks = {
            'touches_critical_paths': [],
            'changes_infrastructure': [],
            'modifies_secrets': [],
            'changes_permissions': [],
            'config_changes': [],
            'new_dependencies': [],
            'complexity_increase': False,
            'large_files_changed': []
        }
        
        # Critical path patterns
        critical_patterns = [
            r'/core/', r'/kernel/', r'/runtime/', r'/driver/',
            r'/memory/', r'/scheduler/', r'/allocator/'
        ]
        
        # Infrastructure patterns
        infra_patterns = [
            r'Dockerfile', r'\.ya?ml$', r'\.github/',
            r'CMakeLists\.txt', r'\.cmake', r'setup\.py',
            r'requirements\.txt', r'package\.json'
        ]
        
        # Secrets/security patterns
        secret_patterns = [
            r'secret', r'password', r'token', r'api[-_]?key',
            r'credential', r'auth', r'\.pem$', r'\.key$'
        ]
        
        # Permission patterns
        permission_patterns = [
            r'chmod', r'permission', r'access.*control',
            r'security', r'auth'
        ]
        
        total_complexity = 0
        
        for file in files:
            filename = file.get('filename', '')
            additions = file.get('additions', 0)
            deletions = file.get('deletions', 0)
            changes = additions + deletions
            patch = file.get('patch', '')
            
            # Check critical paths
            if any(re.search(p, filename, re.IGNORECASE) for p in critical_patterns):
                risks['touches_critical_paths'].append(filename)
            
            # Check infrastructure changes
            if any(re.search(p, filename, re.IGNORECASE) for p in infra_patterns):
                risks['changes_infrastructure'].append(filename)
            
            # Check for secrets/credentials
            if any(re.search(p, filename + patch, re.IGNORECASE) for p in secret_patterns):
                risks['modifies_secrets'].append(filename)
            
            # Check permissions
            if any(re.search(p, patch, re.IGNORECASE) for p in permission_patterns):
                risks['changes_permissions'].append(filename)
            
            # Check for config changes
            if re.search(r'\.(json|ya?ml|toml|ini|conf|config)$', filename, re.IGNORECASE):
                risks['config_changes'].append(filename)
            
            # Check for new dependencies
            if re.search(r'(requirements\.txt|package\.json|Cargo\.toml|go\.mod)', filename):
                if re.search(r'^\+.*[a-zA-Z]', patch, re.MULTILINE):
                    risks['new_dependencies'].append(filename)
            
            # Large file changes (complexity indicator)
            if changes > 500:
                risks['large_files_changed'].append({
                    'filename': filename,
                    'changes': changes
                })
            
            total_complexity += changes
        
        risks['complexity_increase'] = total_complexity > 1000
        risks['total_lines_changed'] = total_complexity
        
        return risks



