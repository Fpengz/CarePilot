# Observability Map

## Request Context Contract
- Incoming headers: `X-Request-ID`, `X-Correlation-ID`
- Middleware responsibilities:
  - Populate `request.state.request_id` and `request.state.correlation_id`
  - Echo both headers in every API response
  - Emit `event=api_request_complete` with method/path/status/duration
  - Optionally emit `event=api_request_started` and `event=api_response_headers` in dev (config-driven)

## Propagation Paths
- API routes:
  - Health profile read/update
  - Deterministic daily suggestions
  - Suggestions generate/list/detail
  - Meal analyze/records
  - Alerts trigger/timeline
  - Recommendations generate
  - Recommendations daily-agent / substitutions / interactions
- Application/workflow services:
  - Suggestions workflow payload (`workflow.request_id`, `workflow.correlation_id`)
  - Meal capture/workflow timeline events
  - Alert workflow timeline events
- Error handlers:
  - Standard envelope with `error.correlation_id`
  - Failure log event `event=api_request_failed`

## Logging Schema
- Success event keys:
  - `event`, `method`, `path`, `status_code`, `request_id`, `correlation_id`, `duration_ms`, `header_contract`
- Failure event keys:
  - `event`, `method`, `path`, `status_code`, `error_code`, `error_message`, `request_id`, `correlation_id`, `failure_metadata`
- Meal inference summary event:
  - `event` (message prefix `hawker_vision_response_summary`), `request_id`, `correlation_id`, `provider`, `model`, `endpoint`, `destination`, `confidence`, `manual_review`, `reason`
- Adaptive recommendation agent events:
  - `agent_recommendation_complete` -> `user_id`, `fallback_mode`, `interactions`, `recommendations`
  - `interaction_learning_complete` -> `user_id`, `candidate_id`, `event_type`, `interactions`
- Persistence support events relevant to personalization:
  - `save_health_profile` -> `user_id`, `goals`
  - `save_recommendation_interaction` -> `user_id`, `candidate_id`, `event_type`
  - `save_preference_snapshot` -> `user_id`, `interactions`

## Dev Log Toggles
- Backend:
  - `API_DEV_LOG_VERBOSE`
  - `API_DEV_LOG_HEADERS`
  - `API_DEV_LOG_RESPONSE_HEADERS`
- Frontend:
  - `NEXT_PUBLIC_DEV_LOG_FRONTEND`
  - `NEXT_PUBLIC_DEV_LOG_FRONTEND_VERBOSE`

## Contract Tests
- `apps/api/tests/test_api_observability_contract.py`
  - Header forwarding
  - Meal workflow propagation
  - Alert workflow propagation
  - Failure log enrichment

## Current Gaps
- The adaptive recommendation service currently emits completion-level learning/ranking logs, but not per-candidate ranking traces.
- Offline learning refresh telemetry does not exist yet because refresh remains an in-process online rerank model in the current release.
