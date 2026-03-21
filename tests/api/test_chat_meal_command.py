"""Tests for chat meal command parsing and logging."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Removed: from care_pilot.agent.runtime.response import Response
from care_pilot.agent.chat.schemas import ChatSummaryOutput  # For structured_output
from care_pilot.agent.runtime.inference_types import InferenceRequest

# Import the actual types and protocol from their respective modules
from care_pilot.features.companion.chat.memory import (
    MemoryManager,
)
from care_pilot.features.companion.chat.orchestrator import ChatOrchestrator
from care_pilot.platform.persistence.domain_stores import build_app_stores
from care_pilot.platform.persistence.sqlite_app_store import SQLiteAppStore


# --- Mock types for Response ---
# Mimic the Response structure as it's not directly importable in test scope.
@dataclass(frozen=True)
class MockResponse:
    request_id: str
    structured_output: Any

# --- Mock Implementation of InferenceEngineProtocol ---
class MockInferenceEngine:
    # This class now correctly implements the imported InferenceEngineProtocol.
    async def infer(self, request: InferenceRequest) -> MockResponse: # Use MockResponse
        """A dummy inference engine for testing."""
        print(f"MockInferenceEngine.infer called with: {request.payload}")
        # Returning a dummy Response object. Its structured_output should be compatible
        # with ChatSummaryOutput for MemoryManager's casting.
        # We create an instance of ChatSummaryOutput to be placed in structured_output.
        dummy_output_data = ChatSummaryOutput(summary="This is a mock summary from MockInferenceEngine.")
        return MockResponse(request_id=request.request_id, structured_output=dummy_output_data) # Use MockResponse

# Instantiate the mock engine to be used in tests
mock_inference_engine = MockInferenceEngine()

# --- Original test functions follow... ---
def test_parse_meal_command_accepts_bracket_prefix(tmp_path: Path) -> None:
    memory = MemoryManager(user_id="u", session_id="s", db_path=tmp_path/"m.db", inference_engine=mock_inference_engine)
    orchestrator = ChatOrchestrator(router=None, memory=memory)
    assert orchestrator._parse_meal_command("[MEAL] chicken rice") == "chicken rice"


def test_parse_meal_command_accepts_colon_prefix(tmp_path: Path) -> None:
    memory = MemoryManager(user_id="u", session_id="s", db_path=tmp_path/"m.db", inference_engine=mock_inference_engine)
    orchestrator = ChatOrchestrator(router=None, memory=memory)
    assert orchestrator._parse_meal_command("meal: soft-boiled eggs with toast") == "soft-boiled eggs with toast"


def test_parse_meal_command_accepts_log_meal_prefix(tmp_path: Path) -> None:
    memory = MemoryManager(user_id="u", session_id="s", db_path=tmp_path/"m.db", inference_engine=mock_inference_engine)
    orchestrator = ChatOrchestrator(router=None, memory=memory)
    assert orchestrator._parse_meal_command("log meal: Test Dish") == "Test Dish"


def test_parse_meal_command_ignores_regular_text(tmp_path: Path) -> None:
    memory = MemoryManager(user_id="u", session_id="s", db_path=tmp_path/"m.db", inference_engine=mock_inference_engine)
    orchestrator = ChatOrchestrator(router=None, memory=memory)
    assert orchestrator._parse_meal_command("Hello there") is None


def test_log_meal_command_persists_event_and_profile(tmp_path: Path) -> None:
    app_store = SQLiteAppStore(str(tmp_path / "chat-meals.db"))
    stores = build_app_stores(app_store)
    memory = MemoryManager(user_id="u", session_id="s", db_path=tmp_path/"m.db", inference_engine=mock_inference_engine)
    orchestrator = ChatOrchestrator(router=None, memory=memory)

    result = orchestrator._log_meal_command(
        user_id="user-42",
        meal_text="Soft-boiled eggs with wholemeal toast",
        stores=stores,
    )

    assert "Soft-boiled eggs" in result["message"]
    assert len(stores.meals.list_validated_meal_events("user-42")) == 1
    assert len(stores.meals.list_nutrition_risk_profiles("user-42")) == 1
