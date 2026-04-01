"""
Normalize inbound messages from various channels into a canonical format.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class InboundAttachment(BaseModel):
    type: Literal["image", "audio", "document"]
    url: str | None = None
    content_type: str | None = None
    file_id: str | None = None  # Channel-specific ID (e.g. Telegram file_id)


class InboundMessage(BaseModel):
    user_id: str
    channel: Literal["telegram", "sms", "chat_ui"]
    text: str
    attachments: list[InboundAttachment] = Field(default_factory=list)
    raw_payload: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
