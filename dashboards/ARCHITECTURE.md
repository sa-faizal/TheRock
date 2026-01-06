# TheRock Dashboard Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Dashboard  │  │   Analysis   │  │     Chat     │          │
│  │  index.html  │  │ analysis.html│  │  chat.html   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┴──────────────────┘                  │
│                            │                                      │
└────────────────────────────┼──────────────────────────────────────┘
                             │
                             │ HTTP/REST
                             │
┌────────────────────────────┼──────────────────────────────────────┐
│                    BACKEND API (FastAPI)                          │
├────────────────────────────┼──────────────────────────────────────┤
│                         app.py                                    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │              NEW ENDPOINTS (v2.0)                      │     │
│  │                                                          │     │
│  │  POST /api/issues/refresh      - Clear cache & reload  │     │
│  │  POST /api/analyze/issue/{id}  - Single issue analysis │     │
│  │  GET  /api/issues/{id}/comments - Get issue comments   │     │
│  │  POST /api/chat                - AI chat queries       │     │
│  │  GET  /api/issues?since_days   - Date filtering        │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │           EXISTING ENDPOINTS (v1.0)                    │     │
│  │                                                          │     │
│  │  GET  /api/issues              - Get open/closed issues│     │
│  │  GET  /api/issues/{id}         - Get single issue      │     │
│  │  POST /api/analyze             - Bulk analysis         │     │
│  │  GET  /api/stats               - Dashboard stats       │     │
│  │  GET  /api/health              - Health check          │     │
│  │  GET  /api/cache/status        - Cache info            │     │
│  │  POST /api/cache/clear         - Clear cache           │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                   │
└─────────────┬───────────────────────┬─────────────────┬──────────┘
              │                       │                 │
              │                       │                 │
    ┌─────────▼─────────┐  ┌─────────▼────────┐  ┌────▼──────────┐
    │  GitHubService    │  │   AIAnalyzer     │  │  GitTracer    │
    │  github_service.py│  │  ai_analyzer.py  │  │ git_tracer.py │
    └─────────┬─────────┘  └─────────┬────────┘  └────┬──────────┘
              │                       │                 │
              │                       │                 │
┌─────────────▼─────────┐  ┌─────────▼────────┐  ┌────▼──────────┐
│  GitHub API           │  │  Claude API      │  │  Git Repo     │
│  (PyGithub)           │  │  (Anthropic)     │  │  (GitPython)  │
│                       │  │                  │  │               │
│  - Fetch issues       │  │  - Analyze text  │  │  - Blame      │
│  - Get comments       │  │  - Generate      │  │  - History    │
│  - List commits       │  │    insights      │  │  - Diff       │
│  - Rate limiting      │  │  - Chat responses│  │               │
│                       │  │                  │  │               │
│  With SMART CACHING:  │  │                  │  │               │
│  ├─ Open Issues: 5min │  │                  │  │               │
│  ├─ Closed: 1hr       │  │                  │  │               │
│  ├─ Commits: 30min    │  │                  │  │               │
│  ├─ Details: 10min    │  │                  │  │               │
│  └─ Comments: 15min   │  │                  │  │               │
└───────────────────────┘  └──────────────────┘  └───────────────┘
```

## Data Flow

### 1. Load Issues (with Cache)

```
User clicks "Load Open Issues"
        │
        ▼
Frontend → GET /api/issues?limit=20
        │
        ▼
Backend checks cache (5 min TTL)
        │
        ├─ Cache HIT → Return cached data ✅ (Fast!)
        │
        └─ Cache MISS → Fetch from GitHub API
                        │
                        ▼
                    Store in cache
                        │
                        ▼
                    Return fresh data
```

### 2. Load New Issues (Force Refresh)

```
User clicks "🔄 Load New Issues"
        │
        ▼
Frontend → POST /api/issues/refresh
        │
        ▼
Backend clears cache ("open_issues")
        │
        ▼
Fetch fresh data from GitHub API
        │
        ▼
Store in cache (new 5 min TTL)
        │
        ▼
Return fresh data + stats update
```

### 3. Date Filtering

```
User selects "Last 30 days" → Apply Filter
        │
        ▼
Frontend → GET /api/issues?since_days=30&limit=20
        │
        ▼
Backend checks cache first
        │
        ▼
Filter cached/fresh data by date
        │
        ├─ Keep issues where: (now - created_at) <= 30 days
        │
        ▼
Return filtered results
```

### 4. Individual Issue Analysis

```
User clicks "📊 Analyze" on issue #123
        │
        ▼
Frontend → analysis.html?issue=123
        │
        ▼
JavaScript → POST /api/analyze/issue/123
        │
        ▼
Backend parallel fetch:
        ├─ Issue details (GitHub API)
        ├─ Closed issues (for similarity)
        ├─ Recent commits (for root cause)
        └─ Issue comments (GitHub API)
        │
        ▼
AI Analyzer:
        ├─ Categorize components (NEW: accurate .gitmodules mapping)
        ├─ Find similar issues (TF-IDF)
        ├─ Identify root cause commits
        └─ Generate insights (Claude AI)
        │
        ▼
Return comprehensive analysis
        │
        ▼
Frontend displays:
        ├─ ROCm components (monorepo-aware)
        ├─ Severity tag
        ├─ AI summary
        ├─ Similar issues
        ├─ Root cause commits
        ├─ Fix suggestions
        ├─ Comments
        └─ Assignees
```

### 5. Chat Query

```
User: "What is the status of issue #123?"
        │
        ▼
Frontend → POST /api/chat {"query": "..."}
        │
        ▼
