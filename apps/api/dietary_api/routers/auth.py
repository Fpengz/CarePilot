from datetime import datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from dietary_guardian.models.identity import AccountRole, ProfileMode
from dietary_guardian.application.auth.use_cases import (
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidSignupPasswordError,
    LoginLockedError,
    MIN_PASSWORD_LENGTH,
    login_and_create_session,
    signup_member_and_create_session,
)

from ..routes_shared import SESSION_COOKIE, current_session, get_context, require_action, require_resource_action
from ..schemas.auth import (
    AuthAuditEvent,
    AuthAuditEventListResponse,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthMeResponse,
    AuthPasswordUpdateRequest,
    AuthPasswordUpdateResponse,
    AuthProfileUpdateRequest,
    AuthSignupRequest,
    AuthSessionListItem,
    AuthSessionListResponse,
    AuthSessionRevokeOthersResponse,
    AuthSessionRevokeResponse,
    SessionInfo,
    SessionUser,
)

router = APIRouter(tags=["auth"])


def _session_user_from_session(session: dict[str, object]) -> SessionUser:
    return SessionUser(
        user_id=str(session["user_id"]),
        email=str(session["email"]),
        account_role=cast(AccountRole, session["account_role"]),
        scopes=cast(list[str], session["scopes"]),
        profile_mode=cast(ProfileMode, session["profile_mode"]),
        display_name=str(session["display_name"]),
    )


def _clear_session_cookie(
    response: Response,
    *,
    secure: bool,
    samesite: Literal["lax", "strict", "none"],
) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=secure,
        httponly=True,
        samesite=samesite,
    )


@router.post("/api/v1/auth/login", response_model=AuthLoginResponse)
def auth_login(payload: AuthLoginRequest, response: Response, request: Request) -> AuthLoginResponse:
    context = get_context(request)
    email = str(payload.email)
    try:
        auth_result = login_and_create_session(
            auth_store=context.auth_store,
            email=email,
            password=payload.password,
        )
    except LoginLockedError as exc:
        raise HTTPException(status_code=429, detail="too many login attempts, try again later") from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail="invalid credentials") from exc
    user = auth_result.user
    session = auth_result.session
    signed = context.session_signer.sign(session["session_id"])
    response.set_cookie(
        key=SESSION_COOKIE,
        value=signed,
        httponly=True,
        secure=context.settings.cookie_secure,
        samesite=context.settings.cookie_samesite,
        path="/",
    )
    return AuthLoginResponse(
        user=SessionUser(
            user_id=user.user_id,
            email=user.email,
            account_role=user.account_role,
            scopes=cast(list[str], session["scopes"]),
            profile_mode=user.profile_mode,
            display_name=user.display_name,
        ),
        session=SessionInfo(session_id=session["session_id"]),
    )


@router.post("/api/v1/auth/signup", response_model=AuthLoginResponse)
def auth_signup(payload: AuthSignupRequest, response: Response, request: Request) -> AuthLoginResponse:
    display_name = (payload.display_name or "").strip()
    if not display_name:
        display_name = str(payload.email).split("@", 1)[0]
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name must not be blank")

    context = get_context(request)
    try:
        auth_result = signup_member_and_create_session(
            auth_store=context.auth_store,
            email=str(payload.email),
            password=payload.password,
            display_name=display_name,
            profile_mode=payload.profile_mode,
        )
    except InvalidSignupPasswordError as exc:
        raise HTTPException(status_code=400, detail=f"password must be at least {MIN_PASSWORD_LENGTH} characters") from exc
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=409, detail="email already registered") from exc
    user = auth_result.user
    session = auth_result.session
    signed = context.session_signer.sign(session["session_id"])
    response.set_cookie(
        key=SESSION_COOKIE,
        value=signed,
        httponly=True,
        secure=context.settings.cookie_secure,
        samesite=context.settings.cookie_samesite,
        path="/",
    )
    return AuthLoginResponse(
        user=SessionUser(
            user_id=user.user_id,
            email=user.email,
            account_role=user.account_role,
            scopes=cast(list[str], session["scopes"]),
            profile_mode=user.profile_mode,
            display_name=user.display_name,
        ),
        session=SessionInfo(session_id=session["session_id"]),
    )


