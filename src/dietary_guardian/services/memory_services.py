from datetime import datetime, timezone
from uuid import uuid4

from dietary_guardian.logging_config import get_logger
from dietary_guardian.models.report import ClinicalProfileSnapshot
from dietary_guardian.models.user import UserProfile
from dietary_guardian.models.workflow import WorkflowTimelineEvent

logger = get_logger(__name__)


class ProfileMemoryService:
    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    def put(self, profile: UserProfile) -> None:
        self._profiles[profile.id] = profile
        logger.info("profile_memory_put user_id=%s", profile.id)

    def get(self, user_id: str) -> UserProfile | None:
        return self._profiles.get(user_id)


class ClinicalSnapshotMemoryService:
    def __init__(self) -> None:
        self._snapshots: dict[str, ClinicalProfileSnapshot] = {}

    def put(self, user_id: str, snapshot: ClinicalProfileSnapshot) -> None:
        self._snapshots[user_id] = snapshot
        logger.info("clinical_memory_put user_id=%s biomarkers=%s", user_id, sorted(snapshot.biomarkers.keys()))

    def get(self, user_id: str) -> ClinicalProfileSnapshot | None:
        return self._snapshots.get(user_id)


class EventTimelineService:
    def __init__(self) -> None:
        self._events: list[WorkflowTimelineEvent] = []

    def append(
        self,
        *,
        event_type: str,
        correlation_id: str,
        payload: dict[str, object],
        request_id: str | None = None,
        user_id: str | None = None,
        workflow_name: str | None = None,
    ) -> WorkflowTimelineEvent:
        event = WorkflowTimelineEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            workflow_name=workflow_name,
            request_id=request_id,
            correlation_id=correlation_id,
            user_id=user_id,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
        self._events.append(event)
        logger.info(
            "event_timeline_append event_type=%s workflow=%s correlation_id=%s request_id=%s",
            event.event_type,
            event.workflow_name,
            event.correlation_id,
            event.request_id,
        )
        return event

    def list(self, *, correlation_id: str | None = None, user_id: str | None = None) -> list[WorkflowTimelineEvent]:
        events = self._events
        if correlation_id is not None:
            events = [e for e in events if e.correlation_id == correlation_id]
        if user_id is not None:
            events = [e for e in events if e.user_id == user_id]
        return sorted(events, key=lambda e: e.created_at)


