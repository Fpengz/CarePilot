from dietary_guardian.config.settings import Settings
from dietary_guardian.infrastructure.cache.rate_limiter import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    build_rate_limiter,
)


def test_build_rate_limiter_uses_in_memory_backend_for_local_profiles() -> None:
    limiter = build_rate_limiter(
        Settings(llm={"provider": "test"}, app={"env": "dev"}, storage={"ephemeral_state_backend": "in_memory"})
    )
    assert isinstance(limiter, InMemoryRateLimiter)


def test_build_rate_limiter_uses_redis_backend_for_shared_profiles() -> None:
    limiter = build_rate_limiter(
        Settings(
            llm={"provider": "test"},
            app={"env": "dev"},
            storage={"ephemeral_state_backend": "redis", "redis_url": "redis://localhost:6379/0"},
        )
    )
    assert isinstance(limiter, RedisRateLimiter)
