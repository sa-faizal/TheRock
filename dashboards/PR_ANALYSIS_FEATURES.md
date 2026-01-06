# PR Analysis Features - Documentation

This document describes the three new PR analysis features added to the ROCm Sentinel Dashboard.

## Features Overview

### 1. PR Quality Analysis
Analyzes PR diffs to detect quality issues and provide actionable feedback.

### 2. Flaky Test Detection
Tracks test pass/fail patterns across runs to identify and fix flaky tests.

### 3. PR Review Suggestions
Generates intelligent review recommendations including test suggestions and reviewer assignments.

---

## Feature 1: PR Quality Analysis

### What It Does

Analyzes pull request code changes to detect:
- ✅ **Missing tests for new code** - Identifies files with new code but no corresponding tests
- ✅ **Test-only PRs** - Flags PRs that only modify test files without code changes
- ✅ **Flaky test modifications** - Detects changes to known flaky tests
- ✅ **High-risk changes** - Identifies GPU kernel code, distributed training logic, memory management
- ✅ **File failure history** - Checks if PR touches files with history of CI failures
- ✅ **Test case suggestions** - AI-powered suggestions for specific tests based on code changes

### API Endpoint

```http
POST /api/prs/{pr_number}/analyze
```

**Parameters:**
- `pr_number` (path): PR number to analyze
- `include_test_analysis` (query, optional): Include flaky test analysis (default: true)
- `include_review_suggestions` (query, optional): Include review suggestions (default: true)

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/prs/123/analyze?include_test_analysis=true&include_review_suggestions=true"
```

**Example Response:**
```json
{
  "pr": {
    "number": 123,
    "title": "Add new GPU kernel optimization",
    "state": "open",
    "author": "developer1"
  },
  "analysis": {
    "pr_number": 123,
    "pr_title": "Add new GPU kernel optimization",
    "quality_score": {
      "score": 75,
      "grade": "B",
      "color": "yellow",
      "issues": [
        "Missing tests for 50 lines of new code (-15)",
        "Contains 1 high-risk change(s) (-20)"
      ],
      "recommendation": "APPROVE with minor comments - Good PR, minor improvements suggested"
    },
    "missing_tests": true,
    "new_code_lines": 150,
    "new_test_lines": 30,
    "test_coverage_ratio": 0.2,
    "untested_files": ["src/kernels/optimization.hip"],
    "is_test_only_pr": false,
    "has_high_risk_changes": true,
    "high_risk_changes": [
      {
        "filename": "src/kernels/optimization.hip",
        "risk_types": ["gpu_kernel", "memory_management"],
        "additions": 100,
        "deletions": 20
      }
    ],
    "test_suggestions": [
      "Add GPU kernel correctness tests with various input sizes",
      "Test memory allocation and deallocation patterns",
      "Add multi-GPU synchronization tests",
      "Test edge cases: zero-sized inputs, very large inputs",
      "Add performance regression tests"
    ],
    "review_comments": [
      {
        "type": "missing_tests",
        "severity": "high",
        "title": "Missing Tests for New Code",
        "message": "You added 150 lines of code but only 30 lines of tests. Please add tests for: src/kernels/optimization.hip",
        "files": ["src/kernels/optimization.hip"]
      },
      {
        "type": "high_risk",
        "severity": "critical",
        "title": "High-Risk Change: src/kernels/optimization.hip",
        "message": "This file contains high-risk code (gpu_kernel, memory_management). Ensure thorough testing including: GPU memory validation, multi-GPU scenarios, and stress testing.",
        "files": ["src/kernels/optimization.hip"]
      }
    ]
  },
  "review_suggestion": {
    "should_approve": false,
    "should_request_changes": true,
    "blocking_issues": [
      "Missing Tests for New Code: You added 150 lines of code but only 30 lines of tests"
    ],
    "suggested_reviewers": [
      {
        "name": "john_doe",
        "expertise_score": 0.45,
        "commits": 15,
        "reason": "Has 15 commits touching 3 of the modified files"
      }
    ],
    "risk_level": "high",
    "risk_factors": [
      "1 high-risk file changes (GPU kernels, distributed training)",
      "Missing tests for new code"
    ]
  }
}
```

### Quality Score Calculation

The quality score starts at 100 and deductions are made for:
- Missing tests: -30 points (max, scales with lines of code)
- Test-only PR: -10 points
- Flaky test modifications: -15 points
- High-risk changes: -20 points
- Files with failure history: -10 points

**Grades:**
- A (90-100): Excellent, ready to merge
- B (75-89): Good, minor improvements suggested
- C (60-74): Needs attention before merge
- D (0-59): Major issues, requires rework

---

## Feature 2: Flaky Test Detection

### What It Does

Tracks test execution results across multiple runs to identify flaky tests:
- 📊 **Pass/fail patterns** - Analyzes test results on identical commits
- 📈 **Flakiness score** - Calculates percentage of runs with inconsistent results (0.0-1.0)
- 🆕 **Newly flaky tests** - Identifies tests that became flaky in a PR
- 🔧 **Fix suggestions** - Recommends specific fixes:
  - Add retries with exponential backoff
  - Increase timeouts
  - Fix race conditions (add synchronization)
  - Improve test isolation

### API Endpoints

#### Get Flaky Tests
```http
GET /api/flaky-tests?min_score=0.1&limit=50
```

**Parameters:**
- `min_score` (query, optional): Minimum flakiness score (default: 0.1)
- `limit` (query, optional): Maximum results (default: 50)

**Example Response:**
```json
{
  "flaky_tests": [
    {
      "test_name": "test_distributed_training_sync",
      "flakiness_score": 0.45,
      "failure_rate": 0.35,
      "total_runs": 100,
      "passed_runs": 65,
      "failed_runs": 35,
      "flaky_commits": 15,
      "total_commits": 30,
      "avg_duration_ms": 2500.5,
      "common_errors": {
        "timeout": 15,
        "race_condition": 10,
        "cuda_error": 5
      },
      "suggested_fixes": [
        "Add synchronization primitives (barriers, locks) to eliminate race conditions",
        "Use hipDeviceSynchronize() or hipStreamSynchronize() after kernel launches",
        "Increase test timeout - test may need more time on slower hardware",
        "Consider marking as @pytest.mark.flaky with max_runs=3"
      ],
      "severity": "high"
    }
  ],
  "total_count": 1,
  "statistics": {
    "total_tests_tracked": 500,
    "flaky_tests_count": 25,
    "flaky_percentage": 5.0,
    "severity_breakdown": {
      "critical": 3,
      "high": 8,
      "medium": 10,
      "low": 4
    }
  }
}
```

#### Record Test Result
```http
POST /api/flaky-tests/record
```

**Request Body:**
```json
{
  "test_name": "test_gpu_memory_allocation",
  "status": "passed",
  "commit_sha": "abc123def456",
  "run_id": "ci-run-12345",
  "duration_ms": 150.5,
  "error_message": null
}
```

#### Get Test History
```http
GET /api/flaky-tests/{test_name}/history?limit=50
```

### Flakiness Score Calculation

```
flakiness_score = flaky_commits / total_commits
```

Where:
- **flaky_commits**: Number of commits where test had inconsistent results (both pass and fail)
- **total_commits**: Total number of commits where test was run multiple times

**Severity Levels:**
- Critical: ≥0.5 (fails 50%+ of the time on same commit)
- High: 0.3-0.49
- Medium: 0.1-0.29
- Low: <0.1

---

## Feature 3: PR Review Suggestions

### What It Does

Generates comprehensive review recommendations:
- 📝 **Test recommendations** - Required and suggested test cases
- 🔍 **Issue flagging** - "This file has failed CI 5 times in last 30 days"
- 👥 **Reviewer suggestions** - Based on git blame + historical fixes
- 💬 **Dashboard comments** - Generates formatted review comments (dashboard only, not posted to GitHub)

### API Endpoint

Review suggestions are included automatically when you call:
```http
POST /api/prs/{pr_number}/analyze?include_review_suggestions=true
```

### Response Structure

```json
{
  "review_suggestion": {
    "pr_number": 123,
    "pr_title": "Add new feature",
    "overall_assessment": "This PR introduces a new GPU optimization feature with 150 lines of code. The implementation looks solid, but test coverage is insufficient for high-risk GPU kernel changes. Recommend adding comprehensive tests before merge.",
    "should_approve": false,
    "should_request_changes": true,
    "blocking_issues": [
      "Missing Tests for New Code: You added 150 lines of code but only 30 lines of tests",
      "High-Risk Change: src/kernels/optimization.hip: This file contains high-risk code (gpu_kernel, memory_management)"
    ],
    "non_blocking_issues": [
      "File with Failure History: src/common/utils.cpp: This file has failed 3 times recently"
    ],
    "suggested_reviewers": [
      {
        "name": "john_doe",
        "expertise_score": 0.45,
        "commits": 15,
        "files_touched": 3,
        "reason": "Has 15 commits touching 3 of the modified files"
      },
      {
        "name": "jane_smith",
        "expertise_score": 0.32,
        "commits": 10,
        "files_touched": 2,
        "reason": "Has 10 commits touching 2 of the modified files"
      }
    ],
    "required_tests": [
      "Add unit tests for new code in src/kernels/optimization.hip",
      "Add GPU kernel validation tests for src/kernels/optimization.hip"
    ],
    "recommended_tests": [
      "Add GPU kernel correctness tests with various input sizes",
      "Test memory allocation and deallocation patterns",
      "Add multi-GPU synchronization tests"
    ],
    "risk_level": "high",
    "risk_factors": [
      "1 high-risk file changes (GPU kernels, distributed training)",
      "Missing tests for new code"
    ],
    "inline_comments": [
      {
        "file": "src/kernels/optimization.hip",
        "line": 1,
        "comment": "⚠️ **Missing Tests**: This file has significant new code but no corresponding test additions. Please add unit tests to cover the new functionality."
      }
    ],
    "summary_comment": "## 🤖 AI-Powered PR Analysis for #123\n\n### 🟡 Quality Score: 75/100 (Grade: B)\n**Recommendation**: APPROVE with minor comments - Good PR, minor improvements suggested\n\n### 📋 Overall Assessment\nThis PR introduces a new GPU optimization feature..."
  }
}
```

### Reviewer Suggestion Algorithm

1. **Analyze commit history** for files changed in PR
2. **Count contributions** by each author:
   - Number of commits touching affected files
   - Recency of contributions
3. **Calculate expertise score**: `commits / total_commits`
4. **Rank reviewers** by expertise score
5. **Return top 5** suggested reviewers

---

## Usage Examples

### Example 1: Analyze a PR

```bash
# Analyze PR #456
curl -X POST "http://localhost:8000/api/prs/456/analyze"
```

### Example 2: Get All Open PRs

```bash
# Get open PRs
curl "http://localhost:8000/api/prs?state=open&limit=20"
```

### Example 3: Track Flaky Tests

```python
import requests

