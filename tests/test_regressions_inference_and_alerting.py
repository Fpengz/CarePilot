from datetime import datetime

import pytest

from dietary_guardian.agents.dietary import AgentResponse, process_meal_request
from dietary_guardian.config.llm import LLMCapability
from dietary_guardian.domain.alerts.models import AlertDeliveryResult, AlertMessage
from dietary_guardian.domain.identity.models import MedicalCondition, UserProfile
from dietary_guardian.infrastructure.persistence import SQLiteRepository
from dietary_guardian.models.meal import Ingredient, MealEvent, Nutrition
from dietary_guardian.infrastructure.notifications.alert_outbox import AlertPublisher, OutboxWorker


@pytest.mark.anyio
async def test_process_meal_request_does_not_force_gemini_model_for_test_provider(monkeypatch) -> None:
    class StubEngine:
        init_args: tuple[str | None, str | None, str | None] | None = None

        def __init__(
            self,
            provider: str | None = None,
            model_name: str | None = None,
            capability: str | None = None,
        ) -> None:
            StubEngine.init_args = (provider, model_name, capability)

        def health(self):
            class Health:
                endpoint = "default"
                provider = "test"

            return Health()

        async def infer(self, request):
            del request
            return type(
                "Result",
                (),
                {
                    "structured_output": AgentResponse(
                        analysis="ok",
                        advice="ok",
                        is_safe=True,
                    )
                },
            )()

    monkeypatch.setenv("LLM_PROVIDER", "test")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    from dietary_guardian.config.settings import get_settings

    get_settings.cache_clear()
    monkeypatch.setattr("dietary_guardian.agents.dietary.InferenceEngine", StubEngine)

    user = UserProfile(
        id="u1",
        name="Mr Tan",
        age=68,
        conditions=[MedicalCondition(name="Hypertension", severity="Medium")],
        medications=[],
    )
    meal = MealEvent(
        name="Soup",
        ingredients=[Ingredient(name="Tofu")],
        nutrition=Nutrition(calories=100, carbs_g=8, sugar_g=2, protein_g=6, fat_g=3, sodium_mg=120),
        timestamp=datetime(2026, 2, 25, 9, 0),
    )

    await process_meal_request(user, meal)

    assert StubEngine.init_args == ("test", None, LLMCapability.DIETARY_REASONING.value)
    get_settings.cache_clear()


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
