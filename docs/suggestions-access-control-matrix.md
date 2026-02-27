# Suggestions Access Control Matrix

## Scope Rules
| Scope | Membership requirement | Visible source users | Out-of-scope detail behavior |
|---|---|---|---|
| `self` | Authenticated user | Current user only | `404 suggestions.not_found` |
| `household` | Active household and current membership | All current household members | `404 suggestions.not_found` |
| `household` without membership | Fails membership check | None | `403 suggestions.forbidden` |

## Edge Cases
| Scenario | Expected result |
|---|---|
| Shared member access | Household scope returns both owner + member suggestions |
| Revoked access (member removed) | Removed member gets `403` for household scope |
| Partial ownership (owner removing member) | Removed member suggestions no longer visible to household list/detail (`404`) |
| Mixed visibility / cross-household | List filter denied with `403`; direct detail hidden as `404` |

## Test Coverage
- `apps/api/tests/test_api_suggestions.py`
  - `test_suggestions_household_access_revoked_after_member_removed`
  - `test_suggestions_cross_household_detail_attempt_is_hidden`
  - Existing household scope and source filter tests
