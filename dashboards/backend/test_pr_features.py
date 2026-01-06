#!/usr/bin/env python3
"""
Test script for PR Analysis Features
Demonstrates the three main features:
1. PR Quality Analysis
2. Flaky Test Detection
3. PR Review Suggestions
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_json(data: Dict[Any, Any], indent: int = 2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent, default=str))


def test_get_prs():
    """Test getting list of pull requests"""
    print_section("TEST 1: Get Open Pull Requests")
    
    response = requests.get(f"{BASE_URL}/api/prs?state=open&limit=5")
    
    if response.status_code == 200:
        prs = response.json()
        print(f"✅ Successfully fetched {len(prs)} PRs")
        if prs:
            print("\nFirst PR:")
            print_json({
                'number': prs[0]['number'],
                'title': prs[0]['title'],
                'author': prs[0]['author'],
                'state': prs[0]['state'],
                'additions': prs[0]['additions'],
                'deletions': prs[0]['deletions']
            })
        return prs
    else:
        print(f"❌ Failed to fetch PRs: {response.status_code}")
        print(response.text)
        return []


def test_analyze_pr(pr_number: int):
    """Test PR quality analysis"""
    print_section(f"TEST 2: Analyze PR #{pr_number}")
    
    response = requests.post(
        f"{BASE_URL}/api/prs/{pr_number}/analyze",
        params={
            'include_test_analysis': True,
            'include_review_suggestions': True
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        analysis = result['analysis']
        
        print("✅ PR Analysis Complete\n")
        
        # Quality Score
        quality = analysis['quality_score']
        print(f"📊 Quality Score: {quality['score']}/100 (Grade: {quality['grade']})")
        print(f"   Recommendation: {quality['recommendation']}\n")
        
        # File Statistics
        print("📁 File Statistics:")
        print(f"   - Total Files: {analysis['total_files']}")
        print(f"   - Code Files: {analysis['code_files_count']}")
        print(f"   - Test Files: {analysis['test_files_count']}")
        print(f"   - New Code Lines: {analysis['new_code_lines']}")
        print(f"   - New Test Lines: {analysis['new_test_lines']}")
        print(f"   - Test Coverage Ratio: {analysis['test_coverage_ratio']:.2f}\n")
        
        # Flags
        print("🚩 Flags:")
        print(f"   - Missing Tests: {analysis['missing_tests']}")
        print(f"   - Test-Only PR: {analysis['is_test_only_pr']}")
        print(f"   - High-Risk Changes: {analysis['has_high_risk_changes']}")
        print(f"   - Flaky Test Changes: {analysis['has_flaky_test_changes']}")
        print(f"   - Risky Files: {analysis['has_risky_files']}\n")
        
        # Review Comments
        if analysis['review_comments']:
            print(f"💬 Review Comments ({len(analysis['review_comments'])}):")
            for comment in analysis['review_comments'][:3]:  # Show first 3
                print(f"   [{comment['severity'].upper()}] {comment['title']}")
                print(f"      {comment['message'][:100]}...")
            print()
        
        # Test Suggestions
        if analysis['test_suggestions']:
            print(f"🧪 Test Suggestions ({len(analysis['test_suggestions'])}):")
            for i, suggestion in enumerate(analysis['test_suggestions'][:3], 1):
                print(f"   {i}. {suggestion}")
            print()
        
        # Review Suggestions
        if result.get('review_suggestion'):
            review = result['review_suggestion']
            print("👥 Review Suggestions:")
            print(f"   - Should Approve: {review['should_approve']}")
            print(f"   - Should Request Changes: {review['should_request_changes']}")
            print(f"   - Risk Level: {review['risk_level'].upper()}")
            
            if review['blocking_issues']:
                print(f"\n   🚫 Blocking Issues ({len(review['blocking_issues'])}):")
                for issue in review['blocking_issues'][:2]:
                    print(f"      - {issue[:80]}...")
            
            if review['suggested_reviewers']:
                print(f"\n   👥 Suggested Reviewers:")
                for reviewer in review['suggested_reviewers'][:3]:
                    print(f"      - {reviewer['name']} (expertise: {reviewer['expertise_score']:.2f})")
                    print(f"        {reviewer['reason']}")
        
        return result
    else:
        print(f"❌ Failed to analyze PR: {response.status_code}")
        print(response.text)
        return None


def test_record_flaky_tests():
    """Test recording test results for flaky test detection"""
    print_section("TEST 3: Record Test Results for Flaky Detection")
    
    # Simulate test results for the same commit
    test_results = [
        {
            'test_name': 'test_gpu_memory_sync',
            'status': 'passed',
            'commit_sha': 'abc123def456',
            'run_id': 'ci-run-001',
            'duration_ms': 150.5
        },
        {
            'test_name': 'test_gpu_memory_sync',
            'status': 'failed',
            'commit_sha': 'abc123def456',
            'run_id': 'ci-run-002',
            'duration_ms': 145.2,
            'error_message': 'Timeout: hipDeviceSynchronize failed'
        },
        {
            'test_name': 'test_gpu_memory_sync',
            'status': 'passed',
            'commit_sha': 'abc123def456',
            'run_id': 'ci-run-003',
            'duration_ms': 152.8
        },
        {
            'test_name': 'test_distributed_training',
            'status': 'passed',
            'commit_sha': 'abc123def456',
            'run_id': 'ci-run-001',
            'duration_ms': 2500.0
        },
    ]
    
    print(f"Recording {len(test_results)} test results...\n")
    
    for result in test_results:
        response = requests.post(f"{BASE_URL}/api/flaky-tests/record", json=result)
        if response.status_code == 200:
            print(f"✅ Recorded: {result['test_name']} - {result['status']}")
        else:
            print(f"❌ Failed to record: {result['test_name']}")
    
    print("\n✅ Test results recorded successfully")


def test_get_flaky_tests():
    """Test getting flaky tests"""
    print_section("TEST 4: Get Flaky Tests")
    
    response = requests.get(f"{BASE_URL}/api/flaky-tests?min_score=0.1&limit=10")
    
    if response.status_code == 200:
        result = response.json()
        flaky_tests = result['flaky_tests']
        
        print(f"✅ Found {len(flaky_tests)} flaky tests\n")
        
        if flaky_tests:
            print("Top Flaky Tests:")
            for test in flaky_tests[:5]:
                print(f"\n📊 {test['test_name']}")
                print(f"   Flakiness Score: {test['flakiness_score']:.2%}")
                print(f"   Failure Rate: {test['failure_rate']:.2%}")
                print(f"   Total Runs: {test['total_runs']} (passed: {test['passed_runs']}, failed: {test['failed_runs']})")
                print(f"   Severity: {test['severity'].upper()}")
                
                if test['common_errors']:
                    print(f"   Common Errors: {', '.join(test['common_errors'].keys())}")
                
                if test['suggested_fixes']:
                    print(f"   Suggested Fixes:")
                    for fix in test['suggested_fixes'][:2]:
                        print(f"      - {fix}")
        
        # Statistics
        stats = result['statistics']
        print(f"\n📈 Statistics:")
        print(f"   Total Tests Tracked: {stats['total_tests_tracked']}")
        print(f"   Flaky Tests: {stats['flaky_tests_count']} ({stats['flaky_percentage']:.1f}%)")
        
        if stats.get('severity_breakdown'):
            print(f"   Severity Breakdown: {stats['severity_breakdown']}")
        
        return result
    else:
        print(f"❌ Failed to get flaky tests: {response.status_code}")
        print(response.text)
        return None


def test_get_test_history(test_name: str):
    """Test getting test history"""
    print_section(f"TEST 5: Get Test History for '{test_name}'")
    
    response = requests.get(f"{BASE_URL}/api/flaky-tests/{test_name}/history?limit=10")
    
    if response.status_code == 200:
        result = response.json()
        history = result['history']
        
        print(f"✅ Found {len(history)} historical results\n")
        
        if history:
            print("Recent Results:")
            for i, result in enumerate(history[:5], 1):
                status_emoji = "✅" if result['status'] == 'passed' else "❌" if result['status'] == 'failed' else "⏭️"
                print(f"   {i}. {status_emoji} {result['status'].upper()} - "
                      f"Commit: {result['commit_sha'][:7]} - "
                      f"Run: {result['run_id']}")
                if result.get('duration_ms'):
                    print(f"      Duration: {result['duration_ms']:.1f}ms")
        
        return result
    else:
        print(f"❌ Failed to get test history: {response.status_code}")
        return None


def main():
    """Run all tests"""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "PR ANALYSIS FEATURES - TEST SUITE" + " " * 25 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Test 1: Get PRs
    prs = test_get_prs()
    
    if not prs:
        print("\n⚠️  No PRs available. Please ensure:")
        print("   1. Backend server is running (python app.py)")
        print("   2. GitHub token is configured")
        print("   3. Repository has open PRs")
        return
    
    # Test 2: Analyze a PR
    pr_number = prs[0]['number'] if prs else None
    if pr_number:
        test_analyze_pr(pr_number)
    
    # Test 3: Record test results
    test_record_flaky_tests()
    
    # Test 4: Get flaky tests
    flaky_result = test_get_flaky_tests()
    
    # Test 5: Get test history
    if flaky_result and flaky_result['flaky_tests']:
        test_name = flaky_result['flaky_tests'][0]['test_name']
        test_get_test_history(test_name)
    else:
        test_get_test_history('test_gpu_memory_sync')
    
    # Summary
    print_section("TEST SUMMARY")
    print("✅ All tests completed successfully!")
    print("\nAvailable Endpoints:")
    print("   - GET  /api/prs - List pull requests")
    print("   - GET  /api/prs/{pr_number} - Get PR details")
    print("   - POST /api/prs/{pr_number}/analyze - Analyze PR quality")
    print("   - GET  /api/flaky-tests - List flaky tests")
    print("   - POST /api/flaky-tests/record - Record test result")
    print("   - GET  /api/flaky-tests/{test_name}/history - Get test history")
    print("\nDocumentation: PR_ANALYSIS_FEATURES.md")


if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend server")
        print("   Please start the server with: python app.py")
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()



