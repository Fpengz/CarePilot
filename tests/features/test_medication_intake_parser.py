"""Tests for medication intake parsing."""

from datetime import date

import pytest

from dietary_guardian.agent.runtime.inference_types import InferenceResponse, ProviderMetadata
from dietary_guardian.features.medications.intake import build_plain_text_source, parse_medication_instructions
from dietary_guardian.features.medications.intake.models import MedicationParseOutput


class _FakeInferenceEngine:
    def __init__(self, output: MedicationParseOutput | None = None, *, should_fail: bool = False) -> None:
        self.output = output
        self.should_fail = should_fail

    async def infer(self, request):  # noqa: ANN001
        if self.should_fail:
            raise RuntimeError("llm unavailable")
        assert request.payload["prompt"]
        lowered_prompt = request.system_prompt.lower()
        assert "medication instructions" in lowered_prompt
        assert "instructions" in lowered_prompt
        assert "confidence_score" in lowered_prompt
        assert "warnings" in lowered_prompt
        assert "markdown" in lowered_prompt
        assert request.output_schema is MedicationParseOutput
        assert self.output is not None
        return InferenceResponse(
            request_id=request.request_id,
            structured_output=self.output,
            confidence=self.output.confidence_score,
            latency_ms=5.0,
            provider_metadata=ProviderMetadata(provider="test", model="test-model", endpoint="default"),
        )


@pytest.mark.anyio
async def test_parse_before_meal_duration_instruction() -> None:
    result = await parse_medication_instructions(
        source=build_plain_text_source("Take Metformin 500mg twice daily before meals for 5 days"),
        today=date(2026, 3, 14),
    )

    assert len(result.instructions) == 1
    instruction = result.instructions[0]
    assert instruction.medication_name_raw == "Metformin"
    assert instruction.dosage_text == "500mg"
    assert instruction.timing_type == "pre_meal"
    assert instruction.slot_scope == ["breakfast", "dinner"]
    assert instruction.duration_days == 5
    assert instruction.start_date == date(2026, 3, 14)
    assert instruction.end_date == date(2026, 3, 18)


@pytest.mark.anyio
async def test_parse_every_morning_defaults_to_8am() -> None:
    result = await parse_medication_instructions(
        source=build_plain_text_source("Amlodipine 5mg every morning"),
        today=date(2026, 3, 14),
    )

    instruction = result.instructions[0]
    assert instruction.timing_type == "fixed_time"
    assert instruction.fixed_time == "08:00"
    assert instruction.time_rules[0]["kind"] == "fixed_time"
    assert instruction.ambiguities == []


@pytest.mark.anyio
async def test_parse_unknown_text_returns_ambiguity() -> None:
    result = await parse_medication_instructions(
        source=build_plain_text_source("Please remind me about my tablets"),
        today=date(2026, 3, 14),
    )

    instruction = result.instructions[0]
    assert instruction.dosage_text == ""
    assert instruction.ambiguities
    assert instruction.confidence == 0.0


@pytest.mark.anyio
async def test_parse_prefers_llm_structured_output_when_available() -> None:
    result = await parse_medication_instructions(
        source=build_plain_text_source("Take Metformin 500mg twice daily before meals for 5 days"),
        today=date(2026, 3, 14),
        inference_engine=_FakeInferenceEngine(
            MedicationParseOutput.model_validate(
                {
                    "confidence_score": 0.97,
                    "instructions": [
                        {
                            "medication_name_raw": "Metformin",
                            "medication_name_canonical": "metformin",
                            "dosage_text": "500mg",
                            "timing_type": "pre_meal",
                            "frequency_type": "fixed_slots",
                            "frequency_times_per_day": 2,
                            "slot_scope": ["breakfast", "dinner"],
                            "offset_minutes": 30,
                            "time_rules": [{"kind": "before_meal", "slots": ["breakfast", "dinner"]}],
                            "duration_days": 5,
                            "start_date": "2026-03-14",
                            "end_date": "2026-03-18",
                            "confidence": 0.97,
                            "ambiguities": [],
                        }
                    ],
                }
            )
        ),
    )

    assert result.instructions[0].medication_name_canonical == "metformin"
    assert result.instructions[0].confidence == 0.97
    assert result.instructions[0].slot_scope == ["breakfast", "dinner"]


@pytest.mark.anyio
async def test_parse_falls_back_to_deterministic_when_llm_fails() -> None:
    result = await parse_medication_instructions(
        source=build_plain_text_source("Amlodipine 5mg every morning"),
        today=date(2026, 3, 14),
        inference_engine=_FakeInferenceEngine(should_fail=True),
    )

    assert result.instructions[0].medication_name_raw == "Amlodipine"
    assert result.instructions[0].fixed_time == "08:00"
