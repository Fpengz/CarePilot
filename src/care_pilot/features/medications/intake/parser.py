"""Medication instruction parsing with LLM-first extraction and deterministic fallback."""

from __future__ import annotations

from datetime import date, timedelta
import logging
import re
from typing import cast

from care_pilot.agent.runtime.inference_types import (
    InferenceModality,
    InferenceRequest,
    InferenceResponse,
)
from care_pilot.config.llm import LLMCapability
from care_pilot.features.profiles.domain.models import MealSlot

from .models import (
    LLMNormalizedMedicationInstruction,
    MedicationFrequencyType,
    MedicationInferenceEngineProtocol,
    MedicationIntakeParseResult,
    MedicationIntakeSource,
    MedicationParseOutputLoose,
    MedicationTimingType,
    NormalizedMedicationInstruction,
)

logger = logging.getLogger(__name__)

_DOSAGE_RE = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9/-]*(?:\s+[A-Za-z][A-Za-z0-9/-]*)?)\s+(?P<dose>\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml))",
    re.IGNORECASE,
)
_TIME_RE = re.compile(r"\b(?P<hour>\d{1,2}):(?P<minute>\d{2})\b")
_DURATION_RE = re.compile(r"\bfor\s+(?P<days>\d+)\s+days?\b", re.IGNORECASE)

_SYSTEM_PROMPT = """\
You extract structured medication instructions from user-provided medication instructions.

Return JSON only using this wrapper schema:
{
  "instructions": [<instruction objects>],
  "confidence_score": 0.0-1.0,
  "warnings": ["..."]
}

Do not include markdown fences or any explanations.

Each instruction object must contain:
- medication_name_raw
- medication_name_canonical (snake_case generic name when known, else normalized lowercase token)
- dosage_text
- timing_type: pre_meal | post_meal | fixed_time
- frequency_type: times_per_day | fixed_slots | fixed_time
- frequency_times_per_day
- offset_minutes
- slot_scope: any of breakfast, lunch, dinner, snack
- fixed_time in HH:MM when exact or confidently defaulted
- time_rules as structured dictionaries
- duration_days when given
- start_date and end_date in YYYY-MM-DD when known or derived
- confidence from 0 to 1
- ambiguities when details are missing or inferred

Rules:
- "every morning" defaults to 08:00 fixed_time.
- "bedtime" defaults to 22:00 fixed_time.
- "twice daily before meals" defaults to breakfast and dinner, offset 30 minutes.
- "after meals" defaults to 15 minutes after meal windows.
- If the instruction is ambiguous, keep the best structured guess but explain the ambiguity.
- Do not invent medication names or strengths not supported by the text.
"""


def _statement_chunks(text: str) -> list[str]:
    parts = [item.strip() for item in re.split(r"[\n;]+", text) if item.strip()]
    return parts or [text.strip()]


