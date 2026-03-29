"""In-process cache for ``UserProfile`` objects.

Provides fast look-up of recently loaded profiles without hitting the
persistence layer on every request.  Cache misses propagate to the repository.
"""

from threading import Lock

from care_pilot.features.profiles.domain.models import UserProfile
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class ProfileMemoryService:
    """Thread-unsafe in-process cache for ``UserProfile`` objects."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}
        self._lock = Lock()

    def put(self, profile: UserProfile) -> None:
        with self._lock:
            self._profiles[profile.id] = profile
        logger.info("profile_memory_put user_id=%s", profile.id)

    def get(self, user_id: str) -> UserProfile | None:
        with self._lock:
            return self._profiles.get(user_id)

    def clear(self, user_id: str | None = None) -> None:
        with self._lock:
            if user_id is None:
                self._profiles.clear()
            else:
                self._profiles.pop(user_id, None)


__all__ = ["ProfileMemoryService"]
