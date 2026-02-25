from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class InferenceModality(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    MIXED = "mixed"


class ProviderMetadata(BaseModel):
    provider: str
    model: str
    endpoint: str


class InferenceRequest(BaseModel):
    request_id: str
    user_id: str | None = None
    modality: InferenceModality
    payload: dict[str, Any]
    safety_context: dict[str, Any] = Field(default_factory=dict)
    runtime_profile: dict[str, str] = Field(default_factory=dict)
    trace_context: dict[str, str] = Field(default_factory=dict)
    output_schema: type[BaseModel]
    system_prompt: str


class InferenceResponse(BaseModel):
    request_id: str
    structured_output: BaseModel
    confidence: float | None = None
    latency_ms: float
    provider_metadata: ProviderMetadata
    warnings: list[str] = Field(default_factory=list)
    raw_reference: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InferenceHealth(BaseModel):
    provider: str
    model: str
    endpoint: str
    supports_modalities: list[InferenceModality]
    healthy: bool = True
