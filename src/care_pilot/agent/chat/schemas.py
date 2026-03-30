"""
Define typed schemas for the chat agent.

This module holds input/output contracts and streaming event payloads for the
SEA-LION companion chat pipeline.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ChatRouteLabel(StrEnum):
    DRUG = "drug"
    FOOD = "food"
    CODE = "code"
    GENERAL = "general"


class ChatInput(BaseModel):
    message: str
    session_id: str = "default"
    emotion_context: str | None = None
    user_id: str | None = None


class ChatOutput(BaseModel):
    response: str
    route: ChatRouteLabel = ChatRouteLabel.GENERAL
    context_used: bool = False


class ChatClassificationOutput(BaseModel):
    label: ChatRouteLabel = Field(default=ChatRouteLabel.GENERAL)


class ChatSearchQueryOutput(BaseModel):
    query: str


class ChatGeneratedCode(BaseModel):
    code: str


class ChatSummaryOutput(BaseModel):
    summary: str


class ChatMetricItem(BaseModel):
    metric_type: str
    value: float
    unit: str | None = None
    label: str | None = None


class ChatMetricsOutput(BaseModel):
    metrics: list[ChatMetricItem] = Field(default_factory=list)


class ChatStreamEvent(BaseModel):
    event: Literal[
        "token", "emotion", "transcribed", "error", "done", "meal_proposed", "meal_logged"
    ]
    data: dict
