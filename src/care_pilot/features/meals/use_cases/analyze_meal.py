"""Meal analysis workflow entrypoints."""

from __future__ import annotations

import asyncio
import time

from care_pilot.features.meals.deps import MealDeps
from care_pilot.features.meals.logging import (
    build_meal_analysis_log_payload,
    log_meal_analysis_event,
    resolve_meal_analysis_model_name,
)
from care_pilot.features.meals.workflows.meal_upload_graph import (
    MealUploadDeps,
    run_meal_upload_workflow,
)
from care_pilot.features.meals.workflows.meal_upload_output import MealUploadOutput
from care_pilot.features.meals.workflows.meal_upload_state import MealUploadState


def _resolved_log_provider(*, deps: MealDeps, routed_provider: str | None) -> str:
    return routed_provider or str(deps.settings.llm.provider)


async def analyze_meal_upload(
    *,
    deps: MealDeps,
    state: MealUploadState,
) -> tuple[float, MealUploadOutput]:
    """Run the meal upload workflow and return latency + output."""
    analysis_started = time.perf_counter()
    workflow_output = await asyncio.wait_for(
        run_meal_upload_workflow(
            deps=MealUploadDeps(stores=deps.stores, event_timeline=deps.event_timeline),
            state=state,
        ),
        timeout=deps.settings.llm.inference.wall_clock_timeout_seconds,
    )
    latency_ms = (time.perf_counter() - analysis_started) * 1000
    return latency_ms, workflow_output


def log_meal_analysis_completion(
    *,
    deps: MealDeps,
    workflow_output: MealUploadOutput,
    routed_provider: str | None,
    latency_ms: float,
) -> None:
    """Log a normalized meal analysis completion event."""
    output = workflow_output
    vision_result = output.raw_observation.vision_result
    log_provider = vision_result.provider or _resolved_log_provider(
        deps=deps, routed_provider=routed_provider
    )
    log_model = vision_result.model_version or resolve_meal_analysis_model_name(
        deps.settings.llm, log_provider
    )
    meal_id = output.validated_event.event_id if output.validated_event else None
    meal_name = (
        output.validated_event.meal_name
        if output.validated_event
        else output.candidate_record.candidate_event.meal_name
    )
    manual_review = bool(output.confirmation_required)
    risk_tags = (
        output.nutrition_profile.risk_tags
        if output.nutrition_profile is not None
        else output.candidate_record.candidate_event.risk_tags
    )
    log_payload = build_meal_analysis_log_payload(
        user_id=output.raw_observation.user_id,
        request_id=output.candidate_record.request_id,
        correlation_id=output.candidate_record.correlation_id,
        provider=log_provider,
        model_name=log_model,
        observation_id=output.raw_observation.observation_id,
        meal_id=meal_id,
        meal_name=meal_name,
        manual_review=manual_review,
        latency_ms=latency_ms,
        inference_latency_ms=vision_result.processing_latency_ms,
        unresolved_count=len(output.raw_observation.unresolved_conflicts),
        risk_tags=risk_tags,
    )
    log_meal_analysis_event(log_payload)
