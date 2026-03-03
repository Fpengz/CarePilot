"""
backend/deps.py
---------------
Initialises all agent singletons once and exposes them for use across routers.
Run from the project root so the parent-level packages (agents/, routes/, etc.) are importable.
"""
import sys
from pathlib import Path

# Make the project root importable regardless of working directory
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(ROOT / ".env")

from agents.chat_agent import ChatAgent
from agents.audio_agent import AudioAgent
from agents.search_agent import SearchAgent
from agents.health_tracker import HealthTracker
from routes import QueryRouter
from ingestion.usermed_ingest import (
    user_med_db,
    prescription_parser,
    TIMING_LABEL_TO_SLOT,
    SLOT_TO_LABEL,
    TIMING_SLOTS,
)

CHAT_MODEL_ID: str = os.environ.get("CHAT_MODEL_ID", "aisingapore/Gemma-SEA-LION-v4-27B-IT")
SEALION_API:   str = os.environ.get("SEALION_API", "")
BASE_URL:      str = "https://api.sea-lion.ai/v1"

# Synchronous agents (routing, memory, medications)
_search_agent = SearchAgent(max_results=3)
_router       = QueryRouter(_search_agent)
chat_agent    = ChatAgent(model_id=CHAT_MODEL_ID, router=_router)
audio_agent   = AudioAgent()

# Async OpenAI client — shares the same credentials & model as chat_agent
# but supports `await client.chat.completions.create(..., stream=True)`
async_client = AsyncOpenAI(api_key=SEALION_API, base_url=BASE_URL)

health_tracker = HealthTracker(
    session_id="default",
    client=chat_agent.client,
    model_id=CHAT_MODEL_ID,
)

__all__ = [
    "chat_agent",
    "audio_agent",
    "async_client",
    "health_tracker",
    "user_med_db",
    "prescription_parser",
    "TIMING_LABEL_TO_SLOT",
    "SLOT_TO_LABEL",
    "TIMING_SLOTS",
    "CHAT_MODEL_ID",
]
