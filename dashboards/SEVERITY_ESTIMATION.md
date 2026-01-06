# 🎯 Severity Estimation - How It Works

## Overview

ROCm Sentinel uses **AI-powered severity estimation** to automatically classify issue severity based on multiple factors. The severity is determined by Claude AI (Anthropic) after analyzing the issue context.

---

## 📊 Severity Levels

### Critical 🔴
- **Definition:** System-breaking issues that affect all users
- **Examples:**
  - Complete system failure or crash
  - Data corruption or loss
  - Security vulnerabilities
  - Build system completely broken
  - Blocks production releases

### High 🟠
- **Definition:** Major functionality broken, affects many users
- **Examples:**
  - Key features not working
  - Performance degradation >50%
  - Affects multiple components
  - No workarounds available
  - Impacts CI/CD pipeline

### Medium 🟡
- **Definition:** Moderate issues with workarounds available
- **Examples:**
  - Feature partially broken
  - Performance issues <50%
  - Affects specific configurations
  - Workarounds exist
  - Edge cases in common scenarios

### Low 🟢
- **Definition:** Minor issues, cosmetic, or rare edge cases
- **Examples:**
  - Documentation errors
  - Cosmetic UI issues
  - Rare edge cases
  - Feature requests
  - Minor inconveniences

---

## 🧠 How Severity is Determined

### 1. **AI Analysis Process**

The severity estimation happens in `ai_analyzer.py` using the `_get_claude_analysis()` method:

```python
def _get_claude_analysis(
    self,
    issue: Dict[str, Any],
    component_categories: List[Dict[str, Any]],
    similar_issues: List[Dict[str, Any]]
) -> Dict[str, Any]:
```

### 2. **Input Factors**

The AI considers multiple data points:

#### A. Issue Content (Primary Factor)
```python
**Issue #{issue['number']}: {issue['title']}**
**Description:**
{issue['body'][:1500]}
```

**Analyzed aspects:**
- Keywords: "crash", "broken", "failure", "critical", "urgent"
- Impact scope: "all users", "production", "release blocker"
- Frequency: "always", "sometimes", "rarely"
- Reproducibility: Steps to reproduce, environment details

#### B. Affected Components
```python
**Detected Components:** {components_str or 'Unknown'}
```

**Component impact:**
- **rocm-systems** (runtime, core) → Higher severity
- **compiler/llvm** → Higher severity (affects builds)
- **base/amdsmi** → Medium severity (monitoring)
- **Documentation** → Lower severity

#### C. Historical Context
```python
**Similar Historical Issues:**
{similar_str or 'None found'}
```

**Pattern analysis:**
- If similar issues were critical → Likely critical
- If similar issues were quickly resolved → Might be lower
- If no similar issues → Novelty increases severity

#### D. User Impact Assessment
```python
1. **Severity** (critical/high/medium/low) - Consider impact on users
```

**The AI evaluates:**
- Number of affected users (all vs. some vs. few)
- Workflow disruption (completely blocked vs. inconvenient)
- Availability of workarounds
- Time sensitivity (immediate vs. can wait)

---

## 🔍 AI Prompt Structure

### The Complete Prompt

```python
prompt = f"""Analyze this GitHub issue from the ROCm/TheRock repository:

**Issue #{issue['number']}: {issue['title']}**

**Description:**
{issue['body'][:1500]}

**Detected Components:** {components_str or 'Unknown'}

**Similar Historical Issues:**
{similar_str or 'None found'}

Please provide:
1. **Severity** (critical/high/medium/low) - Consider impact on users
2. **Analysis Summary** (2-3 sentences) - What is the core problem?
3. **Fix Suggestions** (3-5 actionable items) - Specific steps to resolve this

Respond in JSON format:
{{
  "severity": "...",
  "summary": "...",
  "fix_suggestions": ["...", "...", "..."]
}}"""
```

### Why This Works

1. **Structured Input** - Clear context for the AI
2. **Explicit Criteria** - "Consider impact on users"
3. **JSON Output** - Consistent, parseable format
4. **Multi-factor** - Components + history + content

---

## 🎓 AI Models Used

The system tries multiple Claude models in order of preference:

```python
models_list = [
    "claude-opus-4-5-20251101",      # Latest Opus
    "claude-haiku-4-5-20251001",     # Latest Haiku (fast)
    "claude-sonnet-4-5-20250929",    # Latest Sonnet
    "claude-3-5-sonnet-20241022",    # Stable version
    # ... fallbacks ...
]
```

**Characteristics:**
- **Opus:** Most accurate, slower, higher cost
- **Sonnet:** Balanced performance and accuracy
- **Haiku:** Fast, good for simple cases

---

## 📈 Accuracy Factors

### High Accuracy Scenarios ✅

1. **Clear Keywords**
   - "System crash" → Critical
   - "Minor typo" → Low
   - "Can't build" → High

