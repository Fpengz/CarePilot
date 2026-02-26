from typing import Annotated, cast

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from dietary_guardian.models.identity import AccountRole, ProfileMode

from ..routes_shared import SESSION_COOKIE, current_session, get_context
from ..schemas import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthMeResponse,
    SessionInfo,
    SessionUser,
)

router = APIRouter(tags=["auth"])


@router.post("/api/v1/auth/login", response_model=AuthLoginResponse)
def auth_login(payload: AuthLoginRequest, response: Response, request: Request) -> AuthLoginResponse:
    context = get_context(request)
    user = context.auth_store.authenticate(str(payload.email), payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    session = context.auth_store.create_session(user)
    signed = context.session_signer.sign(session["session_id"])
    response.set_cookie(
        key=SESSION_COOKIE,
        value=signed,
        httponly=True,
        secure=context.settings.cookie_secure,
        samesite="lax",
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
        session_id = context.session_signer.unsign(session_cookie)
        if session_id:
            context.auth_store.destroy_session(session_id)
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=context.settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return {"ok": True}


@router.get("/api/v1/auth/me", response_model=AuthMeResponse)
def auth_me(session: dict[str, object] = Depends(current_session)) -> AuthMeResponse:
    return AuthMeResponse(
        user=SessionUser(
            user_id=str(session["user_id"]),
            email=str(session["email"]),
            account_role=cast(AccountRole, session["account_role"]),
            scopes=cast(list[str], session["scopes"]),
            profile_mode=cast(ProfileMode, session["profile_mode"]),
            display_name=str(session["display_name"]),
        )
    )
