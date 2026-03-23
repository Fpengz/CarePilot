"""
Implement medication use cases.

This module provides workflows for medication regimens, adherence events,
and adherence metrics.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, date, datetime, time
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from apps.api.carepilot_api.deps import AppContext
from care_pilot.core.contracts.api.meal_health import (
    MedicationAdherenceEventCreateRequest,
    MedicationAdherenceEventEnvelopeResponse,
    MedicationAdherenceEventResponse,
    MedicationAdherenceMetricsResponse,
    MedicationAdherenceTotalsResponse,
    MedicationDraftDeleteResponse,
    MedicationDraftInstructionUpdateRequest,
    MedicationIntakeConfirmRequest,
    MedicationIntakeResponse,
    MedicationIntakeSourceResponse,
    MedicationIntakeTextRequest,
    MedicationRegimenCreateRequest,
    MedicationRegimenDeleteResponse,
    MedicationRegimenEnvelopeResponse,
    MedicationRegimenListResponse,
    MedicationRegimenPatchRequest,
    MedicationRegimenResponse,
    NormalizedMedicationInstructionResponse,
)
from care_pilot.core.contracts.api.notifications import ScheduledReminderNotificationItemResponse
from care_pilot.core.errors import build_api_error
from care_pilot.features.companion.core.health.models import (
    MedicationAdherenceEvent,
    MedicationAdherenceMetrics,
)
from care_pilot.features.medications.domain import generate_daily_reminders
from care_pilot.features.medications.intake import (
    build_plain_text_source,
    extract_upload_source,
    parse_medication_instructions,
)
from care_pilot.features.medications.intake.models import (
    MedicationInferenceEngineProtocol,
    MedicationIntakeDraft,
    MedicationIntakeParseResult,
    NormalizedMedicationInstruction,
)
from care_pilot.features.profiles.domain.models import MealSlot
from care_pilot.features.reminders.domain.models import MedicationRegimen, ReminderEvent
from care_pilot.features.reminders.notifications.reminder_materialization import (
    cancel_reminder_notifications,
    materialize_reminder_notifications,
)
from care_pilot.features.workflows.trace_emitter import WorkflowTraceContext, WorkflowTraceEmitter
from care_pilot.platform.auth.session_context import build_user_profile_from_session
from care_pilot.platform.observability.workflows.domain.models import WorkflowName

_DOSAGE_TEXT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|unit|units)\b", re.IGNORECASE)
_GENERIC_MEDICATION_NAMES = {
    "tablet",
    "tablets",
    "medicine",
    "medication",
    "pill",
    "pills",
}
_DRAFT_TTL_SECONDS = 3600


def _default_slot_scope(times_per_day: int) -> list[MealSlot]:
    if times_per_day >= 3:
        return ["breakfast", "lunch", "dinner"]
    if times_per_day == 2:
        return ["breakfast", "dinner"]
    return ["breakfast"]


def _parse_hhmm(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    hh, mm = raw.split(":", 1)
    hour = int(hh)
    minute = int(mm)
    time(hour=hour, minute=minute)
    return f"{hour:02d}:{minute:02d}"


def _to_regimen_response(
    regimen: MedicationRegimen,
) -> MedicationRegimenResponse:
    return MedicationRegimenResponse.model_validate(regimen.model_dump(mode="json"))


def _to_adherence_response(
    event: MedicationAdherenceEvent,
) -> MedicationAdherenceEventResponse:
    return MedicationAdherenceEventResponse.model_validate(event.model_dump(mode="json"))


def _to_notification_response(
    item: object,
) -> ScheduledReminderNotificationItemResponse:
    payload = cast(Any, item).model_dump(mode="json") if hasattr(item, "model_dump") else item
    return ScheduledReminderNotificationItemResponse.model_validate(payload)


def _to_instruction_response(
    item: NormalizedMedicationInstruction,
) -> NormalizedMedicationInstructionResponse:
    return NormalizedMedicationInstructionResponse.model_validate(item.model_dump(mode="json"))


def _session_timezone(*, context: AppContext, user_id: str) -> str:
    profile = context.stores.profiles.get_health_profile(user_id)
    if profile is not None and profile.meal_schedule:
        zone = profile.meal_schedule[0].timezone
        if zone:
            return zone
    return context.settings.app.timezone


def _today_for_timezone(value: str) -> date:
    return datetime.now(ZoneInfo(value)).date()


def _ranges_overlap(
    *,
    left_start: date | None,
    left_end: date | None,
    right_start: date | None,
    right_end: date | None,
) -> bool:
    left_range_start = left_start or date.min
    left_range_end = left_end or date.max
    right_range_start = right_start or date.min
    right_range_end = right_end or date.max
    return left_range_start <= right_range_end and right_range_start <= left_range_end


def _same_schedule_signature(left: MedicationRegimen, right: MedicationRegimen) -> bool:
    return (
        left.canonical_name == right.canonical_name
        and left.dosage_text == right.dosage_text
        and left.timing_type == right.timing_type
        and left.frequency_type == right.frequency_type
        and left.frequency_times_per_day == right.frequency_times_per_day
        and left.offset_minutes == right.offset_minutes
        and left.slot_scope == right.slot_scope
        and left.fixed_time == right.fixed_time
        and left.time_rules == right.time_rules
    )


def _find_duplicate_regimen(
    *,
    context: AppContext,
    user_id: str,
    candidate: MedicationRegimen,
    exclude_regimen_id: str | None = None,
) -> MedicationRegimen | None:
    for item in context.stores.medications.list_medication_regimens(user_id):
        if exclude_regimen_id and item.id == exclude_regimen_id:
            continue
        if not item.active or not candidate.active:
            continue
        if not _same_schedule_signature(item, candidate):
            continue
        if _ranges_overlap(
            left_start=item.start_date,
            left_end=item.end_date,
            right_start=candidate.start_date,
            right_end=candidate.end_date,
        ):
            return item
    return None


def _matching_existing_regimen(
    *,
    context: AppContext,
    user_id: str,
    instruction: NormalizedMedicationInstruction,
    instructions_text: str,
    source_type: str,
    source_filename: str | None,
    source_hash: str | None,
) -> MedicationRegimen | None:
    for item in context.stores.medications.list_medication_regimens(user_id):
        if item.source_hash and item.source_hash == source_hash:
            return item
        if (
            item.medication_name == instruction.medication_name_raw
            and item.dosage_text == instruction.dosage_text
            and item.instructions_text == instructions_text
            and item.source_type == source_type
            and item.source_filename == source_filename
        ):
            return item
    return None


def _build_regimen_from_instruction(
    *,
    regimen_id: str,
    user_id: str,
    timezone_name: str,
    source_type: str,
    source_filename: str | None,
    source_hash: str | None,
    instructions_text: str,
    instruction: NormalizedMedicationInstruction,
) -> MedicationRegimen:
    slot_scope = list(instruction.slot_scope)
    if instruction.timing_type in {"pre_meal", "post_meal"} and not slot_scope:
        slot_scope = _default_slot_scope(max(1, instruction.frequency_times_per_day))
    return MedicationRegimen(
        id=regimen_id,
        user_id=user_id,
        medication_name=instruction.medication_name_raw,
        canonical_name=instruction.medication_name_canonical,
        dosage_text=instruction.dosage_text,
        timing_type=instruction.timing_type,
        frequency_type=instruction.frequency_type,
        frequency_times_per_day=instruction.frequency_times_per_day,
        time_rules=instruction.time_rules,
        offset_minutes=instruction.offset_minutes,
        slot_scope=slot_scope,
        fixed_time=instruction.fixed_time,
        max_daily_doses=max(1, instruction.frequency_times_per_day),
        instructions_text=instructions_text,
        source_type=source_type,  # type: ignore[arg-type]
        source_filename=source_filename,
        source_hash=source_hash,
        start_date=instruction.start_date,
        end_date=instruction.end_date,
        timezone=timezone_name,
        parse_confidence=instruction.confidence,
        active=True,
    )


def _build_intake_user_profile(*, context: AppContext, user_id: str):
    return build_user_profile_from_session(
        {
            "user_id": user_id,
            "display_name": user_id,
            "account_role": "member",
            "profile_mode": "self",
        },
        context.stores.profiles,
    )


def _validate_intake_parse_result(
    *,
    parse_result: MedicationIntakeParseResult,
    allow_ambiguous: bool,
) -> None:
    review_required = any(
        (not item.dosage_text)
        or item.confidence < 0.75
        or any("could not determine" in detail.lower() for detail in item.ambiguities)
        for item in parse_result.instructions
    )
    if review_required and not allow_ambiguous:
        raise build_api_error(
            status_code=422,
            code="medications.intake_review_required",
            message="medication instructions require review before activation",
            details={
                "source_hash": parse_result.source.source_hash,
                "ambiguities": [
                    item.ambiguities for item in parse_result.instructions if item.ambiguities
                ],
            },
        )


def _instruction_is_actionable(
    instruction: NormalizedMedicationInstruction,
) -> bool:
    if not instruction.dosage_text or not _DOSAGE_TEXT_RE.search(instruction.dosage_text):
        return False
    if any("could not determine" in detail.lower() for detail in instruction.ambiguities):
        return False
    if instruction.confidence < 0.75:
        return False
    if instruction.timing_type == "fixed_time" and not instruction.fixed_time:
        return False
    if instruction.timing_type in {"pre_meal", "post_meal"} and not instruction.slot_scope:
        return False
    return instruction.medication_name_raw.strip().lower() not in _GENERIC_MEDICATION_NAMES


def _apply_user_confirmation(
    instruction: NormalizedMedicationInstruction,
) -> NormalizedMedicationInstruction:
    if not instruction.medication_name_raw.strip() or not instruction.dosage_text:
        return instruction
    if instruction.timing_type == "fixed_time" and not instruction.fixed_time:
        return instruction
    if instruction.timing_type in {"pre_meal", "post_meal"} and not instruction.slot_scope:
        return instruction
    return instruction.model_copy(
        update={
            "ambiguities": [],
            "confidence": max(instruction.confidence, 0.9),
        }
    )


def _draft_cache_key(*, user_id: str, draft_id: str) -> str:
    return f"medication-intake-draft:{user_id}:{draft_id}"


def _store_intake_draft(
    *,
    context: AppContext,
    user_id: str,
    timezone_name: str,
    parse_result: MedicationIntakeParseResult,
) -> MedicationIntakeDraft:
    draft = MedicationIntakeDraft(
        draft_id=str(uuid4()),
        user_id=user_id,
        timezone_name=timezone_name,
        source=parse_result.source,
        instructions=parse_result.instructions,
    )
    context.cache_store.set_json(
        _draft_cache_key(user_id=user_id, draft_id=draft.draft_id),
        draft.model_dump(mode="json"),
        ttl_seconds=_DRAFT_TTL_SECONDS,
    )
    return draft


def _load_intake_draft(
    *, context: AppContext, user_id: str, draft_id: str
) -> MedicationIntakeDraft:
    payload = context.cache_store.get_json(_draft_cache_key(user_id=user_id, draft_id=draft_id))
    if payload is None:
        raise build_api_error(
            status_code=404,
            code="medications.intake_draft_not_found",
            message="medication intake draft not found",
        )
    draft = MedicationIntakeDraft.model_validate(payload)
    if draft.user_id != user_id:
        raise build_api_error(
            status_code=404,
            code="medications.intake_draft_not_found",
            message="medication intake draft not found",
        )
    return draft


def _delete_intake_draft(*, context: AppContext, user_id: str, draft_id: str) -> None:
    context.cache_store.delete(_draft_cache_key(user_id=user_id, draft_id=draft_id))


def _save_intake_draft(
    *, context: AppContext, draft: MedicationIntakeDraft
) -> MedicationIntakeDraft:
    context.cache_store.set_json(
        _draft_cache_key(user_id=draft.user_id, draft_id=draft.draft_id),
        draft.model_dump(mode="json"),
        ttl_seconds=_DRAFT_TTL_SECONDS,
    )
    return draft


def _build_preview_response(*, draft: MedicationIntakeDraft) -> MedicationIntakeResponse:
    return MedicationIntakeResponse(
        draft_id=draft.draft_id,
        source=MedicationIntakeSourceResponse.model_validate(draft.source.model_dump(mode="json")),
        normalized_instructions=[_to_instruction_response(item) for item in draft.instructions],
        regimens=[],
        reminders=[],
        scheduled_notifications=[],
    )


def _draft_instruction_at(*, draft: MedicationIntakeDraft, instruction_index: int) -> None:
    if instruction_index < 0 or instruction_index >= len(draft.instructions):
        raise build_api_error(
            status_code=404,
            code="medications.intake_instruction_not_found",
            message="medication draft instruction not found",
        )


def _run_parsed_intake(
    *,
    context: AppContext,
    user_id: str,
    draft_id: str,
    parse_result: MedicationIntakeParseResult,
    timezone_name: str,
    today: date,
) -> MedicationIntakeResponse:
    regimens: list[MedicationRegimen] = []
    reminders: list[ReminderEvent] = []
    scheduled_notifications: list[object] = []
    user_profile = _build_intake_user_profile(context=context, user_id=user_id)
    existing_reminder_events = context.stores.reminders.list_reminder_events(user_id)

    for instruction in parse_result.instructions:
        if not _instruction_is_actionable(instruction):
            continue
        existing = _matching_existing_regimen(
            context=context,
            user_id=user_id,
            instruction=instruction,
            instructions_text=parse_result.source.extracted_text,
            source_type=parse_result.source.source_type,
            source_filename=parse_result.source.filename,
            source_hash=parse_result.source.source_hash,
        )
        regimen = existing or _build_regimen_from_instruction(
            regimen_id=str(uuid4()),
            user_id=user_id,
            timezone_name=timezone_name,
            source_type=parse_result.source.source_type,
            source_filename=parse_result.source.filename,
            source_hash=parse_result.source.source_hash,
            instructions_text=parse_result.source.extracted_text,
            instruction=instruction,
        )
        if existing is None:
            duplicate = _find_duplicate_regimen(context=context, user_id=user_id, candidate=regimen)
            if duplicate is not None:
                regimen = duplicate
            else:
                context.stores.medications.save_medication_regimen(regimen)
        if all(item.id != regimen.id for item in regimens):
            regimens.append(regimen)

        current = [
            item
            for item in existing_reminder_events
            if item.regimen_id == regimen.id and item.scheduled_at.date() == today
        ]
        if not current:
            current = generate_daily_reminders(user_profile, [regimen], today)
            for reminder in current:
                context.stores.reminders.save_reminder_event(reminder)
                scheduled_notifications.extend(
                    materialize_reminder_notifications(
                        repository=context.stores.reminders,
                        reminder_event=reminder,
                        reminder_type=reminder.reminder_type,
                        event_timeline=context.event_timeline,
                    )
                )
        else:
            for reminder in current:
                scheduled_notifications.extend(
                    context.stores.reminders.list_scheduled_notifications(reminder_id=reminder.id)
                )
        reminders.extend(current)

    if regimens:
        context.event_timeline.append(
            event_type="medication_logged",
            workflow_name="medication_intake",
            correlation_id=draft_id,
            request_id=None,
            user_id=user_id,
            payload={
                "regimen_count": len(regimens),
                "regimen_ids": [item.id for item in regimens],
                "source_hash": parse_result.source.source_hash,
            },
        )
    if reminders:
        context.event_timeline.append(
            event_type="reminder_scheduled",
            workflow_name="medication_intake",
            correlation_id=draft_id,
            request_id=None,
            user_id=user_id,
            payload={
                "reminder_count": len(reminders),
                "reminder_type": reminders[0].reminder_type if reminders else None,
            },
        )

    return MedicationIntakeResponse(
        draft_id=draft_id,
        source=MedicationIntakeSourceResponse.model_validate(
            parse_result.source.model_dump(mode="json")
        ),
        normalized_instructions=[
            _to_instruction_response(item) for item in parse_result.instructions
        ],
        regimens=[_to_regimen_response(item) for item in regimens],
        reminders=list(reminders),
        scheduled_notifications=[
            _to_notification_response(item) for item in scheduled_notifications
        ],
    )


def list_regimens_for_session(
    *, context: AppContext, user_id: str
) -> MedicationRegimenListResponse:
    items = context.stores.medications.list_medication_regimens(user_id)
    return MedicationRegimenListResponse(items=[_to_regimen_response(item) for item in items])


def create_regimen_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: MedicationRegimenCreateRequest,
) -> MedicationRegimenEnvelopeResponse:
    fixed_time = _parse_hhmm(payload.fixed_time)
    if payload.timing_type == "fixed_time" and fixed_time is None:
        raise build_api_error(
            status_code=400,
            code="medications.invalid_fixed_time",
            message="fixed_time is required for fixed_time regimens",
        )
    regimen = MedicationRegimen(
        id=str(uuid4()),
        user_id=user_id,
        medication_name=payload.medication_name.strip(),
        canonical_name=(payload.canonical_name or payload.medication_name.strip())
        .lower()
        .replace(" ", "_"),
        dosage_text=payload.dosage_text.strip(),
        timing_type=payload.timing_type,
        frequency_type=payload.frequency_type,
        frequency_times_per_day=payload.frequency_times_per_day,
        time_rules=list(payload.time_rules),
        offset_minutes=payload.offset_minutes,
        slot_scope=list(payload.slot_scope),
        fixed_time=fixed_time,
        max_daily_doses=payload.max_daily_doses,
        instructions_text=payload.instructions_text,
        source_type=payload.source_type,
        source_filename=payload.source_filename,
        source_hash=None,
        start_date=payload.start_date,
        end_date=payload.end_date,
        timezone=payload.timezone,
        parse_confidence=payload.parse_confidence,
        active=payload.active,
    )
    duplicate = _find_duplicate_regimen(context=context, user_id=user_id, candidate=regimen)
    if duplicate is not None:
        raise build_api_error(
            status_code=409,
            code="medications.duplicate_regimen",
            message="duplicate medication regimen already exists",
            details={"existing_regimen_id": duplicate.id},
        )
    context.stores.medications.save_medication_regimen(regimen)
    context.event_timeline.append(
        event_type="medication_logged",
        workflow_name="medication_regimen",
        correlation_id=regimen.id,
        request_id=None,
        user_id=user_id,
        payload={
            "regimen_id": regimen.id,
            "medication_name": regimen.medication_name,
            "timing_type": regimen.timing_type,
            "frequency_type": regimen.frequency_type,
        },
    )
    return MedicationRegimenEnvelopeResponse(regimen=_to_regimen_response(regimen))


def patch_regimen_for_session(
    *,
    context: AppContext,
    user_id: str,
    regimen_id: str,
    payload: MedicationRegimenPatchRequest,
) -> MedicationRegimenEnvelopeResponse:
    existing = context.stores.medications.get_medication_regimen(
        user_id=user_id, regimen_id=regimen_id
    )
    if existing is None:
        raise build_api_error(
            status_code=404,
            code="medications.not_found",
            message="medication regimen not found",
        )
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise build_api_error(
            status_code=400,
            code="medications.no_changes",
            message="no medication changes requested",
        )
    if "fixed_time" in updates:
        updates["fixed_time"] = _parse_hhmm(payload.fixed_time)
    next_payload = existing.model_dump(mode="json")
    next_payload.update(updates)
    if next_payload.get("timing_type") == "fixed_time" and not next_payload.get("fixed_time"):
        raise build_api_error(
            status_code=400,
            code="medications.invalid_fixed_time",
            message="fixed_time is required for fixed_time regimens",
        )
    updated = MedicationRegimen.model_validate(next_payload)
    duplicate = _find_duplicate_regimen(
        context=context,
        user_id=user_id,
        candidate=updated,
        exclude_regimen_id=existing.id,
    )
    if duplicate is not None:
        raise build_api_error(
            status_code=409,
            code="medications.duplicate_regimen",
            message="duplicate medication regimen already exists",
            details={"existing_regimen_id": duplicate.id},
        )
    context.stores.medications.save_medication_regimen(updated)
    context.event_timeline.append(
        event_type="medication_updated",
        workflow_name="medication_regimen",
        correlation_id=updated.id,
        request_id=None,
        user_id=user_id,
        payload={
            "regimen_id": updated.id,
            "medication_name": updated.medication_name,
            "active": updated.active,
        },
    )
    return MedicationRegimenEnvelopeResponse(regimen=_to_regimen_response(updated))


def delete_regimen_for_session(
    *, context: AppContext, user_id: str, regimen_id: str
) -> MedicationRegimenDeleteResponse:
    for event in context.stores.reminders.list_reminder_events(user_id):
        if event.regimen_id == regimen_id:
            cancel_reminder_notifications(repository=context.stores.reminders, reminder_id=event.id)
    deleted = context.stores.medications.delete_medication_regimen(
        user_id=user_id, regimen_id=regimen_id
    )
    context.event_timeline.append(
        event_type="medication_deleted",
        workflow_name="medication_regimen",
        correlation_id=regimen_id,
        request_id=None,
        user_id=user_id,
        payload={"regimen_id": regimen_id, "deleted": deleted},
    )
    return MedicationRegimenDeleteResponse(deleted=deleted)


def record_adherence_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: MedicationAdherenceEventCreateRequest,
) -> MedicationAdherenceEventEnvelopeResponse:
    regimen = context.stores.medications.get_medication_regimen(
        user_id=user_id, regimen_id=payload.regimen_id
    )
    if regimen is None:
        raise build_api_error(
            status_code=404,
            code="medications.not_found",
            message="medication regimen not found",
        )
    event = MedicationAdherenceEvent(
        id=str(uuid4()),
        user_id=user_id,
        regimen_id=payload.regimen_id,
        reminder_id=payload.reminder_id,
        status=payload.status,
        scheduled_at=payload.scheduled_at,
        taken_at=payload.taken_at,
        source=payload.source,
        metadata=payload.metadata,
    )
    saved = context.stores.medications.save_medication_adherence_event(event)
    context.event_timeline.append(
        event_type="adherence_updated",
        workflow_name="medication_adherence",
        correlation_id=event.id,
        request_id=None,
        user_id=user_id,
        payload={
            "regimen_id": event.regimen_id,
            "reminder_id": event.reminder_id,
            "status": event.status,
            "scheduled_at": event.scheduled_at.isoformat() if event.scheduled_at else None,
        },
    )
    return MedicationAdherenceEventEnvelopeResponse(event=_to_adherence_response(saved))


async def _run_medication_agent_proposal(
    *,
    event_timeline: Any,
    correlation_id: str,
    request_id: str | None,
    user_id: str,
    text: str,
) -> None:
    from care_pilot.agent.adapters.shadow_agents import MedicationAgentAdapter
    from care_pilot.agent.core.contracts import AgentRequest
    from care_pilot.agent.runtime.context_builder import build_agent_context

    adapter = MedicationAgentAdapter()
    request = AgentRequest(
        user_id=user_id,
        session_id="medication_intake_agent",
        correlation_id=correlation_id,
        goal="Parse medication instructions",
        inputs={"text_context": text},
    )
    result = await adapter.run(
        request,
        build_agent_context(
            user_id=user_id,
            session_id="medication_intake_agent",
            request_id=request_id,
            correlation_id=correlation_id,
            policy={"allowed_sources": ["medication_text"]},
            selection={"reason": "medication_intake"},
        ),
    )
    response = result.output
    if response is None:
        return
    event_timeline.append(
        event_type="agent_action_proposed",
        workflow_name="medication_intake",
        correlation_id=correlation_id,
        request_id=request_id,
        user_id=user_id,
        payload={
            "agent_name": response.agent_name,
            "status": response.status,
            "confidence": response.confidence,
            "summary_length": len(response.summary or ""),
        },
    )


def _schedule_medication_agent_proposal(
    *,
    event_timeline: Any,
    correlation_id: str,
    request_id: str | None,
    user_id: str,
    text: str,
) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(
            _run_medication_agent_proposal(
                event_timeline=event_timeline,
                correlation_id=correlation_id,
                request_id=request_id,
                user_id=user_id,
                text=text,
            )
        )
        return
    loop.create_task(
        _run_medication_agent_proposal(
            event_timeline=event_timeline,
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=user_id,
            text=text,
        )
    )


def adherence_metrics_for_session(
    *,
    context: AppContext,
    user_id: str,
    from_date: date | None,
    to_date: date | None,
) -> MedicationAdherenceMetricsResponse:
    start_at = datetime.combine(from_date, time.min, tzinfo=UTC) if from_date else None
    end_at = datetime.combine(to_date, time.max, tzinfo=UTC) if to_date else None
    events = context.stores.medications.list_medication_adherence_events(
        user_id=user_id,
        start_at=start_at,
        end_at=end_at,
    )
    taken = sum(1 for item in events if item.status == "taken")
    missed = sum(1 for item in events if item.status == "missed")
    skipped = sum(1 for item in events if item.status == "skipped")
    totals = MedicationAdherenceMetrics(
        events=len(events),
        taken=taken,
        missed=missed,
        skipped=skipped,
        adherence_rate=(taken / len(events)) if events else 0.0,
    )
    return MedicationAdherenceMetricsResponse(
        totals=MedicationAdherenceTotalsResponse.model_validate(totals.model_dump(mode="json")),
        events=[_to_adherence_response(item) for item in events],
    )


async def intake_text_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: MedicationIntakeTextRequest,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> MedicationIntakeResponse:
    started = perf_counter()
    source = build_plain_text_source(payload.instructions_text)
    timezone_name = _session_timezone(context=context, user_id=user_id)
    today = _today_for_timezone(timezone_name)
    trace = WorkflowTraceEmitter(context.event_timeline)
    trace_ctx = WorkflowTraceContext(
        workflow_name=WorkflowName.PRESCRIPTION_INGEST.value,
        correlation_id=correlation_id or str(uuid4()),
        request_id=request_id,
        user_id=user_id,
    )
    trace.workflow_started(
        trace_ctx,
        payload={
            "source_type": source.source_type,
            "source_hash": source.source_hash,
            "filename_present": False,
        },
    )
    try:
        parse_result = await parse_medication_instructions(
            source=source,
            today=today,
            timezone_name=timezone_name,
            inference_engine=cast(
                "MedicationInferenceEngineProtocol",
                context.medication_inference_engine,
            ),
        )
        _validate_intake_parse_result(
            parse_result=parse_result, allow_ambiguous=payload.allow_ambiguous
        )
        draft = _store_intake_draft(
            context=context,
            user_id=user_id,
            timezone_name=timezone_name,
            parse_result=parse_result,
        )
        response = _build_preview_response(draft=draft)
    except Exception as exc:
        error_code = getattr(exc, "code", "medications.intake_failed")
        trace.workflow_failed(
            trace_ctx,
            error_code=str(error_code),
            message="medication intake failed",
            details={
                "source_hash": source.source_hash,
                "source_type": source.source_type,
            },
            duration_ms=(perf_counter() - started) * 1000.0,
        )
        raise
    trace.workflow_completed(
        trace_ctx,
        payload={
            "source_hash": source.source_hash,
            "instructions_count": len(response.normalized_instructions),
            "regimens_count": 0,
            "scheduled_notifications_count": 0,
            "review_mode": payload.allow_ambiguous,
            "draft_id": response.draft_id,
        },
        duration_ms=(perf_counter() - started) * 1000.0,
    )
    _schedule_medication_agent_proposal(
        event_timeline=context.event_timeline,
        correlation_id=trace_ctx.correlation_id,
        request_id=trace_ctx.request_id,
        user_id=user_id,
        text=parse_result.source.extracted_text,
    )
    return response


async def intake_upload_for_session(
    *,
    context: AppContext,
    user_id: str,
    filename: str,
    mime_type: str,
    content: bytes,
    allow_ambiguous: bool = False,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> MedicationIntakeResponse:
    started = perf_counter()
    source = extract_upload_source(filename=filename, mime_type=mime_type, content=content)
    timezone_name = _session_timezone(context=context, user_id=user_id)
    today = _today_for_timezone(timezone_name)
    trace = WorkflowTraceEmitter(context.event_timeline)
    trace_ctx = WorkflowTraceContext(
        workflow_name=WorkflowName.PRESCRIPTION_INGEST.value,
        correlation_id=correlation_id or str(uuid4()),
        request_id=request_id,
        user_id=user_id,
    )
    trace.workflow_started(
        trace_ctx,
        payload={
            "source_type": source.source_type,
            "source_hash": source.source_hash,
            "filename_present": True,
            "mime_type": mime_type,
        },
    )
    try:
        parse_result = await parse_medication_instructions(
            source=source,
            today=today,
            timezone_name=timezone_name,
            inference_engine=cast(
                "MedicationInferenceEngineProtocol",
                context.medication_inference_engine,
            ),
        )
        _validate_intake_parse_result(parse_result=parse_result, allow_ambiguous=allow_ambiguous)
        draft = _store_intake_draft(
            context=context,
            user_id=user_id,
            timezone_name=timezone_name,
            parse_result=parse_result,
        )
        response = _build_preview_response(draft=draft)
    except Exception as exc:
        error_code = getattr(exc, "code", "medications.intake_failed")
        trace.workflow_failed(
            trace_ctx,
            error_code=str(error_code),
            message="medication intake failed",
            details={
                "source_hash": source.source_hash,
                "source_type": source.source_type,
                "mime_type": mime_type,
            },
            duration_ms=(perf_counter() - started) * 1000.0,
        )
        raise
    trace.workflow_completed(
        trace_ctx,
        payload={
            "source_hash": source.source_hash,
            "instructions_count": len(response.normalized_instructions),
            "regimens_count": 0,
            "scheduled_notifications_count": 0,
            "review_mode": allow_ambiguous,
            "draft_id": response.draft_id,
        },
        duration_ms=(perf_counter() - started) * 1000.0,
    )
    _schedule_medication_agent_proposal(
        event_timeline=context.event_timeline,
        correlation_id=trace_ctx.correlation_id,
        request_id=trace_ctx.request_id,
        user_id=user_id,
        text=parse_result.source.extracted_text,
    )
    return response


def confirm_intake_for_session(
    *,
    context: AppContext,
    user_id: str,
    payload: MedicationIntakeConfirmRequest,
) -> MedicationIntakeResponse:
    context.event_timeline.append(
        event_type="workflow_started",
        workflow_name="medication_intake_confirm",
        correlation_id=payload.draft_id,
        request_id=None,
        user_id=user_id,
        payload={"draft_id": payload.draft_id},
    )
    draft = _load_intake_draft(context=context, user_id=user_id, draft_id=payload.draft_id)
    if any(not _instruction_is_actionable(item) for item in draft.instructions):
        raise build_api_error(
            status_code=422,
            code="medications.intake_review_required",
            message="medication instructions require review before activation",
            details={
                "source_hash": draft.source.source_hash,
                "ambiguities": [
                    item.ambiguities for item in draft.instructions if item.ambiguities
                ],
            },
        )
    parse_result = MedicationIntakeParseResult(source=draft.source, instructions=draft.instructions)
    today = _today_for_timezone(draft.timezone_name)
    response = _run_parsed_intake(
        context=context,
        user_id=user_id,
        draft_id=draft.draft_id,
        parse_result=parse_result,
        timezone_name=draft.timezone_name,
        today=today,
    )
    _delete_intake_draft(context=context, user_id=user_id, draft_id=draft.draft_id)
    context.event_timeline.append(
        event_type="workflow_completed",
        workflow_name="medication_intake_confirm",
        correlation_id=payload.draft_id,
        request_id=None,
        user_id=user_id,
        payload={
            "draft_id": payload.draft_id,
            "regimen_count": len(response.regimens),
            "reminder_count": len(response.reminders),
        },
    )
    return response


def update_draft_instruction_for_session(
    *,
    context: AppContext,
    user_id: str,
    draft_id: str,
    instruction_index: int,
    payload: MedicationDraftInstructionUpdateRequest,
) -> MedicationIntakeResponse:
    draft = _load_intake_draft(context=context, user_id=user_id, draft_id=draft_id)
    _draft_instruction_at(draft=draft, instruction_index=instruction_index)
    updated = NormalizedMedicationInstruction.model_validate(payload.model_dump(mode="json"))
    draft.instructions[instruction_index] = _apply_user_confirmation(updated)
    saved = _save_intake_draft(context=context, draft=draft)
    return _build_preview_response(draft=saved)


def delete_draft_instruction_for_session(
    *,
    context: AppContext,
    user_id: str,
    draft_id: str,
    instruction_index: int,
) -> MedicationIntakeResponse:
    draft = _load_intake_draft(context=context, user_id=user_id, draft_id=draft_id)
    _draft_instruction_at(draft=draft, instruction_index=instruction_index)
    remaining = [
        item for index, item in enumerate(draft.instructions) if index != instruction_index
    ]
    saved = _save_intake_draft(
        context=context,
        draft=draft.model_copy(update={"instructions": remaining}),
    )
    return _build_preview_response(draft=saved)


def cancel_intake_draft_for_session(
    *,
    context: AppContext,
    user_id: str,
    draft_id: str,
) -> MedicationDraftDeleteResponse:
    _load_intake_draft(context=context, user_id=user_id, draft_id=draft_id)
    _delete_intake_draft(context=context, user_id=user_id, draft_id=draft_id)
    return MedicationDraftDeleteResponse()
