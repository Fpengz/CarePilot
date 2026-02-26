from typing import Any, Annotated, cast

from fastapi import Cookie, Depends, HTTPException, Request

from dietary_guardian.models.medication import MedicationRegimen
from dietary_guardian.services.authorization import has_scopes

from .deps import AppContext

SESSION_COOKIE = "dg_session"
SessionData = dict[str, Any]


def get_context(request: Request) -> AppContext:
    return cast(AppContext, request.app.state.ctx)


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


def require_session(
    request: Request,
    session_cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> SessionData:
    ctx = get_context(request)
    if not session_cookie:
        raise HTTPException(status_code=401, detail="authentication required")
    session_id = ctx.session_signer.unsign(session_cookie)
    if not session_id:
        raise HTTPException(status_code=401, detail="invalid session")
    session = ctx.auth_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="session expired")
    if not _is_valid_session_payload(session):
        ctx.auth_store.destroy_session(session_id)
        raise HTTPException(status_code=401, detail="invalid session")
    return session


def require_scopes(session: SessionData, required_scopes: set[str]) -> None:
    scopes = [str(item) for item in cast(list[object], session.get("scopes", []))]
    if not has_scopes(scopes, required_scopes):
        raise HTTPException(status_code=403, detail="forbidden")


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