2. **Well-Documented Issues**
   - Reproduction steps
   - Error messages
   - Impact description

3. **Known Components**
   - Matches ROCM_COMPONENTS mapping
   - Similar historical patterns

### Lower Accuracy Scenarios ⚠️

1. **Vague Descriptions**
   - "Something is broken"
   - No steps to reproduce
   - Missing context

2. **Novel Issues**
   - No similar historical issues
   - New feature areas
   - Unclear component

3. **Ambiguous Impact**
   - "Works for me but not others"
   - Configuration-specific
   - Intermittent issues

---

## 🔧 How to Improve Severity Estimation

### For Issue Authors

**Provide clear information:**

```markdown
**Environment:**
- ROCm version: 6.0
- GPU: MI300X
- OS: Ubuntu 22.04

**Impact:**
- Affects: All users on MI300X
- Frequency: Always reproducible
- Workaround: None available

**Steps to Reproduce:**
1. Install ROCm 6.0
2. Run test suite
3. Observe crash in test_xyz

**Expected:** Tests pass
**Actual:** Segmentation fault
```

### For Developers

**Label issues correctly:**
- Add component labels (helps AI)
- Link to similar issues
- Add milestone/priority tags

---

## 📊 Severity Distribution

Typical distribution in a healthy project:

```
Critical: ~5%  (Immediate attention)
High:     ~15% (Next sprint)
Medium:   ~40% (Backlog)
Low:      ~40% (Nice-to-have)
```

If distribution is skewed:
- Too many Critical → Check criteria
- Too many Low → Users may under-report impact

---

## 🎯 Override and Refinement

### Manual Override

Developers can override AI-suggested severity:

1. Review AI analysis
2. Consider organizational priorities
3. Update issue labels
4. Document reasoning

### Feedback Loop

To improve accuracy:
1. Track AI vs. human severity assignments
2. Note patterns where AI is wrong
3. Adjust component mappings
4. Refine prompt if needed

---

## 🧪 Examples

### Example 1: Critical Severity

**Issue:**
```
Title: ROCm 6.0 fails to install on Ubuntu 22.04 - apt error

Body:
After upgrading to ROCm 6.0, apt-get fails with dependency errors.
All users on Ubuntu 22.04 are affected. Cannot install ROCm at all.

Error: Package rocm-core conflicts with rocm-dev
```

**AI Analysis:**
- **Severity:** Critical
- **Reasoning:** Blocks installation for all Ubuntu 22.04 users
- **Component:** base/rocm-core, packaging
- **Fix Priority:** Immediate

### Example 2: Medium Severity

**Issue:**
```
Title: rocBLAS performance 10% slower on specific matrix sizes

Body:
When using rocBLAS with matrices of size 1024x1024, performance is
10% slower compared to ROCm 5.7. Other sizes are fine.

Workaround: Use 1023x1023 or 1025x1025
```

**AI Analysis:**
- **Severity:** Medium
- **Reasoning:** Affects specific case, workaround available
- **Component:** rocm-libraries/rocblas
- **Fix Priority:** Next sprint

### Example 3: Low Severity

**Issue:**
```
Title: Documentation typo in installation guide

Body:
Page says "instal" instead of "install" on line 42
```

**AI Analysis:**
- **Severity:** Low
- **Reasoning:** Cosmetic, doesn't affect functionality
- **Component:** documentation
- **Fix Priority:** Backlog

---

## 🔍 Troubleshooting

### Issue: All Issues Marked as "Medium"

**Possible causes:**
1. Vague issue descriptions
2. AI model fallback (using less capable model)
3. Missing component information

**Solution:**
- Improve issue templates
- Check ANTHROPIC_API_KEY is valid
- Ensure component mapping is accurate

### Issue: Severity Seems Wrong

**Debugging steps:**
1. Check `analysis_summary` field for AI reasoning
2. Review component categorization
3. Check similar issues found
4. Manually verify with `curl` endpoint

```bash
curl -X POST http://localhost:8000/api/analyze/issue/123
```

---

## 📚 Related Documentation

- `ai_analyzer.py` - Implementation details
- `ROCM_COMPONENTS` - Component mapping
- `NEW_FEATURES.md` - Analysis features
- `ARCHITECTURE.md` - System design

---

## 🎉 Summary

**Severity is estimated by:**
1. ✅ Claude AI analyzing issue content
2. ✅ Considering affected ROCm components
3. ✅ Comparing with historical similar issues
4. ✅ Evaluating user impact

**Result:**
- Consistent severity classification
- AI-powered, not rule-based
- Context-aware decisions
- Continuously learning from patterns

**Accuracy:**
- High for well-documented issues
- Improves with better component mapping
- Can be manually overridden
- Provides reasoning for transparency

---

**Last Updated:** January 5, 2026  
**Version:** 2.0.0



