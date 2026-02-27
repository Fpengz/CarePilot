from typing import Any, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .deps import AppContext, build_app_context
from .middleware import request_context_middleware
from .routers import include_routers


def create_app(ctx: AppContext | None = None) -> FastAPI:
    app = FastAPI(title="Dietary Guardian API", version="0.1.0")
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

    return app
