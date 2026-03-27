"""In-process cache for ``ClinicalProfileSnapshot`` objects.

Avoids redundant report-parsing work within a single request or worker tick.
Snapshots are keyed by user ID and replaced on every new report upload.
"""

from threading import Lock

from care_pilot.features.companion.core.health.models import ClinicalProfileSnapshot
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class ClinicalSnapshotMemoryService:
    """Thread-unsafe in-process cache for ``ClinicalProfileSnapshot`` objects."""

    def __init__(self) -> None:
        self._snapshots: dict[str, ClinicalProfileSnapshot] = {}
        self._lock = Lock()

    def put(self, user_id: str, snapshot: ClinicalProfileSnapshot) -> None:
        with self._lock:
            self._snapshots[user_id] = snapshot
        logger.info(
            "clinical_memory_put user_id=%s biomarkers=%s",
            user_id,
            sorted(snapshot.biomarkers.keys()),
        )

    def get(self, user_id: str) -> ClinicalProfileSnapshot | None:
        with self._lock:
            return self._snapshots.get(user_id)

    def clear(self, user_id: str | None = None) -> None:
        with self._lock:
            if user_id is None:
                self._snapshots.clear()
            else:
                self._snapshots.pop(user_id, None)


__all__ = ["ClinicalSnapshotMemoryService"]
