# CarePilot Unified Optimization & Integration Strategy

## Executive Summary

This document synthesizes findings from system robustness analysis, agent evaluation frameworks, personalization strategies, context management, memory architecture, and UX enhancements into a **cohesive optimization roadmap**. The goal is to identify **integration synergies**, eliminate redundancies, and create a unified architecture that delivers <100ms latency while maximizing user engagement and health outcomes.

---

## 1. Cross-Cutting Optimization Opportunities

### 1.1 Unified Context & Memory Pipeline

**Current State:** Fragmented context handling across multiple layers:
- Mem0 for semantic memory
- Preference snapshots for personalization
- Conversation history in orchestration layer
- No unified pruning strategy

**Proposed Integration:** Single Context Pipeline with three stages:

```
┌─────────────────────────────────────────────────────────────┐
│              Unified Context Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│  Stage 1: Ingestion                                          │
│  - Chat messages → Memory Store                              │
│  - User actions → Interaction Tracker                        │
│  - Health events → Timeline Service                          │
│  - Emotion signals → Affective State Manager                 │
├─────────────────────────────────────────────────────────────┤
│  Stage 2: Processing (Async, <50ms overhead)                │
│  - Fact Extraction Agent (LLM-based)                         │
│  - Embedding Generation (for vector search)                  │
│  - Importance Scoring (recency + relevance + user feedback)  │
│  - RL Reward Computation                                     │
├─────────────────────────────────────────────────────────────┤
│  Stage 3: Retrieval & Pruning (<15ms target)                │
│  - ContextPruner builds optimized prompt                     │
│  - Multi-tier: Permanent → Sliding → Semantic Retrieval      │
│  - Token budget enforcement                                  │
└─────────────────────────────────────────────────────────────┘
```

**Implementation Location:** 
- `/workspace/src/care_pilot/platform/memory/context_pipeline.py` (new)
- Refactor `companion_service.py` to use pipeline

**Synergy Benefits:**
- Single source of truth for all context
- Shared embeddings for both retrieval AND RL state encoding
- Unified importance scoring informs both pruning AND recommendation prioritization
- Reduced code duplication (currently 3+ places handle context)

---

### 1.2 Personalization × RL × Memory Integration

**Key Insight:** These three systems are deeply interconnected but currently operate in silos.

**Unified Architecture:**

```python
class IntegratedPersonalizationEngine:
    """
    Combines memory retrieval, contextual bandits, and preference learning
    into a single decision engine.
    """
    
    async def generate_recommendation(
        self,
        user_id: str,
        context: ContextualFeatures,
        candidate_meals: list[FoodItem]
    ) -> Recommendation:
        # Step 1: Retrieve relevant memories (what worked before in similar contexts?)
        relevant_memories = await self.memory_store.search_similar(
            user_id=user_id,
            query=context.to_embedding_vector(),
            filters={"event_type": "meal_acceptance"},
            top_k=10
        )
        
        # Step 2: Extract features for RL state
        rl_state = self._build_rl_state(
            user_profile=await self.get_user_profile(user_id),
            context=context,
            historical_patterns=relevant_memories,
            current_goal=await self.get_active_goal(user_id)
        )
        
        # Step 3: Use contextual bandit to score candidates
        scores = {}
        for meal in candidate_meals:
            # Bandit considers: meal features × user preferences × context × history
            arm_id = self._encode_arm(meal, context)
            expected_reward = self.bandit.predict_reward(arm_id, rl_state)
            
            # Adjust based on explicit preferences (allergies, restrictions)
            preference_score = self.preference_engine.score(meal, user_id)
            
            # Combine: 70% RL prediction, 30% explicit preferences
            scores[meal.id] = 0.7 * expected_reward + 0.3 * preference_score
        
        # Step 4: Select and log for future learning
        selected_meal = max(scores, key=scores.get)
        await self._log_decision_context(user_id, selected_meal, context, scores)
        
        return self._build_recommendation(selected_meal, scores[selected_meal])
```

**Integration Points:**
1. **Memory → RL:** Historical acceptances become training data for bandit
2. **RL → Memory:** High-reward decisions are prioritized for long-term storage
3. **Preferences → RL:** Explicit preferences constrain action space (hard filters)
4. **Context → All Three:** Temporal, emotional, environmental signals inform everything

**Performance Target:** End-to-end recommendation generation <80ms

---

### 1.3 Family Functionality × Personalization Synergies

