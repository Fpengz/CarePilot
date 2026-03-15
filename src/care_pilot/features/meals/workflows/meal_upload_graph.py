from __future__ import annotations

from dataclasses import dataclass

from pydantic_graph import (
    BaseNode,
    End,
    Graph,
    GraphRunContext,
    SimpleStatePersistence,
)

from care_pilot.agent import arbitrate_meal_label
from care_pilot.core.contracts.agent_envelopes import AgentHandoff
from care_pilot.features.meals.domain import (
    MealPerception,
    MealPortionEstimate,
    PerceivedMealItem,
)
from care_pilot.features.meals.domain.models import (
    DietaryClaim,
    DietaryClaims,
    NutritionRiskProfile,
    RawObservationBundle,
    ValidatedMealEvent,
)
from care_pilot.features.meals.presenter import build_meal_analysis_output
from care_pilot.features.meals.use_cases import (
    build_meal_record,
    normalize_vision_result,
)
from care_pilot.features.workflows.trace_emitter import (
    WorkflowTraceContext,
    WorkflowTraceEmitter,
)
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
            "breakfast"
            if "breakfast" in lowered
            else "lunch" if "lunch" in lowered else None
        ),
        vendor_or_source=None,
        preparation_override="no sugar" if "no sugar" in lowered else None,
        dietary_constraints=[
            item for item in ("no sugar", "less salt") if item in lowered
        ],
        goal_context=None,
        certainty_level="high" if claims else "low",
        ambiguity_notes=[],
    )


def _claim_perception(labels: list[str], confidence: float) -> MealPerception:
    items = [
        PerceivedMealItem(
            label=label,
            candidate_aliases=[label],
            portion_estimate=MealPortionEstimate(
                amount=1.0, unit="serving", confidence=confidence
            ),
            confidence=confidence,
        )
        for label in labels
        if label
    ]
    return MealPerception(
        items=items, confidence_score=confidence, image_quality="unknown"
    )


class Start(BaseNode[MealUploadState, MealUploadDeps, MealUploadOutput]):
    async def run(
        self,
        ctx: GraphRunContext[MealUploadState, MealUploadDeps],
    ) -> (
        BaseNode[MealUploadState, MealUploadDeps, MealUploadOutput]
        | End[MealUploadOutput]
    ):
        emitter = WorkflowTraceEmitter(ctx.deps.event_timeline)
        trace_ctx = WorkflowTraceContext(
            workflow_name=WorkflowName.MEAL_ANALYSIS.value,
            correlation_id=ctx.state.correlation_id,
            request_id=ctx.state.request_id,
            user_id=ctx.state.user_id,
        )
        emitter.workflow_started(
            trace_ctx,
            payload={
                "capture_source": ctx.state.capture.source,
                "meal_filename": ctx.state.capture.filename,
                "mime_type": ctx.state.capture.mime_type,
            },
        )
        return PerceiveMeal()


class PerceiveMeal(
    BaseNode[MealUploadState, MealUploadDeps, MealUploadOutput]
):
    async def run(
        self,
        ctx: GraphRunContext[MealUploadState, MealUploadDeps],
    ) -> (
        BaseNode[MealUploadState, MealUploadDeps, MealUploadOutput]
        | End[MealUploadOutput]
    ):
        from care_pilot.agent.meal_analysis.vision_module import (
            HawkerVisionModule,
        )

        module = HawkerVisionModule(provider=ctx.state.provider)
        vision_result, _ = await module.analyze_and_record(
            ctx.state.image_input,
            user_id=ctx.state.user_id,
        )
        vision_result = normalize_vision_result(
            vision_result=vision_result, food_store=ctx.deps.stores.foods
        )

        ctx.state.vision_result = vision_result
        _ = build_meal_record(
            image_input=ctx.state.image_input,
            user_id=ctx.state.user_id,
            vision_result=vision_result,
        )
        return ReconcileClaims()


class ReconcileClaims(
    BaseNode[MealUploadState, MealUploadDeps, MealUploadOutput]
):
    async def run(
        self,
        ctx: GraphRunContext[MealUploadState, MealUploadDeps],
    ) -> (
        BaseNode[MealUploadState, MealUploadDeps, MealUploadOutput]
        | End[MealUploadOutput]
    ):
        if ctx.state.vision_result is None:
            raise ValueError("vision_result missing")

        claims = _extract_dietary_claims(text=ctx.state.meal_text)
        unresolved: list[str] = []
        perception = ctx.state.vision_result.perception or MealPerception()
        claim_labels = [item.label for item in claims.claimed_items]
        vision_labels = [item.label for item in perception.items]
        if (
            claim_labels
            and vision_labels
            and set(claim_labels) != set(vision_labels)
        ):
            unresolved.append("claim_vs_vision_conflict")
            decision = await arbitrate_meal_label(
                vision_labels=vision_labels,
                claim_labels=claim_labels,
                user_text=ctx.state.meal_text,
            )
            if decision and decision.chosen_label:
                claim_labels = [decision.chosen_label]
                unresolved = []
        reconciled_perception = (
            _claim_perception(claim_labels, confidence=0.6)
            if claim_labels
            else perception
        )
        reconciled = normalize_vision_result(
            vision_result=ctx.state.vision_result.model_copy(
                update={"perception": reconciled_perception}
            ),
            food_store=ctx.deps.stores.foods,
        )
        ctx.state.claims = claims
        ctx.state.unresolved_conflicts = unresolved
        ctx.state.vision_result = reconciled
        return Persist()


