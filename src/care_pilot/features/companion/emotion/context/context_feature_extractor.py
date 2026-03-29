"""
Extract context features for emotion fusion.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, Protocol

from care_pilot.agent.emotion.schemas import EmotionContextFeatures, EmotionLabel
from care_pilot.features.companion.emotion.ports import ContextFeaturePort


class TimelineEvent(Protocol):
    created_at: datetime
    payload: dict[str, Any]
    event_type: str


class TimelineServiceProtocol(Protocol):
    def get_events(self, *, user_id: str | None) -> Iterable[TimelineEvent]: ...


class TimelineContextFeatureExtractor(ContextFeaturePort):
    def __init__(self, event_timeline: TimelineServiceProtocol, history_window: int = 5) -> None:
        """
        :param event_timeline: An EventTimelineService instance.
        :param history_window: Number of recent events to consider.
        """
        self._timeline = event_timeline
        self._history_window = history_window

    def extract(self, user_id: str | None) -> EmotionContextFeatures:
        if not user_id:
            return EmotionContextFeatures(
                recent_labels=[], trend="stable", recent_product_states=[]
            )

        # We duck-type the timeline service to avoid circular imports.
        # Assuming event_timeline.get_events(user_id) -> Iterable[TimelineEvent]
        all_events = self._timeline.get_events(user_id=user_id)

        history = [e for e in all_events if getattr(e, "event_type", "") == "emotion_observed"]
        history = sorted(history, key=lambda e: e.created_at)
        recent = history[-self._history_window :]

        recent_labels: list[EmotionLabel] = []
        for event in recent:
            payload = getattr(event, "payload", {})
            raw = str(payload.get("emotion", "")).lower()
            try:
                recent_labels.append(EmotionLabel(raw))
            except ValueError:
                continue

        trend = "stable"
        negative = {
            EmotionLabel.SAD,
            EmotionLabel.ANGRY,
            EmotionLabel.FRUSTRATED,
            EmotionLabel.ANXIOUS,
            EmotionLabel.FEARFUL,
            EmotionLabel.CONFUSED,
        }
        if len(recent_labels) >= 2:
            prev, last = recent_labels[-2], recent_labels[-1]
            if last in negative and prev not in negative:
                trend = "worsening"
            elif last not in negative and prev in negative:
                trend = "improving"

        return EmotionContextFeatures(
            recent_labels=recent_labels,
            trend=trend,
            recent_product_states=[],  # Could be populated similarly if needed
        )
