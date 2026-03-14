"""Tests for regressions inference and alerting."""

import pytest

from dietary_guardian.agent.dietary.agent import analyze_dietary_request
from dietary_guardian.agent.dietary.schemas import DietaryAgentInput, DietaryAgentOutput
from dietary_guardian.config.llm import LLMCapability
from dietary_guardian.features.safety.domain.alerts.models import AlertDeliveryResult, AlertMessage
from dietary_guardian.platform.persistence import SQLiteRepository
from dietary_guardian.platform.messaging.alert_outbox import AlertPublisher, OutboxWorker


@pytest.mark.anyio
async def test_analyze_dietary_request_uses_correct_capability(monkeypatch) -> None:
    captured_capability = None

    class MockModel:
        pass

    def mock_get_model(capability=None):
        nonlocal captured_capability
        captured_capability = capability
        return MockModel()

    class MockResult:
        output = DietaryAgentOutput(analysis="ok", advice="ok", is_safe=True)

    class MockAgent:
        def __init__(self, model, output_type, system_prompt):
            pass
        async def run(self, prompt, **kwargs):
            return MockResult()

    monkeypatch.setattr("dietary_guardian.agent.runtime.LLMFactory.get_model", mock_get_model)
    monkeypatch.setattr("dietary_guardian.agent.dietary.agent.Agent", MockAgent)

    input_data = DietaryAgentInput(
        user_name="Mr Tan",
        meal_name="Soup",
        ingredients=["Tofu"],
        is_safe=True,
    )

    await analyze_dietary_request(input_data)

    assert captured_capability == LLMCapability.DIETARY_REASONING


def test_outbox_worker_preserves_original_alert_message_payload(tmp_path) -> None:
    class CaptureSink:
        name = "in_app"

        def __init__(self) -> None:
            self.seen: AlertMessage | None = None

        def send(self, message: AlertMessage) -> AlertDeliveryResult:
            self.seen = message
            return AlertDeliveryResult(
                alert_id=message.alert_id,
                sink=self.name,
                success=True,
                attempt=1,
                destination="app://alerts",
            )

    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    publisher = AlertPublisher(repo)
    alert = AlertMessage(
        alert_id="alert-123",
        type="medication_reminder",
        severity="critical",
        payload={"message": "Amlodipine 5mg"},
        destinations=["in_app"],
        correlation_id="corr-123",
    )
    publisher.publish(alert)

    worker = OutboxWorker(repo, max_attempts=2, concurrency=2)
    capture = CaptureSink()
    worker._sinks["in_app"] = capture  # test-only seam to inspect delivered message

    import asyncio

    asyncio.run(worker.process_once())

    assert capture.seen is not None
    assert capture.seen.type == "medication_reminder"
    assert capture.seen.severity == "critical"
    assert capture.seen.payload["message"] == "Amlodipine 5mg"
    assert capture.seen.correlation_id == "corr-123"