class Persist(BaseNode[MealUploadState, MealUploadDeps, MealUploadOutput]):
    async def run(
        self,
        ctx: GraphRunContext[MealUploadState, MealUploadDeps],
    ) -> (
        BaseNode[MealUploadState, MealUploadDeps, MealUploadOutput]
        | End[MealUploadOutput]
    ):
        if ctx.state.vision_result is None or ctx.state.claims is None:
            raise ValueError("missing vision_result or claims")

        raw_observation = RawObservationBundle(
            user_id=ctx.state.user_id,
            source=ctx.state.image_input.source,
            vision_result=ctx.state.vision_result,
            dietary_claims=ctx.state.claims,
            context=ctx.state.context,
            image_quality=(
                getattr(
                    ctx.state.vision_result.perception, "image_quality", None
                )
                if ctx.state.vision_result.perception
                else None
            ),
            confidence_score=(
                getattr(
                    ctx.state.vision_result.perception, "confidence_score", 0.0
                )
                if ctx.state.vision_result.perception
                else 0.0
            ),
            unresolved_conflicts=list(ctx.state.unresolved_conflicts),
        )
        enriched_event = ctx.state.vision_result.enriched_event
        if enriched_event is None:
            raise ValueError("meal analysis produced no canonical event")
        validated_event = ValidatedMealEvent(
            user_id=ctx.state.user_id,
            captured_at=raw_observation.captured_at,
            meal_name=enriched_event.meal_name,
            consumption_fraction=ctx.state.claims.consumption_fraction,
            canonical_items=list(enriched_event.normalized_items),
            alternatives=list(enriched_event.unresolved_items),
            confidence_summary={
                "vision_confidence": (
                    getattr(
                        ctx.state.vision_result.perception,
                        "confidence_score",
                        0.0,
                    )
                    if ctx.state.vision_result.perception
                    else 0.0
                ),
                "claim_count": len(ctx.state.claims.claimed_items),
                "unresolved": list(ctx.state.unresolved_conflicts),
            },
            provenance={
                "observation_id": raw_observation.observation_id,
                "source": raw_observation.source,
            },
            needs_manual_review=bool(
                enriched_event.needs_manual_review
                or ctx.state.unresolved_conflicts
            ),
        )
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
            user_id=ctx.state.user_id,
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

        ctx.deps.stores.meals.save_meal_observation(raw_observation)
        ctx.deps.stores.meals.save_validated_meal_event(validated_event)
        ctx.deps.stores.meals.save_nutrition_risk_profile(nutrition_profile)

        output_envelope = build_meal_analysis_output(
            request_id=ctx.state.request_id,
            correlation_id=ctx.state.correlation_id,
            user_id=ctx.state.user_id,
            profile_mode=ctx.state.profile_mode,
            source=ctx.state.capture.source,
            vision_result=ctx.state.vision_result,
        )

        handoffs = [
            AgentHandoff(
                from_agent="meal_perception_agent",
                to_agent="dietary_assessment_agent",
                request_id=ctx.state.request_id,
                correlation_id=ctx.state.correlation_id,
                confidence=ctx.state.vision_result.primary_state.confidence_score,
                obligations=["evaluate_meal_against_profile"],
                payload={
                    "dish_name": ctx.state.vision_result.primary_state.dish_name
                },
            )
        ]
        if ctx.state.vision_result.needs_manual_review:
            handoffs.append(
                AgentHandoff(
                    from_agent="dietary_assessment_agent",
                    to_agent="notification_agent",
                    request_id=ctx.state.request_id,
                    correlation_id=ctx.state.correlation_id,
                    confidence=ctx.state.vision_result.primary_state.confidence_score,
                    obligations=["request_clarification_from_patient"],
                    payload={"reason": "manual_review_required"},
                )
            )

        emitter = WorkflowTraceEmitter(ctx.deps.event_timeline)
        trace_ctx = WorkflowTraceContext(
            workflow_name=WorkflowName.MEAL_ANALYSIS.value,
            correlation_id=ctx.state.correlation_id,
            request_id=ctx.state.request_id,
            user_id=ctx.state.user_id,
        )
        emitter.workflow_completed(
            trace_ctx,
            payload={
                "dish_name": ctx.state.vision_result.primary_state.dish_name,
                "manual_review": ctx.state.vision_result.needs_manual_review,
                "handoff_count": len(handoffs),
                "meal_record_id": validated_event.event_id,
                "confidence": ctx.state.vision_result.primary_state.confidence_score,
                "estimated_calories": ctx.state.vision_result.primary_state.nutrition.calories,
                "model_version": ctx.state.vision_result.model_version,
            },
        )

        workflow = WorkflowExecutionResult(
            workflow_name=WorkflowName.MEAL_ANALYSIS,
            request_id=ctx.state.request_id,
            correlation_id=ctx.state.correlation_id,
            user_id=ctx.state.user_id,
            output_envelope=output_envelope,
            handoffs=handoffs,
            timeline_events=ctx.deps.event_timeline.get_events(
                correlation_id=ctx.state.correlation_id
            ),
        )
        return End(
            MealUploadOutput(
                raw_observation=raw_observation,
                validated_event=validated_event,
                nutrition_profile=nutrition_profile,
                output_envelope=output_envelope,
                workflow=workflow,
            )
        )


meal_upload_graph: Graph[MealUploadState, MealUploadDeps, MealUploadOutput] = (
    Graph(
        nodes=[Start, PerceiveMeal, ReconcileClaims, Persist],
        name="meal_upload",
        state_type=MealUploadState,
        run_end_type=MealUploadOutput,
    )
)


async def run_meal_upload_workflow(
    *, deps: MealUploadDeps, state: MealUploadState
) -> MealUploadOutput:
    persistence = SimpleStatePersistence()
    result = await meal_upload_graph.run(
        Start(), state=state, deps=deps, persistence=persistence
    )
    return result.output