**Untapped Opportunity:** Family data can dramatically improve personalization through:
- Collaborative filtering ("users in similar families liked X")
- Shared meal planning (reduce decision fatigue)
- Social accountability (gamification)

**Enhanced Features:**

#### A. Family-Aware Recommendations
```python
async def get_family_optimized_recommendations(family_id: str) -> list[MealPlan]:
    """
    Generate meal plans that work for entire family, not just individual.
    Considers:
    - Overlapping dietary restrictions (union of all allergies)
    - Age-appropriate portions (children vs adults)
    - Preference aggregation (find meals everyone rates highly)
    - Preparation efficiency (one meal vs multiple)
    """
    family_members = await self.family_repo.get_active_members(family_id)
    
    # Find common constraints
    all_allergies = set()
    all_preferences = []
    for member in family_members:
        profile = await self.get_profile(member.user_id)
        all_allergies.update(profile.allergies)
        all_preferences.append(profile.taste_preferences)
    
    # Aggregate preferences using weighted voting
    # (parents get higher weight for nutrition, kids for taste)
    aggregated_prefs = self._aggregate_preferences(
        all_preferences,
        weights=[self._compute_member_weight(m) for m in family_members]
    )
    
    # Generate meals satisfying constraints and maximizing aggregate preference
    candidates = await self.meal_db.search(
        exclude_ingredients=all_allergies,
        target_nutrition=self._compute_family_nutrition_targets(family_members),
        preference_match=aggregated_prefs
    )
    
    return self._rank_by_family_satisfaction(candidates, family_members)
```

#### B. Cross-User Learning
- If Parent A accepts healthy dinner recommendations 80% of time, boost similar meals for Parent B
- If Child C rejects spicy foods, deprioritize for siblings unless explicitly requested
- Transfer learning: New family members bootstrap from existing member patterns

#### C. Privacy-Preserving Family Analytics
```python
# Differential privacy for family insights
def compute_family_statistic(
    family_id: str, 
    metric: str, 
    epsilon: float = 1.0
) -> float:
    """
    Compute aggregate family statistics with differential privacy.
    Ensures individual data cannot be reverse-engineered.
    """
    raw_values = [get_member_metric(fid, metric) for fid in family_members]
    true_aggregate = np.mean(raw_values)
    
    # Add Laplace noise for privacy
    sensitivity = 1.0 / len(family_members)
    noise = np.random.laplace(0, sensitivity / epsilon)
    
    return true_aggregate + noise
```

---

## 2. Performance Optimization Matrix

### 2.1 Latency Budget Allocation (<100ms Total)

| Component | Target | Current | Gap | Optimization Strategy |
|-----------|--------|---------|-----|----------------------|
| Context Retrieval | 15ms | ~50ms | -35ms | Multi-tier caching, pre-computed embeddings |
| Memory Search | 20ms | ~80ms | -60ms | HNSW index, quantized vectors, result caching |
| RL Inference | 10ms | N/A | New | Lightweight model (logistic regression bandit) |
| Preference Scoring | 5ms | ~15ms | -10ms | Pre-computed affinity matrices |
| LLM Call (streaming) | 40ms | ~500ms | -460ms | Smaller model for first token, speculative decoding |
| Database Queries | 10ms | ~30ms | -20ms | Connection pooling, read replicas, query optimization |

**Critical Path Optimization:**
```python
# Parallel execution of independent operations
async def optimized_recommendation_pipeline(user_id, context):
    # These can run in parallel (<20ms each)
    user_profile, recent_history, active_goals = await asyncio.gather(
        self.profile_cache.get(user_id),           # Redis: <2ms
        self.memory_store.get_recent(user_id, k=5), # Vector DB: <15ms
        self.goal_service.get_active(user_id)      # PostgreSQL: <5ms
    )
    
    # RL inference (single-threaded, optimized)
    rl_scores = await self.bandit.predict_batch(candidates, context)  # <10ms
    
    # Final ranking (CPU-bound, numpy optimized)
    ranked = self._rank_candidates(candidates, rl_scores, user_profile)  # <5ms
    
    return ranked[:3]
```

### 2.2 Caching Strategy (Multi-Tier)