# Record test results from CI
test_results = [
    {"test_name": "test_gpu_sync", "status": "passed", "commit_sha": "abc123", "run_id": "ci-1"},
    {"test_name": "test_gpu_sync", "status": "failed", "commit_sha": "abc123", "run_id": "ci-2"},
    {"test_name": "test_gpu_sync", "status": "passed", "commit_sha": "abc123", "run_id": "ci-3"},
]

for result in test_results:
    requests.post("http://localhost:8000/api/flaky-tests/record", json=result)

# Check if test is flaky
response = requests.get("http://localhost:8000/api/flaky-tests?min_score=0.1")
flaky_tests = response.json()["flaky_tests"]

for test in flaky_tests:
    print(f"{test['test_name']}: {test['flakiness_score']:.2%} flaky")
    print(f"Suggested fixes: {test['suggested_fixes']}")
```

### Example 4: Get PR with Files

```bash
# Get PR details with changed files
curl "http://localhost:8000/api/prs/456"
curl "http://localhost:8000/api/prs/456/files"
curl "http://localhost:8000/api/prs/456/commits"
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: PR Analysis

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - name: Analyze PR
        run: |
          curl -X POST "http://your-dashboard-url/api/prs/${{ github.event.pull_request.number }}/analyze" \
            -H "Content-Type: application/json"
      
      - name: Record Test Results
        if: always()
        run: |
          # Parse test results and record them
          python scripts/record_test_results.py
