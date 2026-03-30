# API Auth Contract (Current)

## Summary
Auth responses now return a principal-style payload that separates:
- `account_role` (authorization)
- `scopes` (capabilities)
- `profile_mode` (UI/care context)

The old `user.role` field has been removed (hard cutover).

## Login
`POST /api/v1/auth/login`

### Example response
```json
{
  "user": {
    "user_id": "ops_001",
    "email": "admin@example.com",
    "account_role": "admin",
    "scopes": [
      "alert:timeline:read",
      "alert:trigger",
      "meal:read",
      "meal:write",
      "recommendation:generate",
      "reminder:read",
      "reminder:write",
      "report:read",
      "report:write",
      "workflow:read",
      "workflow:replay"
    ],
    "profile_mode": "self",
    "display_name": "Ops Admin"
  },
  "session": {
    "session_id": "<uuid>",
    "issued_at": "<iso8601>"
  }
}
```

## Current User
`GET /api/v1/auth/me`

Returns the same `user` shape as login.

## Session Cookie Contract
- Cookie name: `dg_session`
- `HttpOnly`: always enabled
- `Secure`: controlled by `COOKIE_SECURE` (must be enabled in `staging`/`prod`)
- `SameSite`: controlled by `COOKIE_SAMESITE` (`lax` by default)
- Session revoke behavior:
  - `POST /api/v1/auth/logout` clears the cookie and revokes the current session when present
  - `PATCH /api/v1/auth/password` revokes all other sessions for the current user

## Demo Accounts
Demo credentials are for local/test use only.
- `member@example.com` / `member-pass`
- `helper@example.com` / `helper-pass`
- `admin@example.com` / `admin-pass`

## Migration Note
If an older client expects `user.role`, update it to use:
- `user.account_role` for authorization checks
- `user.profile_mode` for persona/UX branching
- `user.scopes` for fine-grained capability checks
