# Observability Map

## Request Context Contract
- Incoming headers: `X-Request-ID`, `X-Correlation-ID`
- Middleware responsibilities:
  - Populate `request.state.request_id` and `request.state.correlation_id`
  - Echo both headers in every API response
  - Emit `event=api_request_complete` with method/path/status/duration

## Propagation Paths
- API routes:
  - Suggestions generate/list/detail
  - Meal analyze/records
  - Alerts trigger/timeline
  - Recommendations generate
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

## Contract Tests
- `apps/api/tests/test_api_observability_contract.py`
  - Header forwarding
  - Meal workflow propagation
  - Alert workflow propagation
  - Failure log enrichment
