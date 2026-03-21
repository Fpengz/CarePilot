"""
Build the FastAPI application and lifecycle hooks.

This module wires middleware, routes, and error handlers into the dietary API
application and configures startup/shutdown behavior.
"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from care_pilot.platform.observability import get_logger
from care_pilot.platform.runtime.background_tasks import run_background_worker

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


def _csv_values(raw: str, *, fallback: list[str]) -> list[str]:
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or fallback


async def _run_maintenance(ctx: AppContext) -> None:
    """Run periodic system maintenance tasks."""
    # Wait a bit after startup
    await asyncio.sleep(10)
    while True:
        try:
            logger.info("background_maintenance_start")
            count = ctx.stores.workflows.prune_events(days=90)
            logger.info("background_maintenance_complete pruned_events=%s", count)
        except Exception as exc:
            logger.exception("background_maintenance_failed error=%s", exc)

        # Run every 24 hours
        await asyncio.sleep(24 * 3600)


async def _prewarm_models(ctx: AppContext) -> None:
    """Pre-load heavy ML models during startup to reduce cold-start latency."""
    try:
        logger.info("model_prewarm_start")
        # Trigger lazy-load of emotion agent if enabled
        if ctx.settings.emotion.inference_enabled:
            await ctx.emotion_agent.health()

        # Trigger load_model for local audio agent
        if True:  # Force check for prewarm
            await asyncio.to_thread(ctx.chat_audio_agent.load_model)

        logger.info("model_prewarm_complete")
    except Exception as exc:
        logger.warning("model_prewarm_failed error=%s", exc)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    ctx_owned = bool(getattr(app.state, "ctx_owned", False))
    if ctx_owned and getattr(app.state, "ctx", None) is None:
        app.state.ctx = build_app_context()

    ctx = cast(AppContext, app.state.ctx)
    maintenance_task = asyncio.create_task(_run_maintenance(ctx))
    worker_task = asyncio.create_task(run_background_worker())

    # Run pre-warming in background to not block startup
    prewarm_task = asyncio.create_task(_prewarm_models(ctx))

    logger.info("event=api_startup status=ready")
    yield

    prewarm_task.cancel()
    worker_task.cancel()
    maintenance_task.cancel()
    if ctx_owned and ctx is not None:
        close_app_context(ctx)
        app.state.ctx = None
    logger.info("event=api_shutdown status=complete")


def create_app(ctx: AppContext | None = None) -> FastAPI:
    app = FastAPI(
        title="CarePilot API",
        version="0.1.0",
        lifespan=app_lifespan,
    )

    if ctx:
        app.state.ctx = ctx
        app.state.ctx_owned = False
    else:
        app.state.ctx_owned = True

    # Middleware
    app.add_middleware(
        cast(Any, CORSMiddleware),
        allow_origins=_csv_values(os.environ.get("ALLOWED_ORIGINS", ""), fallback=["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_context_middleware)

    # Routes
    include_routers(app)

    # Error Handlers
    app.add_exception_handler(ApiAppError, cast(Any, handle_api_app_error))
    app.add_exception_handler(HTTPException, cast(Any, handle_http_exception))
    app.add_exception_handler(RequestValidationError, cast(Any, handle_validation_exception))
    app.add_exception_handler(Exception, cast(Any, handle_unhandled_exception))

    return app
