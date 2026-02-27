from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from dietary_guardian.logging_config import get_logger

from .deps import AppContext, build_app_context, close_app_context
from .errors import (
    ApiAppError,
    handle_api_app_error,
    handle_http_exception,
    handle_unhandled_exception,
    handle_validation_exception,
)
from .middleware import request_context_middleware
from .routers import include_routers

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    ctx_owned = bool(getattr(app.state, "ctx_owned", False))
    if ctx_owned and getattr(app.state, "ctx", None) is None:
        app.state.ctx = build_app_context()
    logger.info("event=api_startup status=ready")
    yield
    ctx = cast(AppContext | None, getattr(app.state, "ctx", None))
    if ctx_owned and ctx is not None:
        close_app_context(ctx)
        app.state.ctx = None
    logger.info("event=api_shutdown status=complete")


def create_app(ctx: AppContext | None = None) -> FastAPI:
    app = FastAPI(title="Dietary Guardian API", version="0.1.0", lifespan=app_lifespan)
    app.state.ctx_owned = ctx is None
    app.state.ctx = ctx or build_app_context()
    settings = app.state.ctx.settings
    app.add_middleware(
        cast(Any, CORSMiddleware),
        allow_origins=[item.strip() for item in settings.api_cors_origins.split(",") if item.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_context_middleware)
    include_routers(app)
    app.add_exception_handler(ApiAppError, cast(Any, handle_api_app_error))
    app.add_exception_handler(HTTPException, cast(Any, handle_http_exception))
    app.add_exception_handler(RequestValidationError, cast(Any, handle_validation_exception))
    app.add_exception_handler(Exception, cast(Any, handle_unhandled_exception))

    return app
