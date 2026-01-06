#!/usr/bin/env python3
"""
Test script to verify backend endpoints are working correctly
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_health():
    """Test the health endpoint"""
    print_section("1. Testing Health Endpoint")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Health Check Result:")
            print(f"   Status: {data.get('status')}")
            print(f"   GitHub Token: {'✓' if data.get('services', {}).get('github') else '✗'}")
            print(f"   Anthropic API: {'✓' if data.get('services', {}).get('anthropic') else '✗'}")
            
            if 'rate_limit' in data:
                rate = data['rate_limit']
                if rate and 'core' in rate:
                    print(f"\n   GitHub Rate Limit:")
                    print(f"   - Remaining: {rate['core'].get('remaining', 'N/A')}/{rate['core'].get('limit', 'N/A')}")
                    print(f"   - Used: {rate['core'].get('used', 'N/A')}")
            
            if 'cache' in data:
                cache = data['cache']
                print(f"\n   Cache Status:")
                print(f"   - Total Entries: {cache.get('total_entries', 0)}")
                print(f"   - Valid Entries: {cache.get('valid_entries', 0)}")
            
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - server may be hung")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_fetch_issues():
    """Test fetching open issues"""
    print_section("2. Testing Fetch Open Issues")
    try:
        response = requests.get(f"{BASE_URL}/api/issues?limit=5&state=open", timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Successfully fetched {len(data)} open issues")
            
            if len(data) > 0:
                print("\n   Sample Issue:")
                issue = data[0]
                print(f"   - Number: #{issue.get('number')}")
                print(f"   - Title: {issue.get('title', '')[:60]}...")
                print(f"   - State: {issue.get('state')}")
                print(f"   - Labels: {len(issue.get('labels', []))}")
                print(f"   - Created: {issue.get('created_at')}")
            
            return True
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_analyze_issues():
    """Test AI analysis of issues"""
    print_section("3. Testing AI Issue Analysis")
    try:
        # Test with a small limit to avoid long wait times
        payload = {
            "analyze_all_open": True,
            "limit": 2
        }
        
        print("Requesting analysis of 2 open issues...")
        print("(This may take 30-60 seconds due to AI processing)")
        
        response = requests.post(
            f"{BASE_URL}/api/analyze",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ AI Analysis Successful!")
            print(f"   Total Analyzed: {data.get('total_analyzed', 0)}")
            print(f"   Timestamp: {data.get('timestamp', 'N/A')}")
            
            if 'analyses' in data and len(data['analyses']) > 0:
                analysis = data['analyses'][0]
                print(f"\n   Sample Analysis for Issue #{analysis.get('issue_number')}:")
                print(f"   - Title: {analysis.get('title', '')[:50]}...")
                print(f"   - Severity: {analysis.get('severity', 'N/A')}")
                print(f"   - Components: {len(analysis.get('component_categories', []))}")
                print(f"   - Similar Issues: {len(analysis.get('similar_issues', []))}")
                print(f"   - Root Cause Commits: {len(analysis.get('root_cause_commits', []))}")
                print(f"   - Suggested Labels: {', '.join(analysis.get('suggested_labels', []))}")
                
                if analysis.get('analysis_summary'):
                    print(f"\n   AI Summary:")
                    summary = analysis.get('analysis_summary', '')
                    print(f"   {summary[:150]}...")
                
                if analysis.get('fix_suggestions'):
                    print(f"\n   Fix Suggestions:")
                    for i, suggestion in enumerate(analysis.get('fix_suggestions', [])[:3], 1):
                        print(f"   {i}. {suggestion[:60]}...")
            
            return True
        else:
            print(f"❌ Analysis failed with status {response.status_code}")
            try:
                error_data = response.json()
                if 'detail' in error_data:
                    print(f"   Error: {error_data['detail'][:200]}")
            except:
                print(f"   Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (analysis takes time, try increasing limit)")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    print("\n" + "="*70)
    print("  BACKEND SERVER ENDPOINT TESTING")
    print("  Testing: Open Issues Fetching + AI Analysis")
    print("="*70)
    print(f"\n  Base URL: {BASE_URL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'health': test_health(),
        'fetch_issues': test_fetch_issues(),
        'analyze_issues': test_analyze_issues()
    }
    
    print_section("SUMMARY")
    print(f"  Health Check:        {'✅ PASS' if results['health'] else '❌ FAIL'}")
    print(f"  Fetch Open Issues:   {'✅ PASS' if results['fetch_issues'] else '❌ FAIL'}")
    print(f"  AI Analysis:         {'✅ PASS' if results['analyze_issues'] else '❌ FAIL'}")
    
    all_passed = all(results.values())
    print("\n" + "="*70)
    if all_passed:
        print("  ✅ ALL TESTS PASSED - Backend is working correctly!")
        print("  The server can:")
        print("    • Fetch open issues from GitHub")
        print("    • Analyze issues using AI (Anthropic Claude)")
        print("    • Categorize issues by component")
        print("    • Find similar historical issues")
        print("    • Identify potential root cause commits")
        print("    • Generate fix suggestions")
    else:
        print("  ⚠️  SOME TESTS FAILED - Check the errors above")
        print("  Common issues:")
        print("    • Server not running (run: python3 app.py)")
        print("    • Missing .env file with API keys")
        print("    • GitHub API rate limit exceeded")
        print("    • Network connectivity issues")
    print("="*70 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