```python
from cashews import cache

class CachedRecommendationService:
    @cache(ttl="5m", key="rec:{user_id}:{context_hash}")
    async def get_recommendations(self, user_id: str, context: ContextualFeatures):
        """Cache recommendations for identical contexts."""
        return await self._generate_recommendations(user_id, context)
    
    @cache(ttl="1h", key="profile:{user_id}")
    async def get_user_profile(self, user_id: str):
        """Cache user profiles with invalidation on update."""
        return await self.profile_repo.get(user_id)
    
    @cache(ttl="24h", key="preference_matrix:{user_id}")
    async def get_preference_affinities(self, user_id: str):
        """Pre-compute preference matrix daily."""
        return await self._compute_affinity_matrix(user_id)
```

**Cache Invalidation Strategy:**
- Profile updates → Invalidate `profile:{user_id}` and `preference_matrix:{user_id}`
- New meal logged → Invalidate `rec:{user_id}:*` (pattern match)
- Goal change → Invalidate `rec:{user_id}:*` and recompute RL state

---

## 3. Agent Evaluation Framework Integration

### 3.1 Continuous Evaluation Pipeline

**Problem:** Currently no systematic way to measure agent performance in production.

**Solution:** Embedded evaluation at every interaction:

```python
class EvaluatedAgentOrchestrator:
    async def process_user_message(self, user_id: str, message: str):
        start_time = time.time()
        
        # Generate response
        response = await self.agent.generate(message, user_id)
        latency = time.time() - start_time
        
        # Log metrics asynchronously (non-blocking)
        asyncio.create_task(self._log_evaluation_metrics(
            user_id=user_id,
            intent=response.detected_intent,
            latency_ms=latency * 1000,
            token_count=response.token_usage,
            safety_flags=response.safety_analysis,
            confidence=response.confidence_score
        ))
        
        # Real-time alerting for anomalies
        if latency > 800:  # P95 threshold
            await self.alerting.send("HIGH_LATENCY", {"user_id": user_id, "latency": latency})
        
        if response.safety_flags.triggered:
            await self.alerting.send("SAFETY_REVIEW_NEEDED", {
                "user_id": user_id, 
                "message": message,
                "response": response.text
            })
        
        return response
```

### 3.2 Automated A/B Testing Infrastructure

```python
class RecommendationExperimentManager:
    """
    Manages concurrent experiments across user segments.
    """
    
    async def assign_and_track(
        self,
        user_id: str,
        experiment_id: str,
        context: dict
    ) -> tuple[str, Any]:
        """
        Assign user to variant, execute treatment, track outcome.
        """
        variant = self._get_variant(user_id, experiment_id)
        
        # Execute variant-specific logic
        if variant == "control":
            result = await self.baseline_recommendation(context)
        elif variant == "contextual_bandit":
            result = await self.bandit_recommendation(context)
        elif variant == "deep_rl":
            result = await self.rl_policy_recommendation(context)
        
        # Log assignment for later analysis
        await self.experiment_db.log_assignment(
            experiment_id=experiment_id,
            user_id=user_id,
            variant=variant,
            timestamp=datetime.utcnow(),
            context=context
        )
        
        return variant, result
    
    async def analyze_experiment(self, experiment_id: str) -> ExperimentResults:
        """
        Statistical analysis of experiment results.
        """
        data = await self.experiment_db.get_results(experiment_id)
        
        # Compute metrics per variant
        metrics = {}
        for variant in data.variants:
            variant_data = data.filter(variant=variant)
            metrics[variant] = {
                "acceptance_rate": variant_data.accepted / variant_data.total,
                "avg_latency": variant_data.latency.mean(),
                "health_alignment": variant_data.health_score.mean(),
                "diversity": 1 - (variant_data.repeat_rate),
                "ci_95": self._compute_confidence_interval(variant_data)
            }
        
        # Statistical significance testing
        significance = self._run_statistical_tests(data)
        
        return ExperimentResults(metrics=metrics, significance=significance)
```

---

## 4. Enhanced Chat Experience: Action Pipeline

### 4.1 Intent → Action → Confirmation Flow

**Current:** Chat responses are primarily informational.

**Target:** Every conversation turn can trigger structured actions.