```

### Record Test Results Script

```python
#!/usr/bin/env python3
import json
import requests
import sys
from pathlib import Path

def record_test_results(junit_file, commit_sha, run_id):
    """Parse JUnit XML and record results"""
    import xml.etree.ElementTree as ET
    
    tree = ET.parse(junit_file)
    root = tree.getroot()
    
    for testcase in root.findall('.//testcase'):
        test_name = f"{testcase.get('classname')}.{testcase.get('name')}"
        duration_ms = float(testcase.get('time', 0)) * 1000
        
        # Determine status
        if testcase.find('failure') is not None:
            status = 'failed'
            error_message = testcase.find('failure').get('message', '')
        elif testcase.find('skipped') is not None:
            status = 'skipped'
            error_message = None
        else:
            status = 'passed'
            error_message = None
        
        # Record result
        payload = {
            'test_name': test_name,
            'status': status,
            'commit_sha': commit_sha,
            'run_id': run_id,
            'duration_ms': duration_ms,
            'error_message': error_message
        }
        
        response = requests.post(
            'http://dashboard-url/api/flaky-tests/record',
            json=payload
        )
        
        if response.status_code != 200:
            print(f"Failed to record {test_name}: {response.text}", file=sys.stderr)

if __name__ == '__main__':
    import os
    junit_file = sys.argv[1]
    commit_sha = os.environ.get('GITHUB_SHA')
    run_id = os.environ.get('GITHUB_RUN_ID')
    
    record_test_results(junit_file, commit_sha, run_id)
```

---

## Configuration

### Environment Variables

```bash
# Required
GITHUB_TOKEN=your_github_token
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional cache durations (seconds)
CACHE_OPEN_ISSUES=300
CACHE_CLOSED_ISSUES=3600
CACHE_COMMITS=1800
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Dashboard                       │
│                  (Display PR Analysis)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP REST API
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   FastAPI Backend                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │             API Endpoints (app.py)                 │    │
│  └─┬─────────────┬──────────────┬───────────────────┬─┘    │
│    │             │              │                   │       │
│  ┌─▼──────────┐ ┌▼────────────┐ ┌▼─────────────┐  ┌▼──────▼┐ │
│  │PRAnalyzer  │ │FlakyTest    │ │PRReview      │  │GitHub │ │
│  │            │ │Detector     │ │Generator     │  │Service│ │
│  │- Quality   │ │- Track runs │ │- AI review   │  │- API  │ │
│  │- Tests     │ │- Calc score │ │- Reviewers   │  │- Cache│ │
│  │- Risk      │ │- Suggest fix│ │- Comments    │  │       │ │
│  └────────────┘ └─────────────┘ └──────────────┘  └───────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────▼────┐
                    │ Claude  │
                    │   AI    │
                    └─────────┘
```

---

## Future Enhancements

1. **Automatic GitHub Comments** - Post analysis results directly to PRs
2. **Historical Trends** - Track quality scores over time
3. **Custom Rules** - Allow teams to define custom quality rules
4. **Integration Testing** - Detect missing integration tests
5. **Performance Impact** - Analyze potential performance regressions
6. **Security Scanning** - Detect potential security issues

---

## Support

For issues or questions, please refer to the main [README.md](README.md) or open an issue in the repository.



