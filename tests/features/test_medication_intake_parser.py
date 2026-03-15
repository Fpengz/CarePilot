"""Tests for medication intake parsing."""

from datetime import date

import pytest

from care_pilot.agent.runtime.inference_types import (
    InferenceResponse,
    ProviderMetadata,
)
from care_pilot.features.medications.intake import (
    build_plain_text_source,
    parse_medication_instructions,
)
from care_pilot.features.medications.intake.models import (
    MedicationParseOutputLoose,
)


class _FakeInferenceEngine:
    def __init__(
        self,
        output: MedicationParseOutputLoose | None = None,
        *,
        should_fail: bool = False,
        expected_schema: type[object] | None = None,
    ) -> None:
        self.output = output
        self.should_fail = should_fail
        self.expected_schema = expected_schema

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
        if self.expected_schema is not None:
            assert request.output_schema is self.expected_schema
        assert self.output is not None
        return InferenceResponse(
            request_id=request.request_id,
            structured_output=self.output,
            confidence=self.output.confidence_score,
            latency_ms=5.0,
            provider_metadata=ProviderMetadata(
                provider="test", model="test-model", endpoint="default"
            ),
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
            MedicationParseOutputLoose.model_validate(
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
                            "time_rules": [
                                {
                                    "kind": "before_meal",
                                    "slots": ["breakfast", "dinner"],
                                }
                            ],
                            "duration_days": 5,
                            "start_date": "2026-03-14",
                            "end_date": "2026-03-18",
                            "confidence": 0.97,
                            "ambiguities": [],
                        }
                    ],
                }
            ),
            expected_schema=MedicationParseOutputLoose,
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
        inference_engine=_FakeInferenceEngine(
            should_fail=True, expected_schema=MedicationParseOutputLoose
        ),
    )

    assert result.instructions[0].medication_name_raw == "Amlodipine"
    assert result.instructions[0].fixed_time == "08:00"


@pytest.mark.anyio
async def test_parse_coerces_llm_invalid_fields() -> None:
    output = MedicationParseOutputLoose.model_validate(
        {
            "confidence_score": 0.88,
            "instructions": [
                {
                    "medication_name_raw": "Gabapentin",
                    "medication_name_canonical": "gabapentin",
                    "dosage_text": "300mg",
                    "timing_type": "times_per_day",
                    "frequency_type": "times_per_day",
                    "frequency_times_per_day": 3,
                    "slot_scope": None,
                    "fixed_time": None,
                    "time_rules": [],
                    "confidence": 0.88,
                    "ambiguities": [],
                }
            ],
        }
    )
    result = await parse_medication_instructions(
        source=build_plain_text_source("Gabapentin 300mg three times daily"),
        today=date(2026, 3, 14),
        inference_engine=_FakeInferenceEngine(output, expected_schema=MedicationParseOutputLoose),
    )

    instruction = result.instructions[0]
    assert instruction.timing_type == "fixed_time"
    assert instruction.frequency_type == "times_per_day"
    assert instruction.frequency_times_per_day == 3
    assert instruction.slot_scope == []
