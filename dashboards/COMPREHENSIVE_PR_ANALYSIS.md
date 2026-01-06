# Comprehensive PR Analysis Feature - Documentation

## Overview

This document describes the **Comprehensive PR Analysis** feature that provides detailed insights into Pull Requests including CI/CD status, test results, code quality analysis, and risk assessment.

## Features Implemented

### 1. **Linked Issues** 📋
- Automatically extracts and displays issues linked in the PR description
- Supports patterns like `fixes #123`, `closes #456`, `#789`
- Shows issue titles, states, and provides direct links

### 2. **Overall CI State** ✅❌
Displays comprehensive CI/CD status including:
- **Overall Status**: success, failure, pending, or partial
- **Pass Rate**: Percentage of checks that passed
- **Check Breakdown**: 
  - ✓ Passed checks
  - ✗ Failed checks
  - ⏳ Pending checks
  - ⊘ Skipped checks

### 3. **CI Job Analysis by Category** 🔨
Jobs are automatically categorized and analyzed:

| Category | Icon | Description |
|----------|------|-------------|
| **Build** | 🔨 | Compilation and build jobs |
| **Unit Tests** | 🧪 | Unit test suites |
| **Integration Tests** | 🔗 | Integration and E2E tests |
| **Lint/Format** | 📝 | Code style, linting, formatting |
| **Security Scan** | 🔒 | Security vulnerabilities, CVE scans |
| **Code Coverage** | 📊 | Test coverage reports |
| **Performance** | ⚡ | Benchmarks and performance tests |

Each category shows:
- Total jobs in category
- Pass/fail counts
- Pass rate percentage
- Individual job status with links

### 4. **Failing Job Details** ❌
For each failing job, provides:
- **Job Name**: Full name of the failing job
- **Status**: failure, timed_out, action_required
- **Duration**: Time taken to run (in minutes)
- **Error Summary**: High-level error description
- **First Error**: First error line from logs
- **Root Cause Hint**: Automatically detected error category:
  - `memory`: OOM, allocation failures
  - `timeout`: Timeouts and deadlines
  - `gpu`: GPU/HIP/CUDA errors
  - `dependency`: Missing packages/imports
  - `compilation`: Build/syntax errors
  - `assertion`: Test failures
  - `connection`: Network errors
  - `permission`: Access/auth errors
- **Link to Logs**: Direct link to full CI logs

### 5. **Flaky Test Detection** ⚠️
Identifies tests with inconsistent pass/fail patterns:
- **Test Name**: Name of the flaky test
- **Total Runs**: Number of times test ran
- **Failures**: Number of failed runs
- **Success**: Number of successful runs
- **Failure Rate**: Percentage of runs that failed
- **Flaky Score**: 0.0-1.0 score indicating flakiness
- **Recent Runs**: History of recent pass/fail pattern

Example: "Failed 3/10 recent runs" → Flaky Score: 0.30

### 6. **Review Status** 👥
Displays PR review metrics:
- Total number of reviews
- ✓ Approved count
- ⚠ Changes requested count
- 💬 Commented count
- Latest review details with timestamps

### 7. **Code Quality & Risk Analysis** 🔍
Comprehensive risk assessment:

#### **Critical Risks** 🚨
- **Touches Critical Paths**: Changes to core runtime, kernels, memory management
- **Modifies Secrets**: Changes to credentials, API keys, certificates
- **Changes Permissions**: Modifications to access control

#### **High Risks** ⚠️
- **Changes Infrastructure**: Dockerfile, CI/CD configs, build system
- **Changes Permissions**: Security and authentication code

#### **Medium Risks** 📝
- **Config Changes**: JSON, YAML, TOML configuration files
- **New Dependencies**: Added packages in requirements.txt, package.json

#### **Code Complexity**
- **Total Lines Changed**: Overall PR size
- **Complexity Increase**: Flagged if >1000 lines changed
- **Large Files Changed**: Individual files with >500 line changes

### 8. **Key Files Modified** 📁
Categorized file breakdown:
- **Source Files**: .cpp, .c, .py, .hip, .cu, .h files
- **Test Files**: Files containing "test" in name
- **Config Files**: Configuration and settings
- **Infrastructure Files**: Build and deployment files
- **Total Files**: Overall count

### 9. **New Dependencies Added** 📦
Lists any new dependencies introduced:
- Detected from requirements.txt, package.json, Cargo.toml, go.mod
- Shows which files contain new dependencies

### 10. **Config or Environment Changes** ⚙️
Tracks changes to:
- Configuration files (.json, .yaml, .toml, .ini)
- Environment settings
- Build configurations

