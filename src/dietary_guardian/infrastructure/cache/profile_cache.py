"""In-process cache for ``UserProfile`` objects.

Provides fast look-up of recently loaded profiles without hitting the
persistence layer on every request.  Cache misses propagate to the repository.
"""

from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.infrastructure.observability import get_logger

logger = get_logger(__name__)


class ProfileMemoryService:
    """Thread-unsafe in-process cache for ``UserProfile`` objects."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    def put(self, profile: UserProfile) -> None:
        self._profiles[profile.id] = profile
        logger.info("profile_memory_put user_id=%s", profile.id)

    def get(self, user_id: str) -> UserProfile | None:
        return self._profiles.get(user_id)


__all__ = ["ProfileMemoryService"]
