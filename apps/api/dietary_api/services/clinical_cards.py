from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from apps.api.dietary_api.deps import ClinicalCardDeps
from apps.api.dietary_api.errors import build_api_error
from apps.api.dietary_api.schemas import (
    ClinicalCardEnvelopeResponse,
    ClinicalCardGenerateRequest,
    ClinicalCardListResponse,
    ClinicalCardResponse,
)
from dietary_guardian.models.clinical_card import ClinicalCardRecord
from dietary_guardian.models.metrics_trend import MetricTrend
from dietary_guardian.services.metrics_trend_service import (
    adherence_rate_points,
    biomarker_points,
    build_metric_trend,
    meal_calorie_points,
)


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    return date.fromisoformat(raw)


def _resolve_date_window(payload: ClinicalCardGenerateRequest) -> tuple[date, date]:
    end_date = _parse_date(payload.end_date) or date.today()
    start_date = _parse_date(payload.start_date) or (end_date - timedelta(days=6))
    if start_date > end_date:
        raise build_api_error(status_code=400, code="clinical_cards.invalid_window", message="start_date must be <= end_date")
    return (start_date, end_date)


def _trend_json(trend: MetricTrend) -> dict[str, object]:
    return {
        "metric": trend.metric,
        "delta": trend.delta,
        "percent_change": trend.percent_change,
        "slope_per_point": trend.slope_per_point,
        "direction": trend.direction,
        "point_count": len(trend.points),
    }


def _to_response(card: ClinicalCardRecord) -> ClinicalCardResponse:
    payload = card.model_dump(mode="json")
    return ClinicalCardResponse.model_validate(payload)


def generate_clinical_card_for_session(
    *,
    deps: ClinicalCardDeps,
    user_id: str,
    payload: ClinicalCardGenerateRequest,
) -> ClinicalCardEnvelopeResponse:
    start_date, end_date = _resolve_date_window(payload)
    meal_records = deps.stores.meals.list_meal_records(user_id)
    biomarker_readings = deps.stores.biomarkers.list_biomarker_readings(user_id)
    symptom_items = deps.stores.symptoms.list_symptom_checkins(user_id=user_id, limit=500)
    adherence_items = deps.stores.medications.list_medication_adherence_events(user_id=user_id)

    in_window_meals = [item for item in meal_records if start_date <= item.captured_at.date() <= end_date]
    in_window_symptoms = [item for item in symptom_items if start_date <= item.recorded_at.date() <= end_date]
    in_window_adherence = [item for item in adherence_items if start_date <= item.scheduled_at.date() <= end_date]
    in_window_biomarkers = [
        item
        for item in biomarker_readings
        if item.measured_at is not None and start_date <= item.measured_at.date() <= end_date
    ]

    calories_now = sum(float(item.meal_state.nutrition.calories) for item in in_window_meals)
    previous_start = start_date - timedelta(days=(end_date - start_date).days + 1)
    previous_end = start_date - timedelta(days=1)
    prev_meals = [item for item in meal_records if previous_start <= item.captured_at.date() <= previous_end]
    calories_prev = sum(float(item.meal_state.nutrition.calories) for item in prev_meals)
    deltas = {
        "meal_count_delta": float(len(in_window_meals) - len(prev_meals)),
        "calories_delta": round(calories_now - calories_prev, 4),
    }

    ldl_trend = build_metric_trend("biomarker:ldl", biomarker_points(biomarker_readings, biomarker_name="ldl"))
    hba1c_trend = build_metric_trend("biomarker:hba1c", biomarker_points(biomarker_readings, biomarker_name="hba1c"))
    calorie_trend = build_metric_trend("meal:calories", meal_calorie_points(meal_records))
    adherence_trend = build_metric_trend("adherence:rate", adherence_rate_points(adherence_items))

    sections = {
        "subjective": (
            f"User reported {len(in_window_symptoms)} symptom check-ins in this window. "
            f"Red-flag symptom entries: {sum(1 for item in in_window_symptoms if item.safety.decision == 'escalate')}."
        ),
        "objective": (
            f"Meals logged: {len(in_window_meals)}. Total estimated calories: {round(calories_now, 2)}. "
            f"Biomarker readings in window: {len(in_window_biomarkers)}. "
            f"Adherence events in window: {len(in_window_adherence)}."
        ),
        "assessment": (
            f"LDL trend: {ldl_trend.direction} ({ldl_trend.delta}). "
            f"HbA1c trend: {hba1c_trend.direction} ({hba1c_trend.delta}). "
            f"Adherence trend: {adherence_trend.direction} ({adherence_trend.delta})."
        ),
        "plan": (
            "Continue meal and symptom logging daily; review high-risk entries promptly; "
            "prioritize medication adherence follow-through for missed doses."
        ),
    }
    trends = {
        "biomarker:ldl": _trend_json(ldl_trend),
        "biomarker:hba1c": _trend_json(hba1c_trend),
        "meal:calories": _trend_json(calorie_trend),
        "adherence:rate": _trend_json(adherence_trend),
    }
    card = ClinicalCardRecord(
        id=str(uuid4()),
        user_id=user_id,
        created_at=datetime.now(timezone.utc),
        start_date=start_date,
        end_date=end_date,
        format=payload.format,
        sections=sections,
        deltas=deltas,
        trends=trends,
        provenance={
            "meal_record_count": len(meal_records),
            "symptom_checkin_count": len(symptom_items),
            "biomarker_reading_count": len(biomarker_readings),
            "adherence_event_count": len(adherence_items),
        },
    )
    saved = deps.stores.clinical_cards.save_clinical_card(card)
    return ClinicalCardEnvelopeResponse(card=_to_response(saved))


def list_clinical_cards_for_session(
    *,
    deps: ClinicalCardDeps,
    user_id: str,
    limit: int,
) -> ClinicalCardListResponse:
    items = deps.stores.clinical_cards.list_clinical_cards(user_id=user_id, limit=limit)
    return ClinicalCardListResponse(items=[_to_response(item) for item in items])


def get_clinical_card_for_session(
    *,
    deps: ClinicalCardDeps,
    user_id: str,
    card_id: str,
) -> ClinicalCardEnvelopeResponse:
    item = deps.stores.clinical_cards.get_clinical_card(user_id=user_id, card_id=card_id)
    if item is None:
        raise build_api_error(status_code=404, code="clinical_cards.not_found", message="clinical card not found")
    return ClinicalCardEnvelopeResponse(card=_to_response(item))
