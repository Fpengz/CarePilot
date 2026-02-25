from fastapi import FastAPI

from .alerts import router as alerts_router
from .auth import router as auth_router
from .health import router as health_router
from .meals import router as meals_router
from .notifications import router as notifications_router
from .recommendations import router as recommendations_router
from .reminders import router as reminders_router
from .reports import router as reports_router
from .workflows import router as workflows_router


def include_routers(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(alerts_router)
    app.include_router(workflows_router)
    app.include_router(meals_router)
    app.include_router(notifications_router)
    app.include_router(reports_router)
    app.include_router(recommendations_router)
    app.include_router(reminders_router)
