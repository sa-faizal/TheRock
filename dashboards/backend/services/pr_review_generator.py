import os
from typing import List, Dict, Any, Optional
import anthropic
import logging
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)


class PRReviewGenerator:
    """
    PR Review Suggestion Generator - Generate intelligent review recommendations:
    1. Generate test recommendations: "You modified cuda_kernels.py but didn't add tests"
    2. Flag potential issues: "This file has failed CI 5 times in last 30 days"
    3. Suggest reviewers based on file expertise (git blame + historical fixes)
    4. Comment on PR with analysis (dashboard only, not GitHub yet)
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_review(
        self,
        pr: Dict[str, Any],
        analysis_result: Dict[str, Any],
        commit_history: Optional[List[Dict[str, Any]]] = None,
        flaky_test_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive review suggestions for a PR
        
        Args:
            pr: PR metadata
            analysis_result: Results from PRAnalyzer
            commit_history: Git commit history for affected files
            flaky_test_analysis: Flaky test detection results
            
        Returns:
            Review suggestions including comments, reviewers, and recommendations
        """
        
        # Get AI-powered overall assessment
        overall_assessment = self._generate_overall_assessment(pr, analysis_result)
        
        # Determine approval recommendation
        should_approve, should_request_changes, blocking_issues, non_blocking_issues = \
            self._determine_approval_status(analysis_result, flaky_test_analysis)
        
        # Suggest reviewers based on file expertise
        suggested_reviewers = self._suggest_reviewers(pr, commit_history or [])
        
        # Generate test recommendations
        required_tests, recommended_tests = self._generate_test_recommendations(
            pr, analysis_result
        )
        
        # Assess risk level
        risk_level, risk_factors = self._assess_risk(analysis_result, flaky_test_analysis)
        
        # Generate inline comments for specific files/lines
        inline_comments = self._generate_inline_comments(pr, analysis_result)
        
        # Generate summary comment
        summary_comment = self._generate_summary_comment(
            pr, analysis_result, overall_assessment, blocking_issues,
            non_blocking_issues, risk_level, suggested_reviewers
        )
        
        return {
            'pr_number': pr['number'],
            'pr_title': pr['title'],
            'overall_assessment': overall_assessment,
            'should_approve': should_approve,
            'should_request_changes': should_request_changes,
            'blocking_issues': blocking_issues,
            'non_blocking_issues': non_blocking_issues,
            'suggested_reviewers': suggested_reviewers,
            'required_tests': required_tests,
            'recommended_tests': recommended_tests,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'inline_comments': inline_comments,
            'summary_comment': summary_comment,
            'generated_at': datetime.now()
        }

    def _generate_overall_assessment(
        self,
        pr: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> str:
        """Use AI to generate overall assessment of the PR"""
        
        try:
            # Build context
            quality_score = analysis_result['quality_score']
            review_comments = analysis_result['review_comments']
            
            prompt = f"""Provide a brief overall assessment of this Pull Request:

PR #{pr['number']}: {pr['title']}
Description: {pr.get('body', '')[:500]}

Quality Score: {quality_score['score']}/100 (Grade: {quality_score['grade']})

Issues Found:
{chr(10).join(['- ' + issue for issue in quality_score['issues']])}

Review Comments:
{chr(10).join([f"- [{c['severity'].upper()}] {c['title']}: {c['message'][:100]}" for c in review_comments[:5]])}

Provide a 2-3 sentence assessment focusing on:
1. Overall code quality
2. Main concerns or strengths
3. Readiness for merge

Be constructive and specific."""

            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Error generating assessment: {e}")
            return f"Quality Score: {quality_score['score']}/100. {quality_score['recommendation']}"

    def _determine_approval_status(
        self,
        analysis_result: Dict[str, Any],
        flaky_test_analysis: Optional[Dict[str, Any]]
    ) -> tuple:
        """Determine if PR should be approved or needs changes"""
        
        quality_score = analysis_result['quality_score']['score']
        review_comments = analysis_result['review_comments']
        
        blocking_issues = []
        non_blocking_issues = []
        
        # Categorize issues
        for comment in review_comments:
            severity = comment['severity']
            issue_desc = f"{comment['title']}: {comment['message'][:80]}"
            
            if severity in ['critical', 'high']:
                blocking_issues.append(issue_desc)
            else:
                non_blocking_issues.append(issue_desc)
        
        # Check flaky test analysis
        if flaky_test_analysis and flaky_test_analysis.get('newly_flaky_count', 0) > 2:
            blocking_issues.append(
                f"Introduces {flaky_test_analysis['newly_flaky_count']} new flaky tests"
            )
        
        # Determine approval
        should_approve = quality_score >= 75 and len(blocking_issues) == 0
        should_request_changes = len(blocking_issues) > 0 or quality_score < 60
        
        return should_approve, should_request_changes, blocking_issues, non_blocking_issues

    def _suggest_reviewers(
        self,
        pr: Dict[str, Any],
        commit_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Suggest reviewers based on file expertise
        Uses git blame + historical fixes to find experts
        """
        
        # Count contributions by author for affected files
        author_contributions = {}
        
        for commit in commit_history:
            author = commit.get('author', 'unknown')
            
            if author not in author_contributions:
                author_contributions[author] = {
                    'name': author,
                    'commits': 0,
                    'files': set(),
                    'recent_commits': []
                }
            
            author_contributions[author]['commits'] += 1
            author_contributions[author]['files'].update(commit.get('files_changed', []))
            author_contributions[author]['recent_commits'].append({
                'sha': commit.get('sha', '')[:7],
                'message': commit.get('message', '')[:50],
                'date': commit.get('date')
            })
        
        # Rank reviewers by expertise
        reviewers = []
        for author, data in author_contributions.items():
            if data['commits'] >= 3:  # Minimum threshold
                expertise_score = data['commits'] / len(commit_history) if commit_history else 0
                
                reviewers.append({
                    'name': author,
                    'expertise_score': round(expertise_score, 3),
                    'commits': data['commits'],
                    'files_touched': len(data['files']),
                    'reason': f"Has {data['commits']} commits touching {len(data['files'])} of the modified files",
                    'recent_work': data['recent_commits'][:3]
                })
        
        # Sort by expertise
        reviewers.sort(key=lambda x: x['expertise_score'], reverse=True)
        
        return reviewers[:5]  # Top 5 suggested reviewers

    def _generate_test_recommendations(
        self,
        pr: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> tuple:
        """Generate required and recommended test cases"""
        
        required_tests = []
        recommended_tests = analysis_result.get('test_suggestions', [])
        
        # Required tests based on missing test analysis
        missing_tests = analysis_result.get('missing_tests', {})
        if missing_tests.get('missing_tests', False):
            for file in missing_tests.get('untested_files', []):
                required_tests.append(
                    f"Add unit tests for new code in {file}"
                )
        
        # Required tests for high-risk changes
        high_risk_changes = analysis_result.get('high_risk_changes', [])
        for risk in high_risk_changes:
            if 'gpu_kernel' in risk.get('risk_types', []):
                required_tests.append(
                    f"Add GPU kernel validation tests for {risk['filename']}"
                )
            if 'distributed_training' in risk.get('risk_types', []):
                required_tests.append(
                    f"Add multi-GPU distributed training tests for {risk['filename']}"
                )
        
        return required_tests, recommended_tests

    def _assess_risk(
        self,
        analysis_result: Dict[str, Any],
        flaky_test_analysis: Optional[Dict[str, Any]]
    ) -> tuple:
        """Assess overall risk level of the PR"""
        
        risk_score = 0
        risk_factors = []
        
        # High-risk changes
        high_risk_changes = analysis_result.get('high_risk_changes', [])
        if high_risk_changes:
            risk_score += len(high_risk_changes) * 10
            risk_factors.append(f"{len(high_risk_changes)} high-risk file changes (GPU kernels, distributed training)")
        
        # Missing tests
        if analysis_result.get('missing_tests', {}).get('missing_tests', False):
            risk_score += 15
            risk_factors.append("Missing tests for new code")
        
        # Flaky test changes
        flaky_changes = analysis_result.get('flaky_test_changes', [])
        if flaky_changes:
            risk_score += len(flaky_changes) * 5
            risk_factors.append(f"Modifies {len(flaky_changes)} known flaky test(s)")
        
        # Risky files (failure history)
        risky_files = analysis_result.get('risky_files', [])
        if risky_files:
            risk_score += len(risky_files) * 5
            risk_factors.append(f"{len(risky_files)} files with recent failure history")
        
        # Newly flaky tests
        if flaky_test_analysis:
            newly_flaky = flaky_test_analysis.get('newly_flaky_count', 0)
            if newly_flaky > 0:
                risk_score += newly_flaky * 10
                risk_factors.append(f"Introduces {newly_flaky} new flaky test(s)")
        
        # Large PR size
        total_lines = analysis_result['file_analysis']['total_additions'] + \
                     analysis_result['file_analysis']['total_deletions']
        if total_lines > 1000:
            risk_score += 10
            risk_factors.append(f"Large PR size ({total_lines} lines changed)")
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = 'critical'
        elif risk_score >= 30:
            risk_level = 'high'
        elif risk_score >= 15:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return risk_level, risk_factors

    def _generate_inline_comments(
        self,
        pr: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate inline comments for specific files"""
        
        inline_comments = []
        
        # Comments for files missing tests
        missing_tests = analysis_result.get('missing_tests', {})
        for file in missing_tests.get('untested_files', []):
            inline_comments.append({
                'file': file,
                'line': 1,  # First line of file
                'comment': f"⚠️ **Missing Tests**: This file has significant new code but no corresponding test additions. "
                          f"Please add unit tests to cover the new functionality."
            })
        
        # Comments for high-risk changes
        for risk in analysis_result.get('high_risk_changes', []):
            risk_types = ', '.join(risk['risk_types'])
            inline_comments.append({
                'file': risk['filename'],
                'line': 1,
                'comment': f"🚨 **High-Risk Change**: This file contains {risk_types}. "
                          f"Ensure thorough testing including edge cases, GPU memory validation, "
                          f"and stress testing before merge."
            })
        
        # Comments for flaky tests
        for flaky in analysis_result.get('flaky_test_changes', []):
            inline_comments.append({
                'file': flaky['filename'],
                'line': 1,
                'comment': f"⚡ **Flaky Test Warning**: This file contains a known flaky test ({flaky['flaky_test_name']}). "
                          f"Consider: adding retries, increasing timeouts, fixing race conditions, "
                          f"or improving test isolation."
            })
        
        # Comments for files with failure history
        for risky in analysis_result.get('risky_files', []):
            inline_comments.append({
                'file': risky['filename'],
                'line': 1,
                'comment': f"📊 **Failure History**: This file has failed {risky['failure_count']} times recently. "
                          f"Review recent fixes and ensure your changes don't reintroduce issues."
            })
        
        return inline_comments

    def _generate_summary_comment(
        self,
        pr: Dict[str, Any],
        analysis_result: Dict[str, Any],
        overall_assessment: str,
        blocking_issues: List[str],
        non_blocking_issues: List[str],
        risk_level: str,
        suggested_reviewers: List[Dict[str, Any]]
    ) -> str:
        """Generate a comprehensive summary comment for the PR"""
        
        quality_score = analysis_result['quality_score']
        
        # Build summary
        summary_parts = []
        
        # Header
        summary_parts.append(f"## 🤖 AI-Powered PR Analysis for #{pr['number']}")
        summary_parts.append("")
        
        # Quality score
        emoji = "🟢" if quality_score['grade'] == 'A' else \
                "🟡" if quality_score['grade'] == 'B' else \
                "🟠" if quality_score['grade'] == 'C' else "🔴"
        
        summary_parts.append(f"### {emoji} Quality Score: {quality_score['score']}/100 (Grade: {quality_score['grade']})")
        summary_parts.append(f"**Recommendation**: {quality_score['recommendation']}")
        summary_parts.append("")
        
        # Overall assessment
        summary_parts.append(f"### 📋 Overall Assessment")
        summary_parts.append(overall_assessment)
        summary_parts.append("")
        
        # Risk level
        risk_emoji = "🚨" if risk_level == 'critical' else \
                    "⚠️" if risk_level == 'high' else \
                    "⚡" if risk_level == 'medium' else "✅"
        summary_parts.append(f"### {risk_emoji} Risk Level: {risk_level.upper()}")
        summary_parts.append("")
        
        # Blocking issues
        if blocking_issues:
            summary_parts.append(f"### 🚫 Blocking Issues ({len(blocking_issues)})")
            for issue in blocking_issues:
                summary_parts.append(f"- {issue}")
            summary_parts.append("")
        
        # Non-blocking issues
        if non_blocking_issues:
            summary_parts.append(f"### 💡 Suggestions ({len(non_blocking_issues)})")
            for issue in non_blocking_issues:
                summary_parts.append(f"- {issue}")
            summary_parts.append("")
        
        # Test recommendations
        test_suggestions = analysis_result.get('test_suggestions', [])
        if test_suggestions:
            summary_parts.append(f"### 🧪 Suggested Test Cases")
            for i, suggestion in enumerate(test_suggestions[:5], 1):
                summary_parts.append(f"{i}. {suggestion}")
            summary_parts.append("")
        
        # Suggested reviewers
        if suggested_reviewers:
            summary_parts.append(f"### 👥 Suggested Reviewers")
            for reviewer in suggested_reviewers[:3]:
                summary_parts.append(f"- **{reviewer['name']}** - {reviewer['reason']}")
            summary_parts.append("")
        
        # File statistics
        file_analysis = analysis_result['file_analysis']
        summary_parts.append(f"### 📊 Change Statistics")
        summary_parts.append(f"- Total Files: {file_analysis['total_files']}")
        summary_parts.append(f"- Code Files: {len(file_analysis['code_files'])}")
        summary_parts.append(f"- Test Files: {len(file_analysis['test_files'])}")
        summary_parts.append(f"- Lines Added: +{file_analysis['total_additions']}")
        summary_parts.append(f"- Lines Deleted: -{file_analysis['total_deletions']}")
        
        # Test coverage ratio
        missing_tests = analysis_result.get('missing_tests', {})
        if missing_tests:
            ratio = missing_tests.get('test_coverage_ratio', 0)
            summary_parts.append(f"- Test Coverage Ratio: {ratio:.2f}")
        summary_parts.append("")
        
        # Footer
        summary_parts.append("---")
        summary_parts.append("*This analysis was generated by ROCm Sentinel AI. Review carefully and use your judgment.*")
        
        return "\n".join(summary_parts)