Backend extracts issue number (#123)
        │
        ▼
Fetch issue details + comments (cached)
        │
        ▼
Build context string:
        ├─ Issue metadata (state, created, updated)
        ├─ Assignees & labels
        ├─ Comment count
        └─ Last 3 comments
        │
        ▼
Claude AI prompt:
        "Answer user's question based on this context..."
        │
        ▼
Generate natural language response
        │
        ▼
Return response + issue link
        │
        ▼
Frontend displays in chat bubble
```

## Component Detection (Updated v2.0)

### Before (v1.0)
```
Generic categories:
├─ compiler
├─ runtime
├─ math-libs
├─ ml-libs
└─ ...

❌ Not aligned with TheRock structure
❌ Random assignments
❌ No monorepo awareness
```

### After (v2.0)
```
Based on .gitmodules:
├─ compiler/
│   ├─ llvm (llvm-project submodule)
│   ├─ hipify (HIPIFY submodule)
│   └─ spirv (SPIRV-LLVM-Translator submodule)
├─ comm-libs/
│   ├─ rccl
│   └─ rccl-tests
├─ ml-libs/
│   └─ composable_kernel
├─ profiler/
│   └─ rocprof-trace-decoder
├─ base/
│   ├─ half
│   ├─ rocm-cmake
│   ├─ amdsmi
│   └─ rocm-kpack
├─ rocm-libraries (monorepo)
│   ├─ rocBLAS
│   ├─ rocSOLVER
│   ├─ rocFFT
│   └─ ... (all math/compute libs)
├─ rocm-systems (monorepo)
│   ├─ HIP runtime
│   ├─ Device management
│   └─ Core systems
├─ third-party/
│   └─ mesa (amd-mesa)
└─ iree-libs/
    ├─ iree
    └─ fusilli

✅ Accurate path mapping
✅ Monorepo-aware
✅ Matches official structure
```

## Caching Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    CACHE MANAGER                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  cache = {                                              │
│    "open_issues_20": {                                  │
│      data: [...],                                       │
│      timestamp: 1704470400,                             │
│      ttl: 300  # 5 minutes                              │
│    },                                                   │
│    "closed_issues_180_200": {                           │
│      data: [...],                                       │
│      timestamp: 1704470000,                             │
│      ttl: 3600  # 1 hour                                │
│    },                                                   │
│    "issue_123": {                                       │
│      data: {...},                                       │
│      timestamp: 1704470200,                             │
│      ttl: 600  # 10 minutes                             │
│    },                                                   │
│    "comments_123": {                                    │
│      data: [...],                                       │
│      timestamp: 1704470300,                             │
│      ttl: 900  # 15 minutes                             │
│    }                                                    │
│  }                                                      │
│                                                         │
│  Operations:                                            │
│  ├─ _get_from_cache(key)  → Check age vs TTL          │
│  ├─ _set_cache(key, data, ttl)  → Store with metadata │
│  ├─ clear_cache(pattern)  → Delete matching entries   │
│  └─ get_cache_stats()  → Report metrics               │
│                                                         │
└─────────────────────────────────────────────────────────┘

Benefits:
✅ Reduced GitHub API calls (rate limit protection)
✅ Faster response times
✅ Configurable TTLs per data type
✅ Pattern-based invalidation
✅ Statistics for monitoring
```

## ROCm Component Mapping Algorithm

```python
def categorize_issue(issue):
    text = f"{issue.title} {issue.body}".lower()
    
    for component, keywords in ROCM_COMPONENTS.items():
        matches = [kw for kw in keywords if kw in text]
        
        if matches:
            confidence = min(len(matches) / len(keywords) * 2, 1.0)
            
            yield {
                'component': component,  # e.g., "rocm-libraries"
                'confidence': confidence,  # 0.0 to 1.0
                'reasoning': f"Matched: {matches[:3]}"
            }
    
    # Sort by confidence, return top 3
```

## Performance Metrics

### Before Caching
```
Load 20 issues:     ~5 seconds  (20 API calls)
Analyze 1 issue:    ~60 seconds (3 API calls + AI)
Get stats:          ~3 seconds  (2 API calls)
Total API calls:    25 calls/minute
```

### After Caching
```
Load 20 issues:     ~0.1 seconds  (cache hit)
Load new issues:    ~5 seconds    (1 API call, cache refresh)
Analyze 1 issue:    ~40 seconds   (2 API calls + AI, comments cached)
Get stats:          ~0.1 seconds  (cache hit)
Total API calls:    <5 calls/minute (80% reduction!)
```

## Security & Rate Limits

```
GitHub API Rate Limits:
├─ Authenticated: 5,000 requests/hour
├─ Unauthenticated: 60 requests/hour
└─ Search API: 30 requests/minute

Protection Mechanisms:
├─ Caching (primary defense)
├─ Rate limit monitoring (before each request)
├─ Exponential backoff (on 403 errors)
├─ Request queuing (planned)
└─ User notifications (rate limit warnings)

Anthropic API:
├─ Claude models with fallback chain
├─ Timeout handling
├─ Error recovery
└─ Cost optimization (caching analysis results)
```

## Future Architecture Enhancements

```
Planned:
├─ Database integration (PostgreSQL)
│   └─ Store analysis history
├─ WebSocket support
│   └─ Real-time issue updates
├─ Redis caching
│   └─ Distributed cache
├─ Job queue (Celery)
│   └─ Background analysis
├─ Webhooks
│   └─ Auto-analyze on new issues
└─ Multi-user authentication
    └─ Personal dashboards
```

---

**Version:** 2.0.0  
**Last Updated:** January 5, 2026