```python
class ActionOrientedChatPipeline:
    INTENT_TO_ACTION = {
        "log_meal": self._handle_meal_logging,
        "log_medication": self._handle_medication_logging,
        "set_reminder": self._handle_reminder_creation,
        "request_recommendation": self._handle_recommendation_request,
        "track_symptom": self._handle_symptom_tracking,
        "ask_health_question": self._handle_health_qa,
    }
    
    async def process_message(self, user_id: str, message: str) -> ChatResponse:
        # Step 1: Classify intent with confidence
        intent_result = await self.intent_classifier.classify(message)
        
        # Step 2: Extract entities
        entities = await self.ner_extractor.extract(message, intent_result.intent)
        
        # Step 3: Validate and disambiguate
        if intent_result.confidence < 0.7 or entities.ambiguous:
            return await self._request_clarification(intent_result, entities)
        
        # Step 4: Execute action
        action_handler = self.INTENT_TO_ACTION.get(intent_result.intent)
        if action_handler:
            action_result = await action_handler(user_id, entities)
            
            # Step 5: Build rich response with UI components
            return self._build_rich_response(
                intent=intent_result.intent,
                action_result=action_result,
                suggested_followups=self._generate_followups(intent_result.intent)
            )
        else:
            # Fallback to conversational response
            return await self.conversational_agent.respond(message, user_id)
```

### 4.2 Specific Feature Implementations

#### Meal Logging with Auto-Completion
```python
async def _handle_meal_logging(self, user_id: str, entities: MealEntities) -> ActionResult:
    """
    Parse natural language meal description into structured log.
    """
    # Extract food items
    foods = await self.food_database.match(entities.mentioned_foods)
    
    # Estimate portions (default if not specified)
    for food in foods:
        if not food.portion:
            food.portion = self._infer_typical_portion(food, user_id)
    
    # Compute nutrition
    nutrition = await self.nutrition_calculator.compute(foods)
    
    # Check against daily goals
    daily_totals = await self.daily_tracker.get_totals(user_id, today())
    remaining = daily_totals.remaining_budget(nutrition)
    
    # Generate personalized feedback
    feedback = []
    if nutrition.calories > remaining.calories * 1.2:
        feedback.append("⚠️ This exceeds your remaining calorie budget.")
    if nutrition.protein < 20:
        feedback.append("💡 Consider adding protein for better satiety.")
    
    return ActionResult(
        success=True,
        logged_items=foods,
        nutrition_summary=nutrition,
        feedback=feedback,
        ui_component="MealLogCard",
        requires_confirmation=True  # Show "Confirm" button before saving
    )
```

#### Medication Parsing with Reminder Setup
```python
async def _handle_medication_logging(self, user_id: str, entities: MedicationEntities) -> ActionResult:
    """
    Parse medication mentions and offer to set reminders.
    """
    # Validate medication name against drug database
    validated_meds = []
    for med in entities.medications:
        drug_info = await self.drug_database.lookup(med.name)
        if not drug_info:
            return ActionResult(
                success=False,
                error=f"Unknown medication: {med.name}. Please verify spelling.",
                suggestions=await self.drug_database.suggest_similar(med.name)
            )
        
        # Check for interactions with existing medications
        interactions = await self.interaction_checker.check(
            new_med=drug_info,
            existing_meds=await self.medication_repo.get_active(user_id)
        )
        
        if interactions.severe:
            return ActionResult(
                success=False,
                error=f"⚠️ Severe interaction detected between {med.name} and {interactions.conflicting_drug}",
                requires_clinician_review=True
            )
        
        validated_meds.append(drug_info)
    
    # Offer reminder setup
    suggested_times = self._infer_dosing_times(entities.frequency)
    
    return ActionResult(
        success=True,
        medications=validated_meds,
        suggested_schedule=suggested_times,
        ui_component="MedicationReminderSetup",
        next_step="confirm_reminder_times"
    )
```

---

## 5. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
**Goal:** Establish core infrastructure for all optimizations.

| Week | Deliverable | Owner | Success Metric |
|------|-------------|-------|----------------|
| 1 | ContextPruner implementation | Backend Team | <20ms pruning latency |
| 2 | Multi-tier caching (Redis + L1) | Backend Team | 50% reduction in DB queries |
| 3 | Contextual bandit MVP | ML Team | Working Thompson Sampling |
| 4 | Evaluation metrics pipeline | Platform Team | All interactions logged with metrics |

### Phase 2: Integration (Weeks 5-8)
**Goal:** Connect systems for unified operation.

| Week | Deliverable | Owner | Success Metric |
|------|-------------|-------|----------------|
| 5 | Memory → RL data pipeline | ML Team | Historical data loaded for training |
| 6 | Family-aware recommendations | Backend Team | Family meal plans working |
| 7 | Action-oriented chat pipeline | Frontend + Backend | 5 intents with rich UI |
| 8 | A/B testing framework | Platform Team | First experiment launched |