### 11. **PR Timeline Metrics** 📅
Detailed timing information:
- **Opened At**: When PR was created
- **Time Since Opened**: Hours since creation
- **Last Commit At**: Timestamp of most recent commit
- **Time Since Last Commit**: Hours since last commit
- **Last Review At**: When last review was submitted
- **Time Since Last Review**: Hours since last review
- **Total Commits**: Number of commits in PR
- **Total Reviews**: Number of review submissions

### 12. **CI Duration** ⏱️
Performance metrics:
- **Total Duration**: Overall CI run time (longest job duration)
- **Total Duration (Minutes)**: Formatted for readability
- **Longest Job**: Name and duration of slowest job
- **Shortest Job**: Name and duration of fastest job
- **Average Job Duration**: Mean time across all jobs

### 13. **Historical Comparison** 📊
Compares current run with history:
- Last successful run on base branch
- Newly failing jobs (passed before, failing now)
- Fixed jobs (failed before, passing now)
- Consistent failures (repeatedly failing)
- Regression detection

## API Endpoints

### Main Endpoint

```http
GET /api/prs/{pr_number}/comprehensive
```

Returns comprehensive PR analysis including all features above.

**Example Request:**
```bash
curl http://localhost:8000/api/prs/123/comprehensive
```

**Example Response:**
```json
{
  "pr_number": 123,
  "pr_title": "Add GPU memory optimization",
  "pr_author": "developer123",
  "pr_state": "open",
  "pr_url": "https://github.com/ROCm/TheRock/pull/123",
  
  "linked_issues": [
    {
      "number": "100",
      "title": "GPU memory leak in kernel",
      "url": "https://github.com/ROCm/TheRock/issues/100",
      "state": "open"
    }
  ],
  
  "ci_state": {
    "overall_status": "failure",
    "total_checks": 15,
    "passed": 12,
    "failed": 2,
    "pending": 1,
    "skipped": 0,
    "pass_rate": 80.0
  },
  
  "job_analysis": {
    "build": {
      "total": 3,
      "passed": 3,
      "failed": 0,
      "pending": 0,
      "pass_rate": 100.0,
      "jobs": [...]
    },
    "unit_tests": {
      "total": 5,
      "passed": 4,
      "failed": 1,
      "pending": 0,
      "pass_rate": 80.0,
      "jobs": [...]
    }
  },
  
  "failing_jobs": [
    {
      "name": "test-unit-gfx94x",
      "status": "failure",
      "url": "https://github.com/ROCm/TheRock/runs/...",
      "logs_url": "https://github.com/ROCm/TheRock/runs/.../logs",
      "duration_seconds": 180,
      "error_summary": "AssertionError: Memory allocation failed",
      "first_error": "test_memory.py:45: AssertionError: Expected 1024MB, got 512MB",
      "root_cause_hint": "memory"
    }
  ],
  
  "flaky_tests": [
    {
      "test_name": "test-integration-multi-gpu",
      "total_runs": 10,
      "failures": 3,
      "success": 7,
      "failure_rate": 30.0,
      "flaky_score": 0.30,
      "runs": [...]
    }
  ],
  
  "review_status": {
    "total_reviews": 3,
    "approved_count": 1,
    "changes_requested_count": 1,
    "commented_count": 1
  },
  
  "code_quality_risks": {
    "touches_critical_paths": ["runtime/memory/allocator.cpp"],
    "changes_infrastructure": [],
    "modifies_secrets": [],
    "changes_permissions": [],
    "config_changes": ["rocm_config.yaml"],
    "new_dependencies": [],
    "complexity_increase": false,
    "large_files_changed": [],
    "total_lines_changed": 245
  },
  
  "key_files": {
    "source_files": [...],
    "test_files": [...],
    "config_files": [...],
    "infrastructure": [...],
    "total_files": 8
  },
  
  "time_metrics": {
    "opened_at": "2026-01-05T10:00:00Z",
    "updated_at": "2026-01-05T14:30:00Z",
    "last_commit_at": "2026-01-05T14:00:00Z",
    "last_review_at": "2026-01-05T12:00:00Z",
    "hours_since_opened": 24.5,
    "hours_since_last_commit": 0.5,
    "hours_since_last_review": 2.5,
    "total_commits": 5,
    "total_reviews": 3
  },
  
  "ci_duration": {
    "total_duration_seconds": 600,
    "total_duration_minutes": 10.0,
    "longest_job": {
      "name": "test-integration-gfx110x",
      "duration_seconds": 600,
      "duration_minutes": 10.0
    },
    "shortest_job": {
      "name": "lint-python",
      "duration_seconds": 45,
      "duration_minutes": 0.8
    },
    "average_job_duration_seconds": 180,
    "average_job_duration_minutes": 3.0
  },
  
  "analyzed_at": "2026-01-05T15:00:00Z"
}
```

## Frontend UI

### Access
Navigate to: `http://localhost:3000/prs.html`

### Using the Feature
1. **View PR List**: Browse open PRs
2. **Click "📊 Comprehensive Analysis"** button on any PR
3. **View Results**: Opens in new tab with tabbed interface