def _normalize_name(raw: str) -> str:
    cleaned = re.sub(
        r"^(take|tab|tablet|capsule|capsules)\s+",
        "",
        raw.strip(),
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip().title()


def _canonical_name(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip().lower())


def _frequency_times(text: str) -> int:
    lowered = text.lower()
    if any(
        token in lowered
        for token in (
            "three times a day",
            "three times daily",
            "3 times a day",
            "tid",
        )
    ):
        return 3
    if any(token in lowered for token in ("twice daily", "twice a day", "two times a day", "bid")):
        return 2
    return 1


def _explicit_slots(text: str) -> list[MealSlot]:
    lowered = text.lower()
    slots: list[MealSlot] = []
    for token, slot in (
        ("breakfast", "breakfast"),
        ("lunch", "lunch"),
        ("dinner", "dinner"),
        ("snack", "snack"),
    ):
        if token in lowered:
            slots.append(slot)
    return slots


def _default_slots(times_per_day: int) -> list[MealSlot]:
    if times_per_day >= 3:
        return ["breakfast", "lunch", "dinner"]
    if times_per_day == 2:
        return ["breakfast", "dinner"]
    return ["breakfast"]


def _fixed_time_from_text(text: str) -> str | None:
    match = _TIME_RE.search(text)
    if match:
        return f"{int(match.group('hour')):02d}:{int(match.group('minute')):02d}"
    lowered = text.lower()
    if "bedtime" in lowered:
        return "22:00"
    if "every evening" in lowered or "every night" in lowered:
        return "20:00"
    if "every morning" in lowered or "morning" in lowered:
        return "08:00"
    return None


def _duration_days(text: str) -> int | None:
    match = _DURATION_RE.search(text)
    return int(match.group("days")) if match else None


def _normalize_instruction_dates(
    instruction: NormalizedMedicationInstruction, *, today: date
) -> NormalizedMedicationInstruction:
    start_date = instruction.start_date or today
    duration_days = instruction.duration_days
    end_date = instruction.end_date
    if end_date is None and duration_days:
        end_date = start_date + timedelta(days=duration_days - 1)

    canonical = instruction.medication_name_canonical or _canonical_name(
        instruction.medication_name_raw
    )
    confidence = min(max(float(instruction.confidence), 0.0), 1.0)
    fixed_time = instruction.fixed_time
    ambiguities = list(instruction.ambiguities)

    if instruction.timing_type == "fixed_time" and not fixed_time:
        fixed_time = "08:00"
        if (
            "No exact administration time was provided; default morning time was used."
            not in ambiguities
        ):
            ambiguities.append(
                "No exact administration time was provided; default morning time was used."
            )

    return instruction.model_copy(
        update={
            "medication_name_raw": _normalize_name(instruction.medication_name_raw),
            "medication_name_canonical": canonical,
            "start_date": start_date,
            "end_date": end_date,
            "fixed_time": fixed_time,
            "confidence": confidence,
            "ambiguities": ambiguities,
        }
    )


def _coerce_llm_instruction(
    instruction: LLMNormalizedMedicationInstruction,
    *,
    default_confidence: float,
) -> NormalizedMedicationInstruction:
    ambiguities = list(instruction.ambiguities or [])
    slot_scope = list(instruction.slot_scope or [])
    time_rules = list(instruction.time_rules or [])
    confidence = (
        instruction.confidence if instruction.confidence is not None else default_confidence
    )
    timing_type = instruction.timing_type or "fixed_time"
    frequency_type = instruction.frequency_type or "fixed_time"
    frequency_times_per_day = instruction.frequency_times_per_day

    if timing_type not in {"pre_meal", "post_meal", "fixed_time"}:
        ambiguities.append("Timing type was invalid; defaulted to fixed_time.")
        timing_type = "fixed_time"

    if frequency_type not in {"times_per_day", "fixed_slots", "fixed_time"}:
        if slot_scope:
            frequency_type = "fixed_slots"
            ambiguities.append("Frequency type inferred from slot scope.")
        elif frequency_times_per_day and frequency_times_per_day > 1:
            frequency_type = "times_per_day"
            ambiguities.append("Frequency type inferred from times per day.")
        else:
            frequency_type = "fixed_time"
            ambiguities.append("Frequency type defaulted to fixed_time.")

    if frequency_times_per_day is None:
        if frequency_type == "fixed_slots":
            frequency_times_per_day = max(1, len(slot_scope))
        elif frequency_type == "times_per_day":
            frequency_times_per_day = 2
            ambiguities.append("Frequency times per day defaulted to 2.")
        else:
            frequency_times_per_day = 1

    return NormalizedMedicationInstruction(
        medication_name_raw=instruction.medication_name_raw,
        medication_name_canonical=instruction.medication_name_canonical,
        dosage_text=instruction.dosage_text,
        timing_type=cast(MedicationTimingType, timing_type),
        frequency_type=cast(MedicationFrequencyType, frequency_type),
        frequency_times_per_day=frequency_times_per_day,
        offset_minutes=instruction.offset_minutes or 0,
        slot_scope=slot_scope,
        fixed_time=instruction.fixed_time,
        time_rules=time_rules,
        duration_days=instruction.duration_days,
        start_date=instruction.start_date,
        end_date=instruction.end_date,
        confidence=confidence,
        ambiguities=ambiguities,
    )


def _build_instruction(statement: str, today: date) -> NormalizedMedicationInstruction:
    dosage_match = _DOSAGE_RE.search(statement)
    ambiguities: list[str] = []
    if dosage_match is None:
        ambiguities.append("Could not determine medication name and dosage.")
        return NormalizedMedicationInstruction(
            medication_name_raw=statement.strip(),
            dosage_text="",
            timing_type="fixed_time",
            confidence=0.0,
            ambiguities=ambiguities,
        )

    medication_name = _normalize_name(dosage_match.group("name"))
    dosage_text = dosage_match.group("dose").replace(" ", "")
    frequency_times_per_day = _frequency_times(statement)
    duration_days = _duration_days(statement)
    start_date = today
    end_date = today + timedelta(days=duration_days - 1) if duration_days else None
    lowered = statement.lower()

    if "before meals" in lowered or "before meal" in lowered:
        slots = _explicit_slots(statement) or _default_slots(frequency_times_per_day)
        return NormalizedMedicationInstruction(
            medication_name_raw=medication_name,
            medication_name_canonical=_canonical_name(medication_name),
            dosage_text=dosage_text,
            timing_type="pre_meal",
            frequency_type="fixed_slots",
            frequency_times_per_day=len(slots),
            offset_minutes=30,
            slot_scope=slots,
            time_rules=[{"kind": "before_meal", "slots": slots, "offset_minutes": 30}],
            duration_days=duration_days,
            start_date=start_date,
            end_date=end_date,
            confidence=0.92,
        )

    if "after meals" in lowered or "after meal" in lowered:
        slots = _explicit_slots(statement) or _default_slots(frequency_times_per_day)
        return NormalizedMedicationInstruction(
            medication_name_raw=medication_name,
            medication_name_canonical=_canonical_name(medication_name),
            dosage_text=dosage_text,
            timing_type="post_meal",
            frequency_type="fixed_slots",
            frequency_times_per_day=len(slots),
            offset_minutes=15,
            slot_scope=slots,
            time_rules=[{"kind": "after_meal", "slots": slots, "offset_minutes": 15}],
            duration_days=duration_days,
            start_date=start_date,
            end_date=end_date,
            confidence=0.92,
        )

    fixed_time = _fixed_time_from_text(statement)
    if fixed_time is None and frequency_times_per_day > 1:
        ambiguities.append(
            "No exact reminder times were provided; default meal slots were inferred."
        )
        slots = _default_slots(frequency_times_per_day)
        return NormalizedMedicationInstruction(
            medication_name_raw=medication_name,
            medication_name_canonical=_canonical_name(medication_name),
            dosage_text=dosage_text,
            timing_type="pre_meal" if "meal" in lowered else "fixed_time",
            frequency_type=("fixed_slots" if "meal" in lowered else "times_per_day"),
            frequency_times_per_day=frequency_times_per_day,
            offset_minutes=30 if "meal" in lowered else 0,
            slot_scope=slots if "meal" in lowered else [],
            fixed_time=None,
            time_rules=[{"kind": "inferred_slots", "slots": slots}],
            duration_days=duration_days,
            start_date=start_date,
            end_date=end_date,
            confidence=0.7,
            ambiguities=ambiguities,
        )

    fixed_time = fixed_time or "08:00"
    label = "morning" if fixed_time == "08:00" else "fixed_time"
    confidence = 0.9 if _fixed_time_from_text(statement) else 0.75
    if confidence < 0.8:
        ambiguities.append(
            "No exact administration time was provided; default morning time was used."
        )
    return NormalizedMedicationInstruction(
        medication_name_raw=medication_name,
        medication_name_canonical=_canonical_name(medication_name),
        dosage_text=dosage_text,
        timing_type="fixed_time",
        frequency_type="fixed_time",
        frequency_times_per_day=1,
        fixed_time=fixed_time,
        time_rules=[{"kind": "fixed_time", "time_local": fixed_time, "label": label}],
        duration_days=duration_days,
        start_date=start_date,
        end_date=end_date,
        confidence=confidence,
        ambiguities=ambiguities,
    )


def _parse_deterministic(
    *, source: MedicationIntakeSource, today: date
) -> MedicationIntakeParseResult:
    instructions = [
        _build_instruction(statement, today)
        for statement in _statement_chunks(source.extracted_text)
        if statement.strip()
    ]
    return MedicationIntakeParseResult(source=source, instructions=instructions)


async def _parse_with_llm(
    *,
    source: MedicationIntakeSource,
    today: date,
    timezone_name: str,
    inference_engine: MedicationInferenceEngineProtocol,
) -> MedicationIntakeParseResult:
    request = InferenceRequest(
        request_id=f"medication-parse-{source.source_hash[:12]}",
        user_id=None,
        modality=InferenceModality.TEXT,
        payload={
            "prompt": (
                "Parse these medication instructions into structured medication instructions.\n"
                f"Today: {today.isoformat()}\n"
                f"Timezone: {timezone_name}\n"
                f"Source type: {source.source_type}\n"
                f"Medication instructions:\n{source.extracted_text}"
            )
        },
        safety_context={"contains_healthcare_data": True},
        runtime_profile={"capability": LLMCapability.MEDICATION_PARSE.value},
        trace_context={
            "source_hash": source.source_hash,
            "source_type": source.source_type,
        },
        output_schema=MedicationParseOutputLoose,
        system_prompt=_SYSTEM_PROMPT,
    )
    response = cast(InferenceResponse, await inference_engine.infer(request))
    output = cast(MedicationParseOutputLoose, response.structured_output)
    normalized = [
        _normalize_instruction_dates(
            _coerce_llm_instruction(item, default_confidence=output.confidence_score),
            today=today,
        )
        for item in output.instructions
    ]
    return MedicationIntakeParseResult(source=source, instructions=normalized)


async def parse_medication_instructions(
    *,
    source: MedicationIntakeSource,
    today: date,
    timezone_name: str = "Asia/Singapore",
    inference_engine: MedicationInferenceEngineProtocol | None = None,
) -> MedicationIntakeParseResult:
    provider_name = (
        getattr(inference_engine, "provider", None) if inference_engine is not None else None
    )
    if inference_engine is not None and provider_name != "test":
        try:
            parsed = await _parse_with_llm(
                source=source,
                today=today,
                timezone_name=timezone_name,
                inference_engine=inference_engine,
            )
            if parsed.instructions:
                return parsed
        except Exception:  # noqa: BLE001
            logger.exception(
                "medication_intake_llm_parse_failed source_type=%s source_hash=%s",
                source.source_type,
                source.source_hash,
            )
    return _parse_deterministic(source=source, today=today)
