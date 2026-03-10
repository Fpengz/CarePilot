"""In-process cache for ``ClinicalProfileSnapshot`` objects.

Avoids redundant report-parsing work within a single request or worker tick.
Snapshots are keyed by user ID and replaced on every new report upload.
"""

from dietary_guardian.domain.health.models import ClinicalProfileSnapshot
from dietary_guardian.observability import get_logger

logger = get_logger(__name__)


class ClinicalSnapshotMemoryService:
    """Thread-unsafe in-process cache for ``ClinicalProfileSnapshot`` objects."""

    def __init__(self) -> None:
        self._snapshots: dict[str, ClinicalProfileSnapshot] = {}

    def put(self, user_id: str, snapshot: ClinicalProfileSnapshot) -> None:
        self._snapshots[user_id] = snapshot
        logger.info("clinical_memory_put user_id=%s biomarkers=%s", user_id, sorted(snapshot.biomarkers.keys()))

    def get(self, user_id: str) -> ClinicalProfileSnapshot | None:
        return self._snapshots.get(user_id)


__all__ = ["ClinicalSnapshotMemoryService"]
