# API Contract: Adaptive Recommendation Agent

## Summary
The adaptive recommendation agent layers behavior-aware meal ranking on top of:
- persisted health profile data
- recent meal logs
- biomarker snapshot context
- online interaction learning

It keeps the existing deterministic daily suggestions flow as a fallback surface, but adds:
- a typed daily agent feed
- healthier substitution planning
- interaction capture for continual reranking

## Endpoints

### `GET /api/v1/recommendations/daily-agent`
Returns the current adaptive meal feed for the authenticated user.

#### Auth / policy action
- route action: `recommendations.daily_agent.read`
- required scope: `recommendation:generate`

#### Response shape
```json
{
  "profile_state": {
    "completeness_state": "ready",
    "bmi": 27.99,
    "target_calories_per_day": 1850,
    "macro_focus": ["higher_protein", "lower_sugar"]
  },
  "temporal_context": {
    "current_slot": "lunch",
    "generated_at": "2026-02-28T00:00:00+00:00",
    "meal_history_count": 10,
    "interaction_count": 5,
    "recent_repeat_titles": ["Laksa", "Char kway teow"],
    "slot_history_counts": {"breakfast": 3, "lunch": 4, "dinner": 3}
  },
  "recommendations": {
    "breakfast": {
      "candidate_id": "sg.breakfast.soft_boiled_eggs_toast",
      "slot": "breakfast",
      "title": "Soft-boiled eggs with wholemeal toast",
      "venue_type": "kopitiam",
      "why_it_fits": ["Matches your usual breakfast pattern."],
      "caution_notes": [],
      "confidence": 0.84,
      "scores": {
        "preference_fit": 0.78,
        "temporal_fit": 0.91,
        "adherence_likelihood": 0.82,
        "health_gain": 0.63,
        "substitution_deviation_penalty": 0.22,
        "total_score": 0.75
      },
      "health_gain_summary": {
        "calories": -80,
        "sugar_g": -4,
        "sodium_mg": -120
      }
    }
  },
  "substitutions": {
    "source_meal": {
      "meal_id": "meal_10",
      "title": "Thunder tea rice",
      "slot": "lunch"
    },
    "alternatives": []
  },
  "fallback_mode": false,
  "data_sources": {
    "meal_history_count": 10,
    "interaction_count": 5,
    "has_preference_snapshot": true,
    "has_clinical_snapshot": true
  },
  "constraints_applied": ["excluded_high_sodium"],
  "workflow": {
    "workflow_name": "daily_recommendation_agent",
    "request_id": "uuid",
    "correlation_id": "uuid",
    "replayed": false,
    "timeline_events": []
  }
}
```

#### Notes
- `fallback_mode=true` means the agent is still in cold-start/warm-up and relies more heavily on deterministic heuristics.
- `substitutions` may be `null` when no current source meal is available.
- Safety and restriction filtering remains hard-blocking even when preference fit is high.

### `POST /api/v1/recommendations/substitutions`
Returns lower-deviation healthier alternatives for a source meal.

#### Auth / policy action
- route action: `recommendations.substitutions.generate`
- required scope: `recommendation:generate`

#### Request
```json
{
  "source_meal_id": "meal_3",
  "limit": 2
}
```

#### Response
```json
{
  "source_meal": {
    "meal_id": "meal_3",
    "title": "Char kway teow",
    "slot": "dinner"
  },
  "alternatives": [
    {
      "candidate_id": "sg.dinner.yong_tau_foo_clear_soup",
      "title": "Yong tau foo clear soup with tofu and greens",
      "venue_type": "hawker",
      "health_delta": {
        "calories": -280,
        "sugar_g": -5,
        "sodium_mg": -900
      },
      "taste_distance": 0.43,
      "reasoning": "A healthier swap that preserves a familiar savory local profile.",
      "confidence": 0.78
    }
  ],
  "blocked_reason": null
}
```

### `POST /api/v1/recommendations/interactions`
Records user feedback for continual online reranking.

#### Auth / policy action
- route action: `recommendations.interactions.write`
- required scope: `recommendation:generate`

#### Request
```json
{
  "recommendation_id": "uuid",
  "candidate_id": "sg.breakfast.soft_boiled_eggs_toast",
  "event_type": "accepted",
  "slot": "breakfast",
  "metadata": {
    "surface": "dashboard_agent"
  }
}
```

#### Supported `event_type`
- `viewed`
- `accepted`
- `dismissed`
- `swap_selected`
- `meal_logged_after_recommendation`
- `ignored`

#### Response
```json
{
  "ok": true,
  "interaction": {
    "interaction_id": "uuid",
    "user_id": "user_001",
    "candidate_id": "sg.breakfast.soft_boiled_eggs_toast",
    "event_type": "accepted"
  },
  "preference_snapshot": {
    "interaction_count": 6,
    "accepted_count": 4,
    "substitution_tolerance": 0.58
  }
}
```

## Fallback and Safety Semantics
- The agent does not require a fully complete profile to return a result.
- Fresh users with sparse meal history still receive a typed response with `fallback_mode=true`.
- Allergen, restriction, budget, sugar, sodium, and safety violations can exclude a candidate before ranking.

## Related Docs
- `docs/api-suggestions-contract.md`
- `docs/rbac-matrix.md`
- `docs/operations-runbook.md`
