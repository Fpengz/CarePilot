from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from dietary_guardian.services.authorization import has_scopes

SessionData = dict[str, Any]
ResourceData = dict[str, Any]


@dataclass(frozen=True, slots=True)
class PolicyRule:
    required_scopes: frozenset[str]
    resource_guard: str | None = None


POLICY_RULES: dict[str, PolicyRule] = {
    "meal.analyze": PolicyRule(required_scopes=frozenset({"meal:write"})),
    "meal.records.read": PolicyRule(required_scopes=frozenset({"meal:read"})),
    "reports.parse": PolicyRule(required_scopes=frozenset({"report:write"})),
    "recommendations.generate": PolicyRule(required_scopes=frozenset({"recommendation:generate"})),
    "recommendations.daily_agent.read": PolicyRule(required_scopes=frozenset({"recommendation:generate"})),
    "recommendations.substitutions.generate": PolicyRule(required_scopes=frozenset({"recommendation:generate"})),
    "recommendations.interactions.write": PolicyRule(required_scopes=frozenset({"recommendation:generate"})),
    "emotions.text.infer": PolicyRule(required_scopes=frozenset({"emotion:infer"})),
    "emotions.speech.infer": PolicyRule(required_scopes=frozenset({"emotion:infer"})),
    "suggestions.generate": PolicyRule(required_scopes=frozenset({"report:write", "recommendation:generate"})),
    "suggestions.read": PolicyRule(required_scopes=frozenset({"report:read"})),
    "reminders.generate": PolicyRule(required_scopes=frozenset({"reminder:write"})),
    "reminders.read": PolicyRule(required_scopes=frozenset({"reminder:read"})),
    "reminders.confirm": PolicyRule(required_scopes=frozenset({"reminder:write"})),
    "medications.regimens.read": PolicyRule(required_scopes=frozenset({"reminder:read"})),
    "medications.regimens.write": PolicyRule(required_scopes=frozenset({"reminder:write"})),
    "medications.adherence.read": PolicyRule(required_scopes=frozenset({"reminder:read"})),
    "medications.adherence.write": PolicyRule(required_scopes=frozenset({"reminder:write"})),
    "symptoms.read": PolicyRule(required_scopes=frozenset({"report:read"})),
    "symptoms.write": PolicyRule(required_scopes=frozenset({"report:write"})),
    "clinical_cards.read": PolicyRule(required_scopes=frozenset({"report:read"})),
    "clinical_cards.generate": PolicyRule(required_scopes=frozenset({"report:read", "recommendation:generate"})),
    "metrics.trends.read": PolicyRule(required_scopes=frozenset({"report:read"})),
    "companion.today.read": PolicyRule(required_scopes=frozenset({"meal:read", "reminder:read", "report:read"})),
    "companion.interactions.write": PolicyRule(required_scopes=frozenset({"recommendation:generate", "report:read"})),
    "clinician.digest.read": PolicyRule(required_scopes=frozenset({"report:read", "recommendation:generate"})),
    "impact.summary.read": PolicyRule(required_scopes=frozenset({"meal:read", "reminder:read", "report:read"})),
    "households.care.read_members": PolicyRule(required_scopes=frozenset()),
    "households.care.read_profile": PolicyRule(required_scopes=frozenset()),
    "households.care.read_meals": PolicyRule(required_scopes=frozenset({"meal:read"})),
    "households.care.read_reminders": PolicyRule(required_scopes=frozenset({"reminder:read"})),
    "alerts.trigger": PolicyRule(required_scopes=frozenset({"alert:trigger"})),
    "alerts.timeline.read": PolicyRule(required_scopes=frozenset({"alert:timeline:read"})),
    "workflows.read": PolicyRule(required_scopes=frozenset({"workflow:read"})),
    "workflows.replay": PolicyRule(required_scopes=frozenset({"workflow:replay"})),
    "workflows.write": PolicyRule(required_scopes=frozenset({"workflow:write"})),
    "auth.audit.read": PolicyRule(required_scopes=frozenset({"auth:audit:read"})),
    "auth.sessions.revoke": PolicyRule(required_scopes=frozenset(), resource_guard="session_owner"),
}


def authorize_action(session: SessionData, *, action: str) -> None:
    rule = POLICY_RULES.get(action)
    if rule is None:
        raise RuntimeError(f"unknown policy action: {action}")
    scopes = [str(item) for item in session.get("scopes", [])]
    if not has_scopes(scopes, set(rule.required_scopes)):
        raise HTTPException(status_code=403, detail="forbidden")


def _guard_session_owner(session: SessionData, resource: ResourceData) -> None:
    owner_user_id = resource.get("owner_user_id")
    if not isinstance(owner_user_id, str):
        raise RuntimeError("session_owner guard requires owner_user_id")
    if str(session["user_id"]) != owner_user_id:
        raise HTTPException(status_code=404, detail="session not found")


def authorize_resource_action(session: SessionData, *, action: str, resource: ResourceData) -> None:
    authorize_action(session, action=action)
    rule = POLICY_RULES[action]
    if rule.resource_guard is None:
        return
    if rule.resource_guard == "session_owner":
        _guard_session_owner(session, resource)
        return
    raise RuntimeError(f"unknown resource guard: {rule.resource_guard}")
