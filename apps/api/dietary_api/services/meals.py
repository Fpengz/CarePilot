from typing import Any, cast

from fastapi import HTTPException, Request, UploadFile

from dietary_guardian.agents.hawker_vision import HawkerVisionModule
from dietary_guardian.models.meal import ImageInput
from dietary_guardian.services.media_ingestion import build_capture_envelope, should_suppress_duplicate_capture
from dietary_guardian.services.upload_service import SUPPORTED_IMAGE_TYPES, _maybe_downscale_image

from apps.api.dietary_api.auth import build_user_profile_from_session
from apps.api.dietary_api.deps import AppContext
from apps.api.dietary_api.schemas import MealAnalyzeResponse, MealRecordsResponse


async def analyze_meal(
    *,
    request: Request,
    context: AppContext,
    session: dict[str, object],
    file: UploadFile,
    provider: str,
) -> MealAnalyzeResponse:
    payload = await file.read()
    if len(payload) == 0:
        raise HTTPException(status_code=400, detail="empty upload")
    mime_type = file.content_type or ""
    if mime_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="unsupported image format")

    image_bytes, preprocess_meta = _maybe_downscale_image(
        payload,
        mime_type,
        enabled=context.settings.image_downscale_enabled,
        max_side_px=context.settings.image_max_side_px,
    )
    image_input = ImageInput(
        source="upload",
        filename=file.filename,
        mime_type=mime_type,
        content=image_bytes,
        metadata=preprocess_meta,
    )
    capture = build_capture_envelope(image_input, user_id=str(session["user_id"]))
    dedupe_state = cast(dict[str, Any], request.app.state.__dict__.setdefault("_capture_dedupe_state", {}))
    if should_suppress_duplicate_capture(dedupe_state, capture, window_seconds=30):
        raise HTTPException(status_code=409, detail="duplicate capture suppressed")

    user_profile = build_user_profile_from_session(session)
    module = HawkerVisionModule(provider=provider)
    vision_result, meal_record = await module.analyze_and_record(
        image_input,
        user_profile.id,
        request_id=capture.request_id,
        correlation_id=capture.correlation_id,
    )
    context.repository.save_meal_record(meal_record)
    workflow = context.coordinator.run_meal_analysis_workflow(
        capture=capture,
        vision_result=vision_result,
        user_profile=user_profile,
        meal_record_id=meal_record.id,
    )
    return MealAnalyzeResponse(
        vision_result=vision_result.model_dump(mode="json"),
        meal_record=meal_record.model_dump(mode="json"),
        output_envelope=workflow.output_envelope.model_dump(mode="json") if workflow.output_envelope else None,
        workflow=workflow.model_dump(mode="json"),
    )


def list_meal_records(*, context: AppContext, user_id: str, limit: int = 50) -> MealRecordsResponse:
    records = context.repository.list_meal_records(user_id)
    return MealRecordsResponse(records=[item.model_dump(mode="json") for item in records[:limit]])
