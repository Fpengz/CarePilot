from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .enums import MetricType, ReminderChannel, ReminderState, ReminderType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


@dataclass(slots=True, frozen=True)
class ThresholdRule:
    metric_type: MetricType
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: str = ""
    alert_title: str = ""

    def evaluate(self, value: float) -> Optional[str]:
        if self.max_value is not None and value > self.max_value:
            return f"高于阈值 {self.max_value}{self.unit}"
        if self.min_value is not None and value < self.min_value:
            return f"低于阈值 {self.min_value}{self.unit}"
        return None


DEFAULT_THRESHOLD_RULES: dict[MetricType, ThresholdRule] = {
    MetricType.HEART_RATE: ThresholdRule(
        metric_type=MetricType.HEART_RATE,
        min_value=50,
        max_value=110,
        unit="bpm",
        alert_title="心率阈值提醒",
    ),
    MetricType.BLOOD_GLUCOSE: ThresholdRule(
        metric_type=MetricType.BLOOD_GLUCOSE,
        min_value=3.9,
        max_value=11.1,
        unit="mmol/L",
        alert_title="血糖阈值提醒",
    ),
}


@dataclass(slots=True, frozen=True)
class ReminderEvent:
    event_id: str
    user_id: str
    reminder_id: str
    reminder_type: ReminderType
    scheduled_at: str
    channel: str
    payload: str
    idempotency_key: str
    correlation_id: str
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        reminder_id: str,
        reminder_type: ReminderType,
        payload: dict[str, Any] | str,
        scheduled_at: Optional[str] = None,
        channel: str | ReminderChannel = ReminderChannel.TELEGRAM,
        correlation_id: Optional[str] = None,
    ) -> "ReminderEvent":
        now_str = utc_now_iso()
        payload_text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

        return cls(
            event_id=f"EVT-{uuid.uuid4().hex}",
            user_id=user_id,
            reminder_id=reminder_id,
            reminder_type=reminder_type,
            scheduled_at=scheduled_at or now_str,
            channel=channel.value if isinstance(channel, ReminderChannel) else channel,
            payload=payload_text,
            idempotency_key=f"IDEM-{uuid.uuid4().hex}",
            correlation_id=correlation_id or f"CORR-{uuid.uuid4().hex}",
            created_at=now_str,
        )


@dataclass(slots=True)
class Reminder:
    reminder_id: str
    user_id: str
    reminder_type: ReminderType
    state: ReminderState
    message: str
    scheduled_at: str
    created_at: str
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        reminder_type: ReminderType,
        message: str,
        scheduled_at: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        reminder_id: Optional[str] = None,
    ) -> "Reminder":
        now_str = utc_now_iso()
        return cls(
            reminder_id=reminder_id or f"REM-{uuid.uuid4().hex[:8].upper()}",
            user_id=user_id,
            reminder_type=reminder_type,
            state=ReminderState.SCHEDULED,
            message=message,
            scheduled_at=scheduled_at or now_str,
            created_at=now_str,
            payload=payload or {},
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "id": self.reminder_id,
            "user_id": self.user_id,
            "reminder_type": self.reminder_type.value,
            "message": self.message,
            "state": self.state.value,
            "scheduled_at": self.scheduled_at,
            "created_at": self.created_at,
            **self.payload,
        }

    def mark(self, state: ReminderState) -> None:
        self.state = state


@dataclass(slots=True, frozen=True)
class MetricReading:
    user_id: str
    metric_type: MetricType
    metric_value: float
    unit: str
    measured_at: str
    source: str = "manual"
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        metric_type: MetricType,
        metric_value: float,
        unit: str,
        measured_at: Optional[str] = None,
        source: str = "manual",
        raw_payload: Optional[dict[str, Any]] = None,
    ) -> "MetricReading":
        return cls(
            user_id=user_id,
            metric_type=metric_type,
            metric_value=metric_value,
            unit=unit,
            measured_at=measured_at or utc_now_iso(),
            source=source,
            raw_payload=raw_payload or {},
        )


@dataclass(slots=True, frozen=True)
class FoodRecord:
    user_id: str
    meal_type: str
    foods: list[str]
    recorded_at: str
    note: str = ""

    @classmethod
    def create(
        cls,
        *,
        user_id: str,
        meal_type: str,
        foods: list[str],
        recorded_at: Optional[str] = None,
        note: Optional[str] = None,
    ) -> "FoodRecord":
        return cls(
            user_id=user_id,
            meal_type=meal_type,
            foods=foods,
            recorded_at=recorded_at or utc_now_iso(),
            note=note or "",
        )


@dataclass(slots=True, frozen=True)
class ReminderDispatchResult:
    success: bool
    provider_msg_id: Optional[str] = None
    error: Optional[str] = None