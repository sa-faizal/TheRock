import os
from typing import List, Dict, Any, Optional
import anthropic
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PRAnalyzer:
    """
    PR Quality Analyzer - Analyzes PR diffs to detect quality issues:
    1. Missing tests for new code
    2. Changes to test files without corresponding code changes (test-only PRs)
    3. Modifications to flaky tests
    4. High-risk changes (GPU kernel code, distributed training logic)
    5. Check if PR touches files with history of failures
    6. Suggest specific test cases based on changed code
    """

    # High-risk patterns and file paths
    HIGH_RISK_PATTERNS = {
        'gpu_kernel': [
            r'\.hip$', r'\.cu$', r'\.cuh$', r'kernel', r'__global__', 
            r'hipLaunchKernelGGL', r'__device__', r'__host__'
        ],
        'distributed_training': [
            r'rccl', r'nccl', r'distributed', r'all_reduce', r'broadcast',
            r'multi_gpu', r'rank', r'world_size'
        ],
        'memory_management': [
            r'hipMalloc', r'hipFree', r'hipMemcpy', r'malloc', r'free',
            r'memory', r'allocat'
        ],
        'build_system': [
            r'CMakeLists\.txt', r'\.cmake', r'Makefile', r'build\.sh'
        ]
    }

    # Test file patterns
    TEST_FILE_PATTERNS = [
        r'/test/', r'/tests/', r'_test\.', r'test_', r'/gtest/',
        r'_unittest\.', r'unittest_'
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def analyze_pr(
        self,
        pr: Dict[str, Any],
        files: List[Dict[str, Any]],
        commit_history: Optional[List[Dict[str, Any]]] = None,
        flaky_tests: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive PR quality analysis
        
        Args:
            pr: PR metadata (number, title, body, etc.)
            files: List of changed files with diffs
            commit_history: Recent commit history for files touched
            flaky_tests: Known flaky test names/paths
            
        Returns:
            Analysis results with quality issues and suggestions
        """
        
        # Analyze file changes
        file_analysis = self._analyze_files(files)
        
        # Check for missing tests
        missing_tests = self._check_missing_tests(files, file_analysis)
        
        # Check for test-only PR
        is_test_only = self._is_test_only_pr(file_analysis)
        
        # Check for flaky test modifications
        flaky_test_changes = self._check_flaky_tests(files, flaky_tests or [])
        
        # Detect high-risk changes
        high_risk_changes = self._detect_high_risk_changes(files, file_analysis)
        
        # Check file failure history
        risky_files = self._check_failure_history(files, commit_history or [])
        
        # Get AI-powered test suggestions
        test_suggestions = self._suggest_test_cases(pr, files, file_analysis)
        
        # Generate overall quality score
        quality_score = self._calculate_quality_score(
            missing_tests, is_test_only, flaky_test_changes, 
            high_risk_changes, risky_files
        )
        
        return {
            'pr_number': pr['number'],
            'pr_title': pr['title'],
            'quality_score': quality_score,
            'file_analysis': file_analysis,
            'missing_tests': missing_tests,
            'is_test_only_pr': is_test_only,
            'flaky_test_changes': flaky_test_changes,
            'high_risk_changes': high_risk_changes,
            'risky_files': risky_files,
            'test_suggestions': test_suggestions,
            'review_comments': self._generate_review_comments(
                missing_tests, is_test_only, flaky_test_changes,
                high_risk_changes, risky_files, test_suggestions
            )
        }

    def _analyze_files(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze changed files to categorize them"""
        import re
        
        test_files = []
        code_files = []
        config_files = []
        doc_files = []
        
        total_additions = 0
        total_deletions = 0
        
        for file in files:
            filename = file.get('filename', '')
            additions = file.get('additions', 0)
            deletions = file.get('deletions', 0)
            patch = file.get('patch', '')
            
            total_additions += additions
            total_deletions += deletions
            
            # Categorize file
            is_test = any(re.search(pattern, filename, re.IGNORECASE) 
                         for pattern in self.TEST_FILE_PATTERNS)
            
            if is_test:
                test_files.append({
                    'filename': filename,
                    'additions': additions,
                    'deletions': deletions,
                    'patch': patch
                })
            elif filename.endswith(('.md', '.rst', '.txt')):
                doc_files.append(filename)
            elif filename.endswith(('.cmake', '.txt', '.yml', '.yaml', '.json', '.xml')):
                config_files.append(filename)
            else:
                code_files.append({
                    'filename': filename,
                    'additions': additions,
                    'deletions': deletions,
                    'patch': patch
                })
        
        return {
            'test_files': test_files,
            'code_files': code_files,
            'config_files': config_files,
            'doc_files': doc_files,
            'total_files': len(files),
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'has_tests': len(test_files) > 0,
            'has_code': len(code_files) > 0
        }

    def _check_missing_tests(
        self, 
        files: List[Dict[str, Any]], 
        file_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if new code is missing tests"""
        
        code_files = file_analysis['code_files']
        test_files = file_analysis['test_files']
        
        # Check if there's new code without tests
        has_new_code = any(f['additions'] > 10 for f in code_files)
        has_new_tests = any(f['additions'] > 5 for f in test_files)
        
        missing_tests = has_new_code and not has_new_tests
        
        # Calculate new code lines
        new_code_lines = sum(f['additions'] for f in code_files)
        new_test_lines = sum(f['additions'] for f in test_files)
        
        test_coverage_ratio = 0.0
        if new_code_lines > 0:
            test_coverage_ratio = new_test_lines / new_code_lines
        
        return {
            'missing_tests': missing_tests,
            'new_code_lines': new_code_lines,
            'new_test_lines': new_test_lines,
            'test_coverage_ratio': round(test_coverage_ratio, 2),
            'untested_files': [f['filename'] for f in code_files if f['additions'] > 10]
        }

    def _is_test_only_pr(self, file_analysis: Dict[str, Any]) -> bool:
        """Check if PR only modifies test files"""
        has_code = file_analysis['has_code']
        has_tests = file_analysis['has_tests']
        
        # Test-only PR: has test changes but no code changes
        return has_tests and not has_code

    def _check_flaky_tests(
        self, 
        files: List[Dict[str, Any]], 
        flaky_tests: List[str]
    ) -> List[Dict[str, Any]]:
        """Check if PR modifies known flaky tests"""
        
        flaky_changes = []
        
        for file in files:
            filename = file.get('filename', '')
            
            # Check if this file is a known flaky test
            for flaky_test in flaky_tests:
                if flaky_test in filename:
                    flaky_changes.append({
                        'filename': filename,
                        'flaky_test_name': flaky_test,
                        'additions': file.get('additions', 0),
                        'deletions': file.get('deletions', 0),
                        'warning': 'This file contains a known flaky test'
                    })
        
        return flaky_changes

    def _detect_high_risk_changes(
        self, 
        files: List[Dict[str, Any]], 
        file_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect high-risk changes (GPU kernels, distributed training, etc.)"""
        import re
        
        high_risk = []
        
        for file in files:
            filename = file.get('filename', '')
            patch = file.get('patch', '')
            
            risks = []
            
            # Check filename and patch content for high-risk patterns
            for risk_type, patterns in self.HIGH_RISK_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, filename, re.IGNORECASE) or \
                       re.search(pattern, patch, re.IGNORECASE):
                        risks.append(risk_type)
                        break
            
            if risks:
                high_risk.append({
                    'filename': filename,
                    'risk_types': list(set(risks)),
                    'additions': file.get('additions', 0),
                    'deletions': file.get('deletions', 0)
                })
        
        return high_risk

    def _check_failure_history(
        self, 
        files: List[Dict[str, Any]], 
        commit_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Check if PR touches files with history of failures"""
        
        # This would ideally use CI/CD failure logs
        # For now, we'll use commit message patterns as a proxy
        risky_files = []
        
        for file in files:
            filename = file.get('filename', '')
            
            # Count commits that touched this file and mentioned failures
            failure_mentions = 0
            recent_commits = []
            
            for commit in commit_history:
                if filename in commit.get('files_changed', []):
                    message = commit.get('message', '').lower()
                    if any(word in message for word in ['fix', 'bug', 'crash', 'fail', 'error']):
                        failure_mentions += 1
                        recent_commits.append({
                            'sha': commit.get('sha', '')[:7],
                            'message': commit.get('message', ''),
                            'date': commit.get('date')
                        })
            
            if failure_mentions > 2:  # File has history of failures
                risky_files.append({
                    'filename': filename,
                    'failure_count': failure_mentions,
                    'recent_fixes': recent_commits[:3]
                })
        
        return risky_files

    def _suggest_test_cases(
        self, 
        pr: Dict[str, Any], 
        files: List[Dict[str, Any]], 
        file_analysis: Dict[str, Any]
    ) -> List[str]:
        """Use AI to suggest specific test cases based on changed code"""
        
        try:
            # Build context from changed files
            code_changes = []
            for code_file in file_analysis['code_files'][:5]:  # Limit to 5 files
                code_changes.append(f"File: {code_file['filename']}\n"
                                  f"Changes: +{code_file['additions']} -{code_file['deletions']}\n"
                                  f"Patch:\n{code_file.get('patch', '')[:500]}")
            
            if not code_changes:
                return []
            
            prompt = f"""Analyze this Pull Request and suggest specific test cases.

PR Title: {pr['title']}
PR Description: {pr.get('body', '')[:500]}

Changed Files:
{chr(10).join(code_changes)}

Based on the code changes, suggest 5 specific test cases that should be added or verified:
1. Focus on edge cases and error conditions
2. Consider GPU memory, multi-GPU scenarios if relevant
3. Think about compatibility and regression testing
4. Suggest integration tests if multiple components are affected

Respond with a JSON array of test case descriptions:
["test case 1", "test case 2", ...]"""

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = message.content[0].text
            
            # Extract JSON array
            import json
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group(0))
                return suggestions
            
            return []
            
        except Exception as e:
            logger.error(f"Error generating test suggestions: {e}")
            return []

    def _calculate_quality_score(
        self,
        missing_tests: Dict[str, Any],
        is_test_only: bool,
        flaky_test_changes: List[Dict[str, Any]],
        high_risk_changes: List[Dict[str, Any]],
        risky_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate overall quality score for the PR"""
        
        score = 100  # Start with perfect score
        issues = []
        
        # Deduct for missing tests
        if missing_tests['missing_tests']:
            deduction = min(30, missing_tests['new_code_lines'] // 10)
            score -= deduction
            issues.append(f"Missing tests for {missing_tests['new_code_lines']} lines of new code (-{deduction})")
        
        # Deduct for test-only PR (might indicate incomplete work)
        if is_test_only:
            score -= 10
            issues.append("Test-only PR - verify if corresponding code changes are needed (-10)")
        
        # Deduct for flaky test modifications
        if flaky_test_changes:
            score -= 15
            issues.append(f"Modifies {len(flaky_test_changes)} known flaky test(s) (-15)")
        
        # Deduct for high-risk changes
        if high_risk_changes:
            score -= 20
            issues.append(f"Contains {len(high_risk_changes)} high-risk change(s) (-20)")
        
        # Deduct for files with failure history
        if risky_files:
            score -= 10
            issues.append(f"Touches {len(risky_files)} file(s) with failure history (-10)")
        
        score = max(0, score)  # Don't go below 0
        
        # Determine grade
        if score >= 90:
            grade = 'A'
            color = 'green'
        elif score >= 75:
            grade = 'B'
            color = 'yellow'
        elif score >= 60:
            grade = 'C'
            color = 'orange'
        else:
            grade = 'D'
            color = 'red'
        
        return {
            'score': score,
            'grade': grade,
            'color': color,
            'issues': issues,
            'recommendation': self._get_recommendation(score)
        }

    def _get_recommendation(self, score: int) -> str:
        """Get review recommendation based on score"""
        if score >= 90:
            return "APPROVE - High quality PR with proper test coverage"
        elif score >= 75:
            return "APPROVE with minor comments - Good PR, minor improvements suggested"
        elif score >= 60:
            return "REQUEST CHANGES - Significant issues need attention before merge"
        else:
            return "REJECT - Major quality issues detected, needs substantial rework"

    def _generate_review_comments(
        self,
        missing_tests: Dict[str, Any],
        is_test_only: bool,
        flaky_test_changes: List[Dict[str, Any]],
        high_risk_changes: List[Dict[str, Any]],
        risky_files: List[Dict[str, Any]],
        test_suggestions: List[str]
    ) -> List[Dict[str, Any]]:
        """Generate specific review comments for the PR"""
        
        comments = []
        
        # Comment on missing tests
        if missing_tests['missing_tests']:
            untested_files = missing_tests['untested_files']
            comments.append({
                'type': 'missing_tests',
                'severity': 'high',
                'title': 'Missing Tests for New Code',
                'message': f"You added {missing_tests['new_code_lines']} lines of code but only "
                          f"{missing_tests['new_test_lines']} lines of tests. "
                          f"Please add tests for: {', '.join(untested_files[:3])}",
                'files': untested_files
            })
        
        # Comment on test-only PR
        if is_test_only:
            comments.append({
                'type': 'test_only',
                'severity': 'medium',
                'title': 'Test-Only PR',
                'message': "This PR only modifies test files. If you're fixing a bug or adding a feature, "
                          "make sure the corresponding code changes are included.",
                'files': []
            })
        
        # Comment on flaky tests
        if flaky_test_changes:
            for flaky in flaky_test_changes:
                comments.append({
                    'type': 'flaky_test',
                    'severity': 'high',
                    'title': f"Modifying Flaky Test: {flaky['filename']}",
                    'message': f"This file contains a known flaky test ({flaky['flaky_test_name']}). "
                              f"Consider adding retries, increasing timeouts, or fixing race conditions.",
                    'files': [flaky['filename']]
                })
        
        # Comment on high-risk changes
        if high_risk_changes:
            for risk in high_risk_changes:
                risk_types_str = ', '.join(risk['risk_types'])
                comments.append({
                    'type': 'high_risk',
                    'severity': 'critical',
                    'title': f"High-Risk Change: {risk['filename']}",
                    'message': f"This file contains high-risk code ({risk_types_str}). "
                              f"Ensure thorough testing including: GPU memory validation, "
                              f"multi-GPU scenarios, and stress testing.",
                    'files': [risk['filename']]
                })
        
        # Comment on risky files
        if risky_files:
            for risky in risky_files:
                comments.append({
                    'type': 'failure_history',
                    'severity': 'medium',
                    'title': f"File with Failure History: {risky['filename']}",
                    'message': f"This file has failed {risky['failure_count']} times in the last 30 days. "
                              f"Recent fixes: {', '.join([c['message'][:50] for c in risky['recent_fixes'][:2]])}. "
                              f"Extra caution recommended.",
                    'files': [risky['filename']]
                })
        
        # Add test suggestions
        if test_suggestions:
            comments.append({
                'type': 'test_suggestions',
                'severity': 'info',
                'title': 'Suggested Test Cases',
                'message': 'Consider adding these test cases:\n' + '\n'.join([f"- {s}" for s in test_suggestions]),
                'files': []
            })
        
        return comments



