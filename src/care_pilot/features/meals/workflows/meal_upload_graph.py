from __future__ import annotations

import asyncio
from dataclasses import dataclass

from langgraph.graph import END, START, StateGraph

from care_pilot.agent.adapters.domain_agents import (
    MealLabelArbitrationAdapter,
    MealLabelArbitrationInput,
)
from care_pilot.agent.adapters.shadow_agents import MealAgentAdapter
from care_pilot.agent.core.contracts import AgentRequest
from care_pilot.agent.runtime.context_builder import build_agent_context
from care_pilot.core.contracts.agent_envelopes import AgentHandoff
from care_pilot.features.meals.domain import MealPerception, MealPortionEstimate, PerceivedMealItem
from care_pilot.features.meals.domain.models import (
    CandidateMealEvent,
    DietaryClaim,
    DietaryClaims,
    MealCandidateRecord,
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
)
from care_pilot.features.meals.domain.normalization import (
    build_meal_record,
    normalize_vision_result,
)
from care_pilot.features.meals.presenters.api import build_meal_analysis_output
from care_pilot.features.workflows.trace_emitter import WorkflowTraceContext, WorkflowTraceEmitter
from care_pilot.platform.cache import EventTimelineService
from care_pilot.platform.observability.workflows.domain.models import (
    WorkflowExecutionResult,
    WorkflowName,
)
from care_pilot.platform.persistence import AppStores

from .meal_upload_output import MealUploadOutput
from .meal_upload_state import MealUploadState


@dataclass(frozen=True)
class MealUploadDeps:
    stores: AppStores
    event_timeline: EventTimelineService


@dataclass(slots=True)
class MealUploadGraphState:
    data: MealUploadState
    output: MealUploadOutput | None = None


def _extract_dietary_claims(*, text: str | None) -> DietaryClaims:
    if not text:
        return DietaryClaims()
    lowered = text.lower()
    claims: list[DietaryClaim] = []
    for token in (
        "rice",
        "chicken",
        "fish",
        "noodles",
        "milo",
        "tea",
        "coffee",
    ):
        if token in lowered:
            claims.append(DietaryClaim(label=token, confidence=0.65))
    consumption_fraction = 1.0
    if "half" in lowered or "1/2" in lowered:
        consumption_fraction = 0.5
    if "quarter" in lowered or "1/4" in lowered:
        consumption_fraction = 0.25
    return DietaryClaims(
        claimed_items=claims,
        consumption_fraction=consumption_fraction,
        meal_time_label=(
            "breakfast" if "breakfast" in lowered else "lunch" if "lunch" in lowered else None
        ),
        vendor_or_source=None,
        preparation_override="no sugar" if "no sugar" in lowered else None,
        dietary_constraints=[item for item in ("no sugar", "less salt") if item in lowered],
        goal_context=None,
        certainty_level="high" if claims else "low",
        ambiguity_notes=[],
    )


def _claim_perception(labels: list[str], confidence: float) -> MealPerception:
    items = [
        PerceivedMealItem(
            label=label,
            candidate_aliases=[label],
            portion_estimate=MealPortionEstimate(amount=1.0, unit="serving", confidence=confidence),
            confidence=confidence,
        )
        for label in labels
        if label
    ]
    return MealPerception(items=items, confidence_score=confidence, image_quality="unknown")


async def _run_meal_agent_proposal(
    *,
    event_timeline: EventTimelineService,
    correlation_id: str,
    request_id: str,
    user_id: str,
    meal_text: str,
) -> None:
    adapter = MealAgentAdapter()
    request = AgentRequest(
        user_id=user_id,
        session_id="meal_upload_agent",
        correlation_id=correlation_id,
        goal="Analyze meal from text",
        inputs={"text_context": meal_text},
    )
    result = await adapter.run(
        request,
        build_agent_context(
            user_id=user_id,
            session_id="meal_upload_agent",
            request_id=request_id,
            correlation_id=correlation_id,
            policy={"allowed_sources": ["meal_text"]},
            selection={"reason": "meal_proposal"},
        ),
    )
    response = result.output
    if response is None:
        return
    event_timeline.append(
        event_type="agent_action_proposed",
        workflow_name=WorkflowName.MEAL_ANALYSIS.value,
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


def _schedule_meal_agent_proposal(
    *,
    event_timeline: EventTimelineService,
    correlation_id: str,
    request_id: str,
    user_id: str,
    meal_text: str | None,
) -> None:
    if not meal_text:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(
            _run_meal_agent_proposal(
                event_timeline=event_timeline,
                correlation_id=correlation_id,
                request_id=request_id,
                user_id=user_id,
                meal_text=meal_text,
            )
        )
        return
    loop.create_task(
        _run_meal_agent_proposal(
            event_timeline=event_timeline,
            correlation_id=correlation_id,
            request_id=request_id,
            user_id=user_id,
            meal_text=meal_text,
        )
    )


def build_meal_upload_graph(*, deps: MealUploadDeps) -> StateGraph:
    async def start_node(state: MealUploadGraphState) -> dict[str, object]:
        data = state.data
        emitter = WorkflowTraceEmitter(deps.event_timeline)
        trace_ctx = WorkflowTraceContext(
            workflow_name=WorkflowName.MEAL_ANALYSIS.value,
            correlation_id=data.correlation_id,
            request_id=data.request_id,
            user_id=data.user_id,
        )
        emitter.workflow_started(
            trace_ctx,
            payload={
                "capture_source": data.capture.source,
                "meal_filename": data.capture.filename,
                "mime_type": data.capture.mime_type,
            },
        )
        return {}

    async def perceive_meal_node(state: MealUploadGraphState) -> dict[str, object]:
        from care_pilot.agent.meal_analysis.vision_module import HawkerVisionModule

        data = state.data
        module = HawkerVisionModule(provider=data.provider)
        vision_result, _ = await module.analyze_and_record(
            data.image_input,
            user_id=data.user_id,
        )
        vision_result = normalize_vision_result(
            vision_result=vision_result, food_store=deps.stores.foods
        )

        data.vision_result = vision_result
        _ = build_meal_record(
            image_input=data.image_input,
            user_id=data.user_id,
            vision_result=vision_result,
        )
        return {"data": data}

    async def reconcile_claims_node(state: MealUploadGraphState) -> dict[str, object]:
        data = state.data
        if data.vision_result is None:
            raise ValueError("vision_result missing")

        claims = _extract_dietary_claims(text=data.meal_text)
        unresolved: list[str] = []
        perception = data.vision_result.perception or MealPerception()
        claim_labels = [item.label for item in claims.claimed_items]
        vision_labels = [item.label for item in perception.items]
        if claim_labels and vision_labels and set(claim_labels) != set(vision_labels):
            unresolved.append("claim_vs_vision_conflict")
            adapter = MealLabelArbitrationAdapter()
            arbitration_result = await adapter.run(
                MealLabelArbitrationInput(
                    vision_labels=vision_labels,
                    claim_labels=claim_labels,
                    user_text=data.meal_text,
                ),
                build_agent_context(
                    user_id=data.user_id,
                    session_id=None,
                    request_id=data.request_id,
                    correlation_id=data.correlation_id,
                    policy={"allowed_sources": ["vision_labels", "claim_labels", "user_text"]},
                    selection={"reason": "meal_label_arbitration"},
                ),
            )
            decision = arbitration_result.output
            if decision and decision.chosen_label:
                deps.event_timeline.append(
                    event_type="agent_action_proposed",
                    workflow_name=WorkflowName.MEAL_ANALYSIS.value,
                    correlation_id=data.correlation_id,
                    request_id=data.request_id,
                    user_id=data.user_id,
                    payload={
                        "agent_name": "meal_label_arbitration_agent",
                        "status": "success",
                        "confidence": decision.confidence,
                        "chosen_label": decision.chosen_label,
                    },
                )
                claim_labels = [decision.chosen_label]
                unresolved = []
        reconciled_perception = (
            _claim_perception(claim_labels, confidence=0.6) if claim_labels else perception
        )
        reconciled = normalize_vision_result(
            vision_result=data.vision_result.model_copy(
                update={"perception": reconciled_perception}
            ),
            food_store=deps.stores.foods,
        )
        data.claims = claims
        data.unresolved_conflicts = unresolved
        data.vision_result = reconciled
        return {"data": data}

    async def persist_node(state: MealUploadGraphState) -> dict[str, object]:
        data = state.data
        if data.vision_result is None or data.claims is None:
            raise ValueError("missing vision_result or claims")

        raw_observation = RawObservationBundle(
            user_id=data.user_id,
            source=data.image_input.source,
            vision_result=data.vision_result,
            dietary_claims=data.claims,
            context=data.context,
            image_quality=(
                getattr(data.vision_result.perception, "image_quality", None)
                if data.vision_result.perception
                else None
            ),
            confidence_score=(
                getattr(data.vision_result.perception, "confidence_score", 0.0)
                if data.vision_result.perception
                else 0.0
            ),
            unresolved_conflicts=list(data.unresolved_conflicts),
        )
        enriched_event = data.vision_result.enriched_event
        if enriched_event is None:
            raise ValueError("meal analysis produced no canonical event")
        candidate_event = CandidateMealEvent(
            meal_name=enriched_event.meal_name,
            normalized_items=list(enriched_event.normalized_items),
            total_nutrition=enriched_event.total_nutrition,
            risk_tags=list(enriched_event.risk_tags),
            unresolved_items=list(enriched_event.unresolved_items),
            source_records=list(enriched_event.source_records),
            needs_manual_review=enriched_event.needs_manual_review,
            summary=enriched_event.summary,
        )
        validated_event = ValidatedMealEvent(
            user_id=data.user_id,
            captured_at=raw_observation.captured_at,
            meal_name=enriched_event.meal_name,
            consumption_fraction=data.claims.consumption_fraction,
            canonical_items=list(enriched_event.normalized_items),
            alternatives=list(enriched_event.unresolved_items),
            confidence_summary={
                "vision_confidence": (
                    getattr(
                        data.vision_result.perception,
                        "confidence_score",
                        0.0,
                    )
                    if data.vision_result.perception
                    else 0.0
                ),
                "claim_count": len(data.claims.claimed_items),
                "unresolved": list(data.unresolved_conflicts),
            },
            provenance={
                "observation_id": raw_observation.observation_id,
                "source": raw_observation.source,
            },
            needs_manual_review=bool(
                enriched_event.needs_manual_review or data.unresolved_conflicts
            ),
        )
        deps.event_timeline.append(
            event_type="meal_analyzed",
            workflow_name=WorkflowName.MEAL_ANALYSIS.value,
            correlation_id=data.correlation_id,
            request_id=data.request_id,
            user_id=data.user_id,
            payload={
                "meal_name": validated_event.meal_name,
                "needs_manual_review": validated_event.needs_manual_review,
                "confidence_summary": validated_event.confidence_summary,
            },
        )
        _schedule_meal_agent_proposal(
            event_timeline=deps.event_timeline,
            correlation_id=data.correlation_id,
            request_id=data.request_id,
            user_id=data.user_id,
            meal_text=data.meal_text,
        )
        confirmation_required = bool(validated_event.needs_manual_review)
        total = enriched_event.total_nutrition
        uncertainty: dict[str, object] = {}
        if enriched_event.unresolved_items:
            uncertainty = {
                "calories_range": [
                    max(total.calories * 0.8, 0.0),
                    total.calories * 1.2,
                ]
            }
        nutrition_profile = NutritionRiskProfile(
            event_id=validated_event.event_id,
            user_id=data.user_id,
            captured_at=validated_event.captured_at,
            calories=total.calories,
            carbs_g=total.carbs_g,
            sugar_g=total.sugar_g,
            protein_g=total.protein_g,
            fat_g=total.fat_g,
            sodium_mg=total.sodium_mg,
            fiber_g=total.fiber_g,
            risk_tags=list(enriched_event.risk_tags),
            uncertainty=uncertainty,
        )

        deps.stores.meals.save_meal_observation(raw_observation)
        candidate_record = MealCandidateRecord(
            user_id=data.user_id,
            captured_at=raw_observation.captured_at,
            confirmation_status="pending",
            candidate_event=candidate_event,
            observation_id=raw_observation.observation_id,
            request_id=data.request_id,
            correlation_id=data.correlation_id,
            source=raw_observation.source,
            meal_text=data.meal_text,
            validated_event=validated_event,
            nutrition_profile=nutrition_profile,
        )
        if not confirmation_required:
            candidate_record = candidate_record.model_copy(
                update={
                    "confirmation_status": "confirmed",
                    "confirmed_at": raw_observation.captured_at,
                }
            )
            deps.stores.meals.save_validated_meal_event(validated_event)
            deps.stores.meals.save_nutrition_risk_profile(nutrition_profile)
        deps.stores.meals.save_meal_candidate(candidate_record)

        output_envelope = build_meal_analysis_output(
            request_id=data.request_id,
            correlation_id=data.correlation_id,
            user_id=data.user_id,
            profile_mode=data.profile_mode,
            source=data.capture.source,
            vision_result=data.vision_result,
        )

        handoffs = [
            AgentHandoff(
                from_agent="meal_perception_agent",
                to_agent="dietary_assessment_agent",
                request_id=data.request_id,
                correlation_id=data.correlation_id,
                confidence=data.vision_result.primary_state.confidence_score,
                obligations=["evaluate_meal_against_profile"],
                payload={"dish_name": data.vision_result.primary_state.dish_name},
            )
        ]
        if data.vision_result.needs_manual_review:
            handoffs.append(
                AgentHandoff(
                    from_agent="dietary_assessment_agent",
                    to_agent="notification_agent",
                    request_id=data.request_id,
                    correlation_id=data.correlation_id,
                    confidence=data.vision_result.primary_state.confidence_score,
                    obligations=["request_clarification_from_patient"],
                    payload={"reason": "manual_review_required"},
                )
            )

        emitter = WorkflowTraceEmitter(deps.event_timeline)
        trace_ctx = WorkflowTraceContext(
            workflow_name=WorkflowName.MEAL_ANALYSIS.value,
            correlation_id=data.correlation_id,
            request_id=data.request_id,
            user_id=data.user_id,
        )
        emitter.workflow_completed(
            trace_ctx,
            payload={
                "dish_name": data.vision_result.primary_state.dish_name,
                "manual_review": data.vision_result.needs_manual_review,
                "handoff_count": len(handoffs),
                "meal_record_id": validated_event.event_id,
                "confidence": data.vision_result.primary_state.confidence_score,
                "estimated_calories": data.vision_result.primary_state.nutrition.calories,
                "model_version": data.vision_result.model_version,
            },
        )

        workflow = WorkflowExecutionResult(
            workflow_name=WorkflowName.MEAL_ANALYSIS,
            request_id=data.request_id,
            correlation_id=data.correlation_id,
            user_id=data.user_id,
            output_envelope=output_envelope,
            handoffs=handoffs,
            timeline_events=deps.event_timeline.get_events(correlation_id=data.correlation_id),
        )
        output = MealUploadOutput(
            raw_observation=raw_observation,
            candidate_record=candidate_record,
            confirmation_required=confirmation_required,
            validated_event=None if confirmation_required else validated_event,
            nutrition_profile=None if confirmation_required else nutrition_profile,
            output_envelope=output_envelope,
            workflow=workflow,
        )
        return {"output": output}

    workflow = StateGraph(MealUploadGraphState)
    workflow.add_node("start", start_node)
    workflow.add_node("perceive", perceive_meal_node)
    workflow.add_node("reconcile", reconcile_claims_node)
    workflow.add_node("persist", persist_node)

    workflow.add_edge(START, "start")
    workflow.add_edge("start", "perceive")
    workflow.add_edge("perceive", "reconcile")
    workflow.add_edge("reconcile", "persist")
    workflow.add_edge("persist", END)
    return workflow


async def run_meal_upload_workflow(
    *, deps: MealUploadDeps, state: MealUploadState
) -> MealUploadOutput:
    graph = build_meal_upload_graph(deps=deps).compile()
    final_state = await graph.ainvoke(MealUploadGraphState(data=state))
    if isinstance(final_state, MealUploadGraphState):
        output = final_state.output
    elif isinstance(final_state, dict):
        output = final_state.get("output")
    else:
        output = None
    if output is None:
        raise ValueError("meal upload workflow did not produce output")
    return output