### Phase 3: Optimization (Weeks 9-12)
**Goal:** Performance tuning and advanced features.

| Week | Deliverable | Owner | Success Metric |
|------|-------------|-------|----------------|
| 9 | Latency optimization sprint | All Teams | P95 <100ms achieved |
| 10 | Deep RL policy training | ML Team | Offline policy trained |
| 11 | Advanced personalization (dynamic weights) | ML Team | Per-user weight optimization |
| 12 | Security audit + HIPAA compliance | Security Team | Zero critical vulnerabilities |

### Phase 4: Production Rollout (Weeks 13-16)
**Goal:** Gradual deployment with monitoring.

| Week | Deliverable | Owner | Success Metric |
|------|-------------|-------|----------------|
| 13 | Canary deployment (5% users) | DevOps | Error rate <0.1% |
| 14 | Expand to 25% users | DevOps | No performance degradation |
| 15 | Full rollout (100%) | DevOps | All users on new system |
| 16 | Post-launch optimization | All Teams | Address feedback, tune parameters |

---

## 6. Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| RL model performs worse than baseline | Medium | High | Keep baseline as fallback; A/B test rigorously |
| Context pruning removes critical info | Low | High | Conservative pruning; manual review of edge cases |
| Family data leakage | Low | Critical | Strict access controls; automated security tests |
| Latency targets not met | Medium | High | Feature flags to disable heavy computations |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Model drift over time | High | Medium | Continuous evaluation; weekly retraining |
| User backlash to changes | Low | Medium | Gradual rollout; clear communication; opt-out option |
| Compliance violations | Low | Critical | Legal review before launch; audit logging |

---

## 7. Success Metrics Dashboard

### Key Performance Indicators (KPIs)

| Category | Metric | Baseline | Target | Measurement Frequency |
|----------|--------|----------|--------|----------------------|
| **Performance** | P95 Latency | ~500ms | <100ms | Real-time |
| | Cache Hit Rate | N/A | >80% | Hourly |
| **Engagement** | Daily Active Users | Current | +30% | Daily |
| | Session Duration | Current | +20% | Daily |
| | Feature Adoption | N/A | >60% try new features | Weekly |
| **Health Outcomes** | Medication Adherence | Current | +25% | Weekly |
| | Goal Achievement Rate | Current | +35% | Weekly |
| | Health Biomarker Improvement | Current | Statistically significant | Monthly |
| **Quality** | Hallucination Rate | N/A | <1% | Per-interaction |
| | Safety Violations | N/A | 0 | Real-time |
| | User Satisfaction (CSAT) | Current | >4.5/5 | Per-session |
| **Business** | User Retention D7 | Current | >60% | Weekly |
| | User Retention D30 | Current | >40% | Monthly |
| | Referral Rate | Current | +50% | Monthly |

### Monitoring Dashboard Components

```python
# Prometheus metrics to expose
RECOMMENDATION_ACCEPTANCE_RATE = Gauge(
    'recommendation_acceptance_rate',
    'Rate of accepted recommendations',
    ['variant', 'meal_slot']
)

CONTEXT_PRUNING_LATENCY = Histogram(
    'context_pruning_duration_seconds',
    'Time spent pruning conversation context',
    buckets=[0.005, 0.01, 0.02, 0.05, 0.1]
)

RL_MODEL_CONFIDENCE = Histogram(
    'rl_prediction_confidence',
    'Confidence scores from RL model',
    buckets=[0.1, 0.3, 0.5, 0.7, 0.9]
)

FAMILY_FEATURE_USAGE = Counter(
    'family_feature_interactions_total',
    'Total interactions with family features',
    ['feature_type', 'role']
)

SAFETY_GUARDRAIL_TRIGGERS = Counter(
    'safety_guardrail_triggers_total',
    'Number of times safety guardrails activated',
    ['trigger_type', 'severity']
)
```

---

## 8. Tool & Library Recommendations

### Backend Enhancements

