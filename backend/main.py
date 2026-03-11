"""
backend/main.py
---------------
FastAPI application.

Run from the project root:
    uvicorn backend.main:app --reload --port 8000

Or from the backend directory after adding project root to PYTHONPATH:
    PYTHONPATH=.. uvicorn main:app --reload --port 8000
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import chat, medications, dashboard
from backend.routers import emotion as emotion_router

app = FastAPI(
    title="SEA-LION Health Assistant API",
    version="1.0.0",
    description="Backend API for the SEA-LION Health Assistant.",
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server (port 3000) and any local origin
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(chat.router)
app.include_router(medications.router)
app.include_router(dashboard.router)
app.include_router(emotion_router.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}
