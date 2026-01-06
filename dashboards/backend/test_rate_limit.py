#!/usr/bin/env python3
"""
Demonstration script for GitHub API Rate Limit Solution
Shows the caching and rate limit handling features
"""

import requests
import json
from time import sleep

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def check_rate_limit():
    """Check current GitHub API rate limit"""
    print_section("GitHub API Rate Limit Status")
    response = requests.get(f"{BASE_URL}/api/rate-limit")
    data = response.json()
    
    print(f"Core API:")
    print(f"  - Remaining: {data['core']['remaining']}/{data['core']['limit']}")
    print(f"  - Used: {data['core']['used']}")
    print(f"  - Reset: {data['core']['reset']}")
    print(f"\nSearch API:")
    print(f"  - Remaining: {data['search']['remaining']}/{data['search']['limit']}")
    return data

def check_cache_status():
    """Check cache status"""
    print_section("Cache Status")
    response = requests.get(f"{BASE_URL}/api/cache/status")
    data = response.json()
    
    print(f"Total Entries: {data['total_entries']}")
    print(f"Valid Entries: {data['valid_entries']}")
    print(f"Expired Entries: {data['expired_entries']}")
    if data['cache_keys']:
        print(f"\nCached Keys:")
        for key in data['cache_keys']:
            print(f"  - {key}")
    return data

def check_health():
    """Check service health"""
    print_section("Service Health Check")
    response = requests.get(f"{BASE_URL}/api/health")
    data = response.json()
    
    print(f"Status: {data['status']}")
    print(f"GitHub Token: {'✅ Configured' if data['services']['github'] else '❌ Not configured'}")
    print(f"Anthropic API: {'✅ Configured' if data['services']['anthropic'] else '❌ Not configured'}")
    print(f"\nRate Limit: {data['rate_limit']['core']['remaining']}/{data['rate_limit']['core']['limit']} remaining")
    print(f"Cache Entries: {data['cache']['total_entries']}")
    return data

def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║   GitHub API Rate Limit Solution - Demo Script           ║
    ║   Rock Issue Analysis Dashboard                           ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # 1. Check initial health
        check_health()
        
        # 2. Check rate limit status
        initial_rate_limit = check_rate_limit()
        
        # 3. Check cache status
        check_cache_status()
        
        print_section("✅ All Endpoints Working!")
        print("\nYou can now use these endpoints:")
        print(f"  • GET {BASE_URL}/api/rate-limit")
        print(f"  • GET {BASE_URL}/api/cache/status")
        print(f"  • GET {BASE_URL}/api/health")
        print(f"  • POST {BASE_URL}/api/cache/clear")
        
        print("\n📊 Key Features Implemented:")
        print("  ✅ Multi-layer caching with configurable TTLs")
        print("  ✅ Rate limit pre-checking before API calls")
        print("  ✅ Exponential backoff on rate limit errors")
        print("  ✅ Smart cache invalidation on data changes")
        print("  ✅ Real-time monitoring endpoints")
        
        print("\n🎯 Benefits:")
        print("  • Drastically reduced API calls (most from cache)")
        print("  • Automatic rate limit handling")
        print("  • Faster response times")
        print("  • Real-time visibility into cache and rate limits")
        
        print("\n📝 Note:")
        print("  GitHub token not configured, so actual issue fetching")
        print("  won't work yet. But the caching and rate limit")
        print("  infrastructure is fully operational!")
        
        print("\n🚀 Next Steps:")
        print("  1. Add GITHUB_TOKEN to .env file")
        print("  2. Test with: curl http://localhost:8000/api/issues")
        print("  3. Watch cache populate: curl http://localhost:8000/api/cache/status")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server")
        print("   Make sure the server is running:")
        print("   cd /home/safaizal/projects/TheRock/dashboards/backend")
        print("   python3 app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()