### UI Sections

#### **CI/CD Status Overview**
- Visual status badge (green/red/yellow)
- Progress bar showing pass rate
- Metric cards for passed/failed/pending/skipped

#### **Tabs**
1. **CI Details**: Job breakdown by category
2. **Failing Jobs**: Detailed failure analysis
3. **Flaky Tests**: Flaky test detection results
4. **Code Quality**: Risk analysis and warnings
5. **Timeline**: PR timeline and metrics

#### **Side Cards**
- **Linked Issues**: Clickable issue links
- **Review Status**: Review metrics
- **Key Files**: File categorization summary

## Technical Implementation

### Backend Services

#### **CIAnalyzer** (`services/ci_analyzer.py`)
Main service class for CI analysis:
- `analyze_pr_ci()`: Main analysis method
- `_get_check_runs()`: Fetches CI check runs
- `_analyze_ci_state()`: Calculates overall state
- `_analyze_jobs()`: Categorizes jobs
- `_analyze_failing_jobs()`: Extracts failure details
- `_detect_flaky_tests()`: Finds flaky tests
- `_detect_root_cause()`: Determines error categories
- `analyze_code_quality_risks()`: Risk assessment
- `get_linked_issues()`: Extracts issue references

#### **GitHubService** Extensions
New methods added:
- `get_check_runs(commit_sha)`: Fetch CI check runs
- `get_workflow_runs()`: Get workflow run history
- `get_pr_time_metrics()`: Calculate timeline metrics

### Pattern Matching

#### **Job Categories**
```python
JOB_CATEGORIES = {
    'build': [r'build', r'compile', r'package'],
    'unit_tests': [r'unit[-_]?test', r'unittest'],
    'integration_tests': [r'integration[-_]?test', r'e2e'],
    'lint': [r'lint', r'format', r'style'],
    'security': [r'security', r'scan', r'vulnerability'],
    'coverage': [r'coverage', r'codecov'],
    'performance': [r'perf', r'benchmark']
}
```

#### **Error Patterns**
```python
ERROR_PATTERNS = {
    'memory': [r'out of memory', r'OOM', r'hipMalloc failed'],
    'timeout': [r'timeout', r'timed out'],
    'gpu': [r'hip error', r'cuda error', r'device not available'],
    'dependency': [r'module not found', r'import error'],
    'compilation': [r'compilation failed', r'syntax error'],
    'assertion': [r'assertion.*failed', r'test.*failed'],
    'connection': [r'connection.*refused', r'network.*error'],
    'permission': [r'permission denied', r'access denied']
}
```

## Usage Examples

### Example 1: Check PR CI Status
```bash
curl http://localhost:8000/api/prs/456/comprehensive | jq '.ci_state'
```

### Example 2: Find Failing Jobs
```bash
curl http://localhost:8000/api/prs/456/comprehensive | jq '.failing_jobs[]'
```

### Example 3: Detect Flaky Tests
```bash
curl http://localhost:8000/api/prs/456/comprehensive | jq '.flaky_tests[] | select(.flaky_score > 0.3)'
```

### Example 4: Check Code Risks
```bash
curl http://localhost:8000/api/prs/456/comprehensive | jq '.code_quality_risks'
```

## Benefits

1. **Quick CI Status**: Immediately see which tests pass/fail
2. **Root Cause Analysis**: Auto-detect error categories
3. **Flaky Test Identification**: Find unreliable tests
4. **Risk Assessment**: Identify high-risk changes
5. **Time Tracking**: Monitor PR age and review times
6. **Linked Context**: See related issues
7. **Performance Monitoring**: Track CI duration trends

## Future Enhancements

- [ ] Historical comparison with base branch
- [ ] Test coverage diff visualization
- [ ] AI-powered fix suggestions for failing tests
- [ ] Integration with flaky test database
- [ ] Automatic labeling based on risks
- [ ] Slack/email notifications for failures
- [ ] CI cost tracking and optimization
- [ ] Code duplication detection
- [ ] Security vulnerability scanning integration

## Troubleshooting

### Issue: No check runs found
**Solution**: Ensure PR has run CI workflows. Check that `GITHUB_TOKEN` has proper permissions.

### Issue: Empty flaky tests
**Solution**: Flaky tests require multiple runs. Re-run failed jobs to collect data.

### Issue: Missing linked issues
**Solution**: Ensure PR description uses keywords like "fixes #123" or "closes #456".

### Issue: Timeout errors
**Solution**: Increase API timeout limits in `github_service.py` rate limit handler.

## Related Documentation

- [PR Analysis Features](PR_ANALYSIS_FEATURES.md)
- [GitHub Service API](backend/services/github_service.py)
- [CI Analyzer Implementation](backend/services/ci_analyzer.py)



