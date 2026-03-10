"""Module for routes shared."""

from typing import Annotated, Any, cast

from fastapi import Cookie, Depends, HTTPException, Request

from dietary_guardian.domain.notifications.models import MedicationRegimen
from dietary_guardian.domain.tooling import has_scopes

from .deps import AppContext, AuthContext, auth_context
from .policy import authorize_action, authorize_resource_action

SESSION_COOKIE = "dg_session"
SessionData = dict[str, Any]


def get_context(request: Request) -> AppContext:
    return cast(AppContext, request.app.state.ctx)


def get_auth_context(request: Request) -> AuthContext:
    return auth_context(get_context(request))


def _is_valid_session_payload(session: object) -> bool:
    if not isinstance(session, dict):
        return False
    payload = cast(dict[str, object], session)
    required_str_keys = [
        "session_id",
        "user_id",
        "email",
        "account_role",
        "profile_mode",
        "display_name",
    ]
    for key in required_str_keys:
        if not isinstance(payload.get(key), str):
            return False
    scopes = payload.get("scopes")
    if not isinstance(scopes, list) or not all(isinstance(item, str) for item in scopes):
        return False
    return True


def _session_cookie_candidates(request: Request, session_cookie: str | None) -> list[str]:
    raw_cookie = request.headers.get("cookie") or ""
    candidates: list[str] = []
    for part in raw_cookie.split(";"):
        item = part.strip()
        if not item or "=" not in item:
            continue
        name, value = item.split("=", 1)
        if name.strip() != SESSION_COOKIE:
            continue
        token = value.strip()
        if token:
            candidates.append(token)
    if session_cookie and session_cookie not in candidates:
        candidates.append(session_cookie)
    return candidates


def require_session(
    request: Request,
    session_cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> SessionData:
    ctx = get_auth_context(request)  # narrow context — only auth fields needed
    candidates = _session_cookie_candidates(request, session_cookie)
    if not candidates:
        raise HTTPException(status_code=401, detail="authentication required")

    had_signed_candidate = False
    had_malformed_payload = False
    for token in candidates:
        session_id = ctx.session_signer.unsign(
            token,
            max_age_seconds=int(ctx.settings.auth.session_ttl_seconds),
        )
        if not session_id:
            continue
        had_signed_candidate = True
        session = ctx.auth_store.get_session(session_id)
        if session is None:
            continue
        if not _is_valid_session_payload(session):
            had_malformed_payload = True
            ctx.auth_store.destroy_session(session_id)
            continue
        return session

    if had_malformed_payload:
        raise HTTPException(status_code=401, detail="invalid session")
    if had_signed_candidate:
        raise HTTPException(status_code=401, detail="session expired")
    raise HTTPException(status_code=401, detail="invalid session")


def require_scopes(session: SessionData, required_scopes: set[str]) -> None:
    scopes = [str(item) for item in cast(list[object], session.get("scopes", []))]
    if not has_scopes(scopes, required_scopes):
        raise HTTPException(status_code=403, detail="forbidden")


def require_action(session: SessionData, action: str) -> None:
    authorize_action(session, action=action)


def require_resource_action(session: SessionData, action: str, resource: dict[str, object]) -> None:
    authorize_resource_action(session, action=action, resource=resource)


def current_session(session: SessionData = Depends(require_session)) -> SessionData:
    return session


def default_demo_regimens(user_id: str) -> list[MedicationRegimen]:
    return [
        MedicationRegimen(
            id=f"api-demo-pre-{user_id}",
            user_id=user_id,
            medication_name="Metformin",
            dosage_text="500mg",
            timing_type="pre_meal",
            offset_minutes=30,
            slot_scope=["lunch"],
        ),
        MedicationRegimen(
            id=f"api-demo-post-{user_id}",
            user_id=user_id,
            medication_name="Amlodipine",
            dosage_text="5mg",
            timing_type="post_meal",
            offset_minutes=15,
            slot_scope=["dinner"],
        ),
    ]
