from fastapi import FastAPI

from .alerts import router as alerts_router
from .auth import router as auth_router
from .clinical_cards import router as clinical_cards_router
from .emotions import router as emotions_router
from .health import router as health_router
from .health_profiles import router as health_profiles_router
from .households import router as households_router
from .meals import router as meals_router
from .medications import router as medications_router
from .metrics import router as metrics_router
from .notifications import router as notifications_router
from .recommendations import router as recommendations_router
from .reminders import router as reminders_router
from .reports import router as reports_router
from .symptoms import router as symptoms_router
from .workflows import router as workflows_router
from .suggestions import router as suggestions_router


def include_routers(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(emotions_router)
    app.include_router(health_profiles_router)
    app.include_router(auth_router)
    app.include_router(households_router)
    app.include_router(alerts_router)
    app.include_router(workflows_router)
    app.include_router(meals_router)
    app.include_router(notifications_router)
    app.include_router(reports_router)
    app.include_router(recommendations_router)
    app.include_router(suggestions_router)
    app.include_router(reminders_router)
    app.include_router(medications_router)
    app.include_router(symptoms_router)
    app.include_router(clinical_cards_router)
    app.include_router(metrics_router)
