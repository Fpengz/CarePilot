# RBAC Matrix

## Overview
The system now separates:

- `account_role` (authorization): `member`, `admin`
- `profile_mode` (product persona / UX mode): `self`, `caregiver`

`profile_mode` changes presentation and workflow context, but **does not grant privileges**.

## Demo Accounts
- `member@example.com` / `member-pass` -> `account_role=member`, `profile_mode=self`
- `helper@example.com` / `helper-pass` -> `account_role=member`, `profile_mode=caregiver`
- `admin@example.com` / `admin-pass` -> `account_role=admin`, `profile_mode=self`

## Scope Mapping

### `member`
- `meal:write`
- `meal:read`
- `report:write`
- `report:read`
- `recommendation:generate`
- `reminder:write`
- `reminder:read`

### `admin`
- all `member` scopes
- `alert:trigger`
- `alert:timeline:read`
- `workflow:read`
- `workflow:replay`

## API Endpoint Permissions

### Auth
- `POST /api/v1/auth/login` -> public
- `POST /api/v1/auth/logout` -> authenticated session
- `GET /api/v1/auth/me` -> authenticated session

### Health Profile / Personalization
- `GET /api/v1/profile/health` -> authenticated session
- `PATCH /api/v1/profile/health` -> authenticated session
- `GET /api/v1/suggestions/daily` -> authenticated session

### Meals
- `POST /api/v1/meal/analyze` -> `meal:write`
- `GET /api/v1/meal/records` -> `meal:read`

### Reports / Recommendations
- `POST /api/v1/reports/parse` -> `report:write`
- `POST /api/v1/recommendations/generate` -> `recommendation:generate`
- `GET /api/v1/recommendations/daily-agent` -> `recommendation:generate`
- `POST /api/v1/recommendations/substitutions` -> `recommendation:generate`
- `POST /api/v1/recommendations/interactions` -> `recommendation:generate`

### Suggestions
- `POST /api/v1/suggestions/generate-from-report` -> `report:write` + `recommendation:generate`
- `GET /api/v1/suggestions` -> `report:read`
- `GET /api/v1/suggestions/{suggestion_id}` -> `report:read`

### Reminders
- `POST /api/v1/reminders/generate` -> `reminder:write`
- `GET /api/v1/reminders` -> `reminder:read`
- `POST /api/v1/reminders/{event_id}/confirm` -> `reminder:write`
- `GET /api/v1/reminders/{event_id}/notification-schedules` -> `reminder:read`
- `GET /api/v1/reminders/{event_id}/notification-logs` -> `reminder:read`
- `GET /api/v1/reminder-notification-preferences` -> `reminder:read`
- `PUT /api/v1/reminder-notification-preferences/default` -> `reminder:write`
- `PUT /api/v1/reminder-notification-preferences/reminder-types/{type}` -> `reminder:write`
- `GET /api/v1/reminder-notification-endpoints` -> `reminder:read`
- `PUT /api/v1/reminder-notification-endpoints` -> `reminder:write`

### Alerts / Workflows (privileged)
- `POST /api/v1/alerts/trigger` -> `alert:trigger`
- `GET /api/v1/alerts/{alert_id}/timeline` -> `alert:timeline:read`
- `GET /api/v1/workflows` -> `workflow:read`
- `GET /api/v1/workflows/{correlation_id}` -> `workflow:replay`

## Tool Policy (Internal)
- `trigger_alert` tool requires `alert:trigger` scope
- Tool registry policy is scope-based (`required_scopes`), not role-name based