@router.post("/api/v1/auth/logout")
def auth_logout(
    request: Request,
    response: Response,
    session_cookie: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> dict[str, object]:
    context = get_context(request)
    if session_cookie:
        session_id = context.session_signer.unsign(
            session_cookie,
            max_age_seconds=int(context.settings.auth_session_ttl_seconds),
        )
        if session_id:
            context.auth_store.destroy_session(session_id)
    _clear_session_cookie(
        response,
        secure=context.settings.cookie_secure,
        samesite=context.settings.cookie_samesite,
    )
    return {"ok": True}


@router.get("/api/v1/auth/me", response_model=AuthMeResponse)
def auth_me(session: dict[str, object] = Depends(current_session)) -> AuthMeResponse:
    return AuthMeResponse(user=_session_user_from_session(session))


@router.patch("/api/v1/auth/profile", response_model=AuthMeResponse)
def auth_update_profile(
    payload: AuthProfileUpdateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> AuthMeResponse:
    display_name = payload.display_name
    if display_name is not None:
        display_name = display_name.strip()
        if not display_name:
            raise HTTPException(status_code=400, detail="display_name must not be blank")
    if display_name is None and payload.profile_mode is None:
        raise HTTPException(status_code=400, detail="no profile changes requested")
    context = get_context(request)
    updated = context.auth_store.update_user_profile(
        user_id=str(session["user_id"]),
        display_name=display_name,
        profile_mode=payload.profile_mode,
    )
    if updated is None:
        raise HTTPException(status_code=401, detail="invalid session")
    refreshed = context.auth_store.get_session(str(session["session_id"]))
    if refreshed is None:
        raise HTTPException(status_code=401, detail="session expired")
    return AuthMeResponse(user=_session_user_from_session(cast(dict[str, object], refreshed)))


@router.patch("/api/v1/auth/password", response_model=AuthPasswordUpdateResponse)
def auth_update_password(
    payload: AuthPasswordUpdateRequest,
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> AuthPasswordUpdateResponse:
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=400, detail="new password must differ from current password")
    if len(payload.new_password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"new password must be at least {MIN_PASSWORD_LENGTH} characters",
        )

    context = get_context(request)
    ok, revoked_count = context.auth_store.change_user_password(
        user_id=str(session["user_id"]),
        current_password=payload.current_password,
        new_password=payload.new_password,
        keep_session_id=str(session["session_id"]),
    )
    if not ok:
        context.auth_store.append_auth_audit_event(
            event_type="password_change_failed",
            email=str(session["email"]),
            user_id=str(session["user_id"]),
            metadata={"reason": "invalid_current_password"},
        )
        raise HTTPException(status_code=400, detail="current password is incorrect")

    context.auth_store.append_auth_audit_event(
        event_type="password_changed",
        email=str(session["email"]),
        user_id=str(session["user_id"]),
        metadata={"revoked_other_sessions": revoked_count},
    )
    return AuthPasswordUpdateResponse(revoked_other_sessions=revoked_count)


@router.get("/api/v1/auth/sessions", response_model=AuthSessionListResponse)
def auth_sessions(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> AuthSessionListResponse:
    context = get_context(request)
    user_id = str(session["user_id"])
    current_session_id = str(session["session_id"])
    sessions = context.auth_store.list_sessions_for_user(user_id)
    return AuthSessionListResponse(
        sessions=[
            AuthSessionListItem(
                session_id=str(item["session_id"]),
                issued_at=datetime.fromisoformat(str(item["issued_at"])),
                is_current=str(item["session_id"]) == current_session_id,
            )
            for item in sessions
        ]
    )


@router.post("/api/v1/auth/sessions/revoke-others", response_model=AuthSessionRevokeOthersResponse)
def auth_revoke_other_sessions(
    request: Request,
    session: dict[str, object] = Depends(current_session),
) -> AuthSessionRevokeOthersResponse:
    context = get_context(request)
    revoked_count = context.auth_store.revoke_other_sessions(
        str(session["user_id"]),
        keep_session_id=str(session["session_id"]),
    )
    return AuthSessionRevokeOthersResponse(revoked_count=revoked_count)


@router.post("/api/v1/auth/sessions/{session_id}/revoke", response_model=AuthSessionRevokeResponse)
def auth_revoke_session(
    session_id: str,
    request: Request,
    response: Response,
    session: dict[str, object] = Depends(current_session),
) -> AuthSessionRevokeResponse:
    context = get_context(request)
    owner_user_id = context.auth_store.get_session_owner(session_id)
    if owner_user_id is None:
        return AuthSessionRevokeResponse(revoked=False)
    require_resource_action(
        session,
        "auth.sessions.revoke",
        {"owner_user_id": owner_user_id},
    )
    context.auth_store.destroy_session(session_id)
    if session_id == str(session["session_id"]):
        _clear_session_cookie(
            response,
            secure=context.settings.cookie_secure,
            samesite=context.settings.cookie_samesite,
        )
    return AuthSessionRevokeResponse(revoked=True)


@router.get("/api/v1/auth/audit-events", response_model=AuthAuditEventListResponse)
def auth_audit_events(
    request: Request,
    limit: int = 50,
    session: dict[str, object] = Depends(current_session),
) -> AuthAuditEventListResponse:
    require_action(session, "auth.audit.read")
    context = get_context(request)
    items = context.auth_store.list_auth_audit_events(limit=limit)
    return AuthAuditEventListResponse(
        items=[
            AuthAuditEvent(
                event_id=str(item["event_id"]),
                event_type=str(item["event_type"]),
                email=str(item["email"]),
                user_id=(str(item["user_id"]) if item.get("user_id") is not None else None),
                created_at=datetime.fromisoformat(str(item["created_at"])),
                metadata=cast(dict[str, object], item.get("metadata", {})),
            )
            for item in items
        ]
    )
