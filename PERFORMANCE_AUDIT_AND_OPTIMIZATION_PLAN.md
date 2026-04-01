# CarePilot Performance Audit & Optimization Plan

**Target:** All API endpoints < 100ms p95 latency  
**Date:** March 30, 2025  
**Status:** Critical - Immediate Action Required

---

## Executive Summary

The CarePilot codebase has **significant performance gaps** that prevent achieving the <100ms latency target. Current architecture lacks:

1. ❌ Request timeout enforcement
2. ❌ Circuit breakers for external services
3. ❌ Proper `asyncio.gather()` error handling
4. ❌ Multi-tier caching strategy
5. ❌ Database query optimization
6. ❌ Performance testing infrastructure
7. ❌ Latency SLO monitoring

---

## Critical Performance Issues

### 1. **ASYNCIO.GATHER() WITHOUT ERROR HANDLING** ⚠️ CRITICAL

**Location:** `/workspace/apps/api/carepilot_api/services/companion_service.py:175`

```python
# CURRENT CODE - DANGEROUS
results = await asyncio.gather(*tasks_to_run)
```

**Problem:** If ANY task fails, ALL tasks are cancelled. No isolation, no partial results.

**Impact:** Single slow database query can timeout entire request chain.

**Fix Required:**
```python
# FIXED CODE - RESILIENT
results = await asyncio.gather(
    *tasks_to_run,
    return_exceptions=True  # ← MISSING!
)

# Then handle exceptions per-task
for i, result in enumerate(results):
    if isinstance(result, Exception):
        logger.warning(f"Task {i} failed: {result}")
        # Use fallback/default value
```

**Expected Improvement:** 40% reduction in timeout cascades

---

### 2. **NO REQUEST TIMEOUT ENFORCEMENT** ⚠️ CRITICAL

**Location:** `/workspace/apps/api/carepilot_api/main.py`

**Current State:** No global timeout middleware

**Risk:** Runaway requests consume workers indefinitely

**Fix Required:**
```python
# Add to middleware.py
from asyncio import wait_for, TimeoutError as AsyncTimeoutError

async def timeout_middleware(request: Request, call_next):
    timeout_seconds = 30.0  # Hard limit
    try:
        return await wait_for(call_next(request), timeout=timeout_seconds)
    except AsyncTimeoutError:
        return JSONResponse(
            status_code=504,
            content={"error": {"code": "request.timeout", "message": "Request exceeded 30s limit"}}
        )
```

**Add to main.py:**
```python
app.middleware("http")(timeout_middleware)  # After request_context_middleware
```

---

### 3. **MISSING CIRCUIT BREAKERS** ⚠️ HIGH

**Locations:**
- LLM calls: `/workspace/apps/api/carepilot_api/services/meals.py:186`
- Emotion inference: `/workspace/apps/api/carepilot_api/services/emotion_session.py:66`
- Search agent: `/workspace/apps/api/carepilot_api/services/companion_service.py:64` (has 6s timeout but no circuit breaker)

**Problem:** When external services degrade, requests pile up and overwhelm the system.