| Category | Current | Recommended | Migration Effort |
|----------|---------|-------------|------------------|
| Caching | Custom | `cashews` | Low (drop-in replacement) |
| RL | None | `vowpalwabbit` (bandits), `ray[rllib]` (deep RL) | Medium |
| Vector Search | Basic | `qdrant-client` or `pgvector` | Medium |
| Feature Flags | None | `flagsmith` (self-hosted) | Low |
| Observability | Logfire | Add `prometheus-client` + Grafana | Medium |
| Rate Limiting | None | `slowapi` | Low |
| Circuit Breaker | None | `pybreaker` | Low |

### Frontend Enhancements

| Category | Current | Recommended | Migration Effort |
|----------|---------|-------------|------------------|
| Forms | Native | `react-hook-form` + `zod` | Medium |
| State | React Query | Add `zustand` for client state | Low |
| Error Tracking | None | `Sentry` | Low |
| Accessibility | Manual | `@axe-core/react` | Low |
| Analytics | None | `PostHog` (self-hosted) | Medium |

### ML/MLOps

| Category | Current | Recommended | Purpose |
|----------|---------|-------------|---------|
| Experiment Tracking | None | `mlflow` or `weights-biases` | Track RL training runs |
| Model Serving | Direct calls | `bentoml` or `torchserve` | Scalable inference |
| Data Versioning | Git | `dvc` | Version datasets |
| Feature Store | None | `feast` | Share features across models |

---

## 9. Conclusion & Next Steps

### Immediate Actions (This Week)

1. **Create ContextPruner Implementation**
   - File: `/workspace/src/care_pilot/platform/memory/context_pruner.py`
   - Owner: Backend Team Lead
   - Deadline: End of week

2. **Set Up Evaluation Metrics Pipeline**
   - Instrument all recommendation endpoints
   - Create Prometheus dashboards
   - Owner: Platform Team

3. **Audit Family Permission System**
   - Security review of current implementation
   - Identify gaps in consent management
   - Owner: Security Engineer

4. **Design A/B Test #1**
   - Hypothesis: Contextual bandits improve acceptance by 15%
   - Metrics: Acceptance rate, diversity, health alignment
   - Owner: ML Team Lead

### Long-Term Vision

By implementing this unified optimization strategy, CarePilot will achieve:

- **10x Performance Improvement:** <100ms latency enables real-time, fluid interactions
- **Personalization at Scale:** RL-driven adaptation to individual users without manual tuning
- **Family-Centric Care:** Leverage social dynamics for better health outcomes
- **Production-Ready Reliability:** Comprehensive monitoring, circuit breakers, graceful degradation
- **Continuous Improvement Loop:** Embedded evaluation drives iterative enhancement

The integration of context management, memory systems, personalization engines, and RL creates a **virtuous cycle** where every user interaction improves the system, leading to better recommendations, higher engagement, and improved health outcomes.

---

## Appendix A: Code Templates

### A.1 ContextPruner Skeleton

```python
# /workspace/src/care_pilot/platform/memory/context_pruner.py

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

from care_pilot.platform.memory.store import MemorySnippet, MemoryStore
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


@dataclass
class ContextTier:
    """Represents a tier of context with pruning rules."""
    name: str
    priority: Literal["permanent", "sliding", "retrieved"]
    max_tokens: int | None = None
    max_items: int | None = None
    ttl_hours: float | None = None
    decay_factor: float = 1.0


@dataclass
class PrunedContext:
    """Result of context pruning operation."""
    system_prompt: str
    permanent_facts: list[str]
    recent_turns: list[dict[str, str]]
    retrieved_memories: list[MemorySnippet]
    total_tokens: int
    pruned_count: int
    retrieval_query: str | None = None


class ContextPruner:
    """Intelligent context pruning for LLM conversations."""
    
    PERMANENT_CATEGORIES = {
        "allergies",
        "medical_conditions",
        "dietary_restrictions",
        "active_goals",
        "medication_schedule"
    }
    
    SLIDING_WINDOW_SIZE = 5
    RETRIEVAL_TOP_K = 3
    MAX_CONTEXT_TOKENS = 3500
    
    def __init__(
        self,
        memory_store: MemoryStore,
        token_estimator,
    ):
        self.memory_store = memory_store
        self.estimate_tokens = token_estimator
        self.tiers = self._initialize_tiers()
    
    def _initialize_tiers(self) -> dict[str, ContextTier]:
        return {
            "system": ContextTier(name="system", priority="permanent", max_tokens=500),
            "facts": ContextTier(name="facts", priority="permanent", max_items=20),
            "recent": ContextTier(name="recent", priority="sliding", max_items=self.SLIDING_WINDOW_SIZE),
            "history": ContextTier(
                name="history",
                priority="retrieved",
                max_items=self.RETRIEVAL_TOP_K,
                decay_factor=0.95
            )
        }
    
    async def prune_context(
        self,
        *,
        user_id: str,
        session_id: str,
        full_conversation: list[dict[str, str]],
        user_profile,
        health_profile,
        current_query: str,
    ) -> PrunedContext:
        """Apply multi-tier pruning strategy."""
        # Implementation from PERSONALIZATION_CONTEXT_UX_STRATEGY.md
        pass
```