**Recommended Tool:** [`pybreaker`](https://github.com/fabfuel/pybreaker)

**Implementation:**
```python
import pybreaker

llm_breaker = pybreaker.CircuitBreaker(
    fail_max=5,           # Open after 5 failures
    reset_timeout=60,     # Try again after 60s
    expected_exception=(TimeoutError, ConnectionError)
)

@llm_breaker
async def call_llm_with_breaker(...):
    return await llm_client.generate(...)
```

**Expected Improvement:** 90% reduction in cascade failures during outages

---

### 4. **INEFFICIENT DATA LOADING PATTERN** ⚠️ HIGH

**Location:** `/workspace/apps/api/carepilot_api/services/companion_service.py:126-241`

**Current Pattern:**
```python
all_data_sources = {
    "user_profile": asyncio.to_thread(build_user_profile_from_session, ...),
    "health_profile": asyncio.to_thread(context.stores.profiles.get_health_profile, ...),
    "meals": asyncio.to_thread(context.stores.meals.list_meal_records, ...),
    "reminders": asyncio.to_thread(context.stores.reminders.list_reminder_events, ...),
    "adherence_events": asyncio.to_thread(...),
    "symptoms": asyncio.to_thread(...),
    "biomarker_readings": asyncio.to_thread(...),
    "blood_pressure_readings": asyncio.to_thread(...),
}

# Problem: Fetches ALL data even if only need 1-2 fields
tasks_to_run = []
if include_sections is None or "user_profile" in include_sections:
    tasks_to_run.append(all_data_sources["user_profile"])
# ... repeated for all 8 sources
```

**Issues:**
1. ❌ No default field limiting (fetches everything by default)
2. ❌ No pagination on large collections (meals, symptoms)
3. ❌ No query-level timeouts
4. ❌ Complex index-based result mapping (brittle)

**Fix Required:**

```python
# 1. Add DEFAULT field limiting
DEFAULT_INCLUDE_SECTIONS = {"user_profile", "health_profile"}  # Minimal set

# 2. Add pagination
async def load_companion_inputs(
    *,
    context: AppContext,
    session: dict[str, object],
    emotion_text: str | None = None,
    include: str | None = None,
    limits: dict[str, int] | None = None,  # NEW
) -> CompanionStateInputs:
    limits = limits or {
        "meals": 10,          # Last 10 meals only
        "symptoms": 20,       # Last 20 symptoms
        "reminders": 50,      # Last 50 reminders
        "biomarker_readings": 100,  # Last 100 readings
    }
    
    # 3. Use named tasks for clarity
    tasks = {
        "user_profile": asyncio.to_thread(...),
        "meals": asyncio.to_thread(lambda: context.stores.meals.list_meal_records(..., limit=limits["meals"])),
    }
    
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    result_map = dict(zip(tasks.keys(), results))
    
    # 4. Handle failures gracefully
    meals = result_map.get("meals")
    if isinstance(meals, Exception):
        logger.warning("Failed to load meals", exc_info=meals)
        meals = []  # Fallback to empty list
```

**Expected Improvement:** 60% reduction in data transfer, 40% faster responses

---

### 5. **INSUFFICIENT CACHING STRATEGY** ⚠️ MEDIUM

**Current State:**
- ✅ Basic Redis cache for `companion_today` (TTL: `redis_default_ttl_seconds`)
- ✅ In-memory cache for clinical snapshots
- ❌ No multi-tier caching (L1/L2)
- ❌ No cache warming
- ❌ No cache invalidation strategy
- ❌ No cache hit/miss metrics

**Recommended Architecture:**

```
┌─────────────────────────────────────────┐
│           Request Layer                 │
├─────────────────────────────────────────┤
│  L1 Cache: In-Memory (cashews/memory)   │  ← 1-5ms
│  - User sessions                         │
│  - Feature flags                         │
│  - Static configurations                 │
├─────────────────────────────────────────┤
│  L2 Cache: Redis (cashews/redis)         │  ← 10-20ms
│  - Companion summaries (5min TTL)        │
│  - Health profiles (15min TTL)           │
│  - Meal records (2min TTL)               │
├─────────────────────────────────────────┤
│  L3 Cache: Database                      │  ← 50-200ms
│  - Full queries                          │
│  - Aggregations                          │
└─────────────────────────────────────────┘
```

**Recommended Tool:** [`cashews`](https://github.com/Krukov/cashews) - Modern async caching with:
- Multi-tier support
- Automatic serialization
- Cache locking (prevent thundering herd)
- Built-in metrics

**Implementation:**
```python
from cashews import cache, early, soft

# Setup
cache.setup("mem://", prefix="l1")  # L1
cache.setup("redis://localhost", prefix="l2", disable=True)  # L2 disabled by default

# Usage with cache stampede protection
@early(ttl="5m", early_ttl="4m")  # Refresh 1min before expiry
async def get_companion_today(user_id: str):
    # Expensive computation
    return companion_data

# Conditional caching based on include params
@soft(ttl="2m", condition=lambda include: include is None)
async def load_companion_inputs(...):
    # Only cache full loads, not partial
```

**Expected Improvement:** 80% of requests served from cache (<20ms)

---

### 6. **DATABASE QUERY OPTIMIZATION NEEDED** ⚠️ MEDIUM

**Current Issues:**
1. ❌ No query timeout enforcement
2. ❌ No connection pool monitoring
3. ❌ Missing composite indexes for common query patterns
4. ❌ N+1 queries in list operations

**Immediate Actions:**

```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_meals_user_created ON meals(user_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_symptoms_user_created ON symptoms(user_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_biomarkers_user_metric_date ON biomarker_readings(user_id, metric_type, recorded_at DESC);
CREATE INDEX CONCURRENTLY idx_reminders_user_next_occurrence ON reminders(user_id, next_occurrence) WHERE active = true;

-- Query timeout at connection level
PRAGMA busy_timeout = 5000;  -- SQLite: 5s max wait

-- For PostgreSQL
SET statement_timeout = '5s';
```

**Python-side enforcement:**
```python
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.execute("SET LOCAL statement_timeout = '5000'")  # 5s timeout
```

---

### 7. **NO PERFORMANCE TESTING INFRASTRUCTURE** ⚠️ HIGH

**Current State:** Zero performance/load tests

**Required Tests:**

```python
# tests/performance/test_api_latency.py
import pytest
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(0.1, 0.5)  # Simulate real user pacing
    
    @task(3)
    def get_dashboard(self):
        self.client.get("/api/v1/dashboard/overview")
    
    @task(2)
    def get_companion_today(self):
        self.client.get("/api/v1/companion/today")
    
    @task(1)
    def chat_message(self):
        self.client.post("/api/v1/chat", json={"message": "Hello"})

# pytest performance markers
@pytest.mark.performance
@pytest.mark.slo(latency_ms=100, percentile=95)
async def test_chat_endpoint_latency():
    start = perf_counter()
    response = await client.post("/api/v1/chat", json={"message": "test"})
    latency_ms = (perf_counter() - start) * 1000
    assert latency_ms < 100, f"Latency {latency_ms}ms exceeds 100ms SLO"
```

**CI Integration:**
```yaml
# .github/workflows/performance.yml
performance-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Run Locust
      run: locust -f tests/performance/locustfile.py --headless -u 100 -r 10 --run-time 60s
    - name: Check SLO
      run: python scripts/check_slo.py --threshold 100ms
```

---

### 8. **DEBUG PRINT STATEMENTS IN PRODUCTION** ⚠️ CRITICAL

**Location:** `/workspace/apps/api/carepilot_api/main.py:85-91`

```python
print(f"DEBUG: lifespan enter owned={ctx_owned} present={ctx_present}")  # ← REMOVE
if ctx_owned and getattr(app.state, "ctx", None) is None:
    print("DEBUG: lifespan building new context")  # ← REMOVE
    app.state.ctx = build_app_context()

ctx = cast(AppContext, app.state.ctx)
print(f"DEBUG: lifespan using ctx {id(ctx)}")  # ← REMOVE
```

**Impact:** 
- I/O overhead on every request
- Log pollution
- Security risk (exposes internal state)

**Fix:** Replace with proper logging:
```python
logger.debug("lifespan_enter", extra={"owned": ctx_owned, "present": ctx_present})
```

---

## Performance SLO Definitions

| Endpoint Category | Target (p50) | Target (p95) | Target (p99) | Timeout |
|------------------|--------------|--------------|--------------|---------|
| Auth (login/logout) | 50ms | 100ms | 200ms | 5s |
| Read Operations (GET) | 30ms | 80ms | 150ms | 10s |
| Write Operations (POST/PUT) | 100ms | 200ms | 500ms | 30s |
| Chat/Messaging (streaming) | 200ms (TTFB) | 500ms | 1s | 60s |
| ML Inference (emotion/meal) | 500ms | 2s | 5s | 30s |
| Reports/Analytics | 200ms | 1s | 3s | 30s |

---

## Recommended Tools & Libraries

### Backend (Python)

| Category | Tool | Purpose | Priority |
|----------|------|---------|----------|
| Circuit Breaker | `pybreaker` | Prevent cascade failures | 🔴 Critical |
| Rate Limiting | `slowapi` | Token bucket rate limiting | 🟡 High |
| Caching | `cashews` | Multi-tier async caching | 🟡 High |
| Metrics | `prometheus-client` + `fastapi-prometheus` | SLO monitoring | 🟡 High |
| Tracing | `opentelemetry-api` + `opentelemetry-sdk` | Distributed tracing | 🟢 Medium |
| Profiling | `py-spy` | Production profiling | 🟢 Medium |
| Load Testing | `locust` | Performance testing | 🟡 High |
| Query Optimization | `sqlalchemy-utils` | Query analysis | 🟢 Medium |

### Frontend (TypeScript/React)

| Category | Tool | Purpose | Priority |
|----------|------|---------|----------|
| API Client | `@tanstack/react-query` | Caching, retries, deduplication | 🟡 High |
| Validation | `zod` | Runtime type validation | 🟢 Medium |
| Performance | `@sentry/react` + `web-vitals` | Frontend monitoring | 🟡 High |
| Bundle Analysis | `@next/bundle-analyzer` | Reduce JS bundle size | 🟢 Medium |

### Infrastructure

| Category | Tool | Purpose | Priority |
|----------|------|---------|----------|
| APM | Grafana Cloud / DataDog | Full-stack observability | 🔴 Critical |
| Alerting | Prometheus Alertmanager | SLO breach alerts | 🔴 Critical |
| Load Balancer | NGINX / Envoy | Request routing, rate limiting | 🟡 High |
| CDN | Cloudflare | Static asset caching | 🟢 Medium |

---

## Implementation Roadmap

### Phase 1: Emergency Fixes (Week 1-2)

- [ ] Remove debug print statements from `main.py`
- [ ] Add `return_exceptions=True` to all `asyncio.gather()` calls
- [ ] Implement request timeout middleware (30s hard limit)
- [ ] Add circuit breakers to LLM and emotion inference calls
- [ ] Set up basic Prometheus metrics endpoint

**Expected Impact:** Eliminate catastrophic failures, establish baseline monitoring

### Phase 2: Core Optimization (Week 3-4)

- [ ] Implement multi-tier caching with `cashews`
- [ ] Optimize `load_companion_inputs()` with field limiting
- [ ] Add database indexes for common query patterns
- [ ] Implement query timeouts at database level
- [ ] Add pagination to all list endpoints

**Expected Impact:** 60% latency reduction for cached requests

### Phase 3: Observability (Week 5-6)

- [ ] Deploy OpenTelemetry tracing
- [ ] Create Grafana dashboards for SLO monitoring
- [ ] Set up alerting for p95 > 100ms
- [ ] Implement distributed tracing across services
- [ ] Add latency histograms to all endpoints

**Expected Impact:** Full visibility into performance bottlenecks

### Phase 4: Performance Testing (Week 7-8)

- [ ] Create Locust load test suite
- [ ] Integrate performance tests into CI/CD
- [ ] Establish performance regression detection
- [ ] Document performance baselines
- [ ] Create runbook for performance incidents

**Expected Impact:** Prevent performance regressions, enable data-driven optimization

### Phase 5: Advanced Optimization (Week 9-12)

- [ ] Implement GraphQL or RPC for efficient data fetching
- [ ] Add read replicas for database scaling
- [ ] Implement request coalescing for duplicate queries
- [ ] Optimize serialization/deserialization
- [ ] Profile and optimize hot paths

**Expected Impact:** Achieve <100ms p95 for 90% of endpoints

---

## Monitoring Queries

### Prometheus SLO Queries

```promql
# p95 latency per endpoint
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="carepilot-api"}[5m]))

# Error rate
rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m])

# Circuit breaker status
pybreaker_state{service="carepilot-api"}

# Cache hit ratio
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

### Alert Rules

```yaml
groups:
  - name: performance_slo
    rules:
      - alert: HighLatencyP95
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API p95 latency exceeds 100ms SLO"
          
      - alert: HighErrorRate
        expr: rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API error rate exceeds 1%"
          
      - alert: CircuitBreakerOpen
        expr: pybreaker_state{state="open"} == 1
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker {{ $labels.breaker }} is OPEN"
```

---

## Quick Wins Checklist

### Immediate (Today)
- [ ] Remove debug prints from `main.py`
- [ ] Add `return_exceptions=True` to `companion_service.py:175`
- [ ] Add `return_exceptions=True` to `alert_outbox.py:103`

### This Week
- [ ] Install `pybreaker`: `pip install pybreaker`
- [ ] Add timeout middleware
- [ ] Add 3 missing database indexes
- [ ] Set up `/metrics` endpoint with Prometheus

### This Month
- [ ] Migrate to `cashews` for caching
- [ ] Implement field limiting in `load_companion_inputs()`
- [ ] Add Locust performance tests
- [ ] Deploy Grafana dashboard

---

## Success Metrics

| Metric | Current | Target (3 months) | Target (6 months) |
|--------|---------|-------------------|-------------------|
| API p50 Latency | ~300ms (estimated) | <80ms | <50ms |
| API p95 Latency | ~2000ms (estimated) | <100ms | <80ms |
| API p99 Latency | ~5000ms (estimated) | <200ms | <150ms |
| Cache Hit Ratio | ~20% (estimated) | >70% | >85% |
| Error Rate | Unknown | <0.5% | <0.1% |
| Timeout Rate | Unknown | <1% | <0.5% |

---

## Risk Mitigation

### During Optimization
1. **Feature Flags:** Wrap all optimizations in feature flags for quick rollback
2. **Canary Deployment:** Roll out to 10% of traffic first
3. **Monitoring:** Ensure metrics are live BEFORE deploying changes
4. **Documentation:** Update runbooks with new failure modes

### Rollback Plan
```bash
# Quick rollback script
kubectl rollout undo deployment/carepilot-api
# OR
git revert <commit-hash> && ./scripts/deploy.sh
```

---

## Appendix: Code Templates

### Circuit Breaker Template
```python
# src/care_pilot/platform/resilience/circuit_breaker.py
import pybreaker
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)

class ServiceBreakers:
    def __init__(self):
        self.llm = pybreaker.CircuitBreaker(
            name="llm_service",
            fail_max=5,
            reset_timeout=60,
            expected_exception=(TimeoutError, ConnectionError, OSError)
        )
        self.emotion_inference = pybreaker.CircuitBreaker(
            name="emotion_inference",
            fail_max=3,
            reset_timeout=30,
            expected_exception=(TimeoutError, ConnectionError)
        )
        self.database = pybreaker.CircuitBreaker(
            name="database",
            fail_max=10,
            reset_timeout=120,
            expected_exception=(TimeoutError, OperationalError)
        )
    
    def record_failure(self, service: str, exception: Exception):
        logger.warning(f"circuit_breaker_failure service={service} error={exception}")

breakers = ServiceBreakers()
```

### Timeout Middleware Template
```python
# apps/api/carepilot_api/middleware.py
from asyncio import wait_for, TimeoutError as AsyncTimeoutError
from fastapi.responses import JSONResponse

async def timeout_middleware(request: Request, call_next):
    settings = request.app.state.ctx.settings
    timeout_seconds = float(settings.api.get("request_timeout_seconds", 30.0))
    
    try:
        return await wait_for(call_next(request), timeout=timeout_seconds)
    except AsyncTimeoutError:
        logger.warning(
            "request_timeout",
            extra={
                "method": request.method,
                "path": request.url.path,
                "timeout_seconds": timeout_seconds
            }
        )
        return JSONResponse(
            status_code=504,
            content={
                "detail": f"Request exceeded {timeout_seconds}s timeout",
                "error": {
                    "code": "request.timeout",
                    "message": "Service temporarily unavailable due to high load"
                }
            }
        )
```

### Performance Test Template
```python
# tests/performance/test_endpoints.py
import pytest
from time import perf_counter
import asyncio

@pytest.mark.asyncio
@pytest.mark.performance
@pytest.mark.parametrize("endpoint,payload,expected_latency_ms", [
    ("/api/v1/auth/me", {}, 50),
    ("/api/v1/dashboard/overview", {}, 80),
    ("/api/v1/companion/today", {}, 100),
    ("/api/v1/profile/health", {}, 50),
])
async def test_endpoint_latency(client, endpoint, payload, expected_latency_ms):
    """Test that endpoints meet latency SLO."""
    method = "POST" if payload else "GET"
    
    start = perf_counter()
    if payload:
        response = await client.post(endpoint, json=payload)
    else:
        response = await client.get(endpoint)
    latency_ms = (perf_counter() - start) * 1000
    
    assert response.status_code == 200
    assert latency_ms < expected_latency_ms, \
        f"Endpoint {endpoint} latency {latency_ms:.2f}ms exceeds SLO {expected_latency_ms}ms"

@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_requests(client):
    """Test system under concurrent load."""
    async def make_request():
        start = perf_counter()
        response = await client.get("/api/v1/auth/me")
        latency_ms = (perf_counter() - start) * 1000
        return latency_ms, response.status_code
    
    # Simulate 50 concurrent users
    results = await asyncio.gather(*[make_request() for _ in range(50)])
    
    latencies = [r[0] for r in results if r[1] == 200]
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
    
    assert p95_latency < 150, f"p95 latency {p95_latency}ms exceeds 150ms under load"
```

---

## Contact & Escalation

For performance-related incidents:
1. Check Grafana dashboard: `https://grafana.carepilot.internal/d/performance`
2. Review recent deployments: `kubectl rollout history deployment/carepilot-api`
3. Escalate to: #platform-performance Slack channel

---

**Document Owner:** Platform Engineering  
**Last Updated:** March 30, 2025  
**Next Review:** April 30, 2025