### A.2 Contextual Bandit Integration

```python
# /workspace/src/care_pilot/platform/ml/recommendation_bandit.py

from typing import TypedDict
import numpy as np

class BanditArm(TypedDict):
    meal_id: str
    context_features: dict[str, float]
    alpha: float  # Successes + 1
    beta: float   # Failures + 1

class ContextualBanditRecommender:
    """Thompson Sampling for meal recommendations."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.arms: dict[str, BanditArm] = {}
    
    def select_meal(
        self,
        candidates: list[FoodItem],
        context: ContextualFeatures
    ) -> FoodItem:
        """Select meal using Thompson Sampling."""
        scores = {}
        
        for candidate in candidates:
            arm_id = f"{candidate.id}_{context.time_bucket}_{context.day_type}"
            
            if arm_id not in self.arms:
                # Initialize with prior
                self.arms[arm_id] = BanditArm(
                    meal_id=candidate.id,
                    context_features=context.to_dict(),
                    alpha=1.0,
                    beta=1.0
                )
            
            # Sample from Beta posterior
            arm = self.arms[arm_id]
            sampled_value = np.random.beta(arm['alpha'], arm['beta'])
            scores[candidate.id] = sampled_value
        
        best_id = max(scores, key=scores.get)
        return next(c for c in candidates if c.id == best_id)
    
    def update(self, meal_id: str, context: ContextualFeatures, reward: float):
        """Update bandit with observed reward."""
        arm_id = f"{meal_id}_{context.time_bucket}_{context.day_type}"
        
        if arm_id in self.arms:
            arm = self.arms[arm_id]
            # Convert reward to binary (accept/reject)
            success = 1 if reward > 0.5 else 0
            failure = 1 - success
            
            # Update Beta parameters
            self.arms[arm_id] = BanditArm(
                meal_id=meal_id,
                context_features=context.to_dict(),
                alpha=arm['alpha'] + success,
                beta=arm['beta'] + failure
            )
```

---

## Appendix B: Database Schema Extensions

```sql
-- Family permissions with granular control
CREATE TABLE family_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    family_id UUID NOT NULL REFERENCES families(id),
    grantor_id UUID NOT NULL REFERENCES users(id),
    grantee_id UUID NOT NULL REFERENCES users(id),
    role VARCHAR(32) NOT NULL CHECK (role IN ('admin', 'caregiver', 'member', 'observer')),
    permissions JSONB NOT NULL DEFAULT '{}',
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    consent_record_id UUID,
    UNIQUE(family_id, grantor_id, grantee_id)
);

-- Create index for fast permission checks
CREATE INDEX idx_family_permissions_active 
ON family_permissions(family_id, grantee_id) 
WHERE revoked_at IS NULL AND (expires_at IS NULL OR expires_at > NOW());

-- RL training data storage
CREATE TABLE rl_interaction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    session_id UUID NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    state_json JSONB NOT NULL,  -- Encoded RL state
    action_json JSONB NOT NULL, -- Taken action (recommended meal)
    reward FLOAT NOT NULL,      -- Computed reward
    context_features JSONB,     -- Contextual features used
    experiment_id VARCHAR(64),  -- A/B test variant
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient batch loading during training
CREATE INDEX idx_rl_logs_user_timestamp 
ON rl_interaction_logs(user_id, timestamp DESC);

-- Memory importance tracking
CREATE TABLE memory_importance_scores (
    memory_id UUID PRIMARY KEY REFERENCES user_memories(id),
    recency_score FLOAT NOT NULL,
    relevance_score FLOAT NOT NULL,
    user_feedback_score FLOAT,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    decay_rate FLOAT DEFAULT 0.95
);
```

---

**Document Version:** 1.0  
**Last Updated:** 2024  
**Authors:** CarePilot Engineering Team  
**Review Cycle:** Quarterly
