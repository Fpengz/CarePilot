from types import SimpleNamespace

import pytest

from apps.workers import run as worker_run


class StopLoop(BaseException):
    pass


class FakeCoordinationStore:
    def __init__(self) -> None:
        self.released: list[tuple[str, str]] = []
        self.waits: list[tuple[str, float]] = []

    def acquire_lock(self, name: str, *, owner: str, ttl_seconds: int) -> bool:
        return True

    def release_lock(self, name: str, *, owner: str) -> None:
        self.released.append((name, owner))

    def wait_for_signal(self, channel: str, *, timeout_seconds: float) -> None:
        self.waits.append((channel, timeout_seconds))


class FakeCoordinationStoreNoWait:
    def __init__(self) -> None:
        self.released: list[tuple[str, str]] = []

    def acquire_lock(self, name: str, *, owner: str, ttl_seconds: int) -> bool:
        return True

    def release_lock(self, name: str, *, owner: str) -> None:
        self.released.append((name, owner))


@pytest.mark.anyio
async def test_worker_loop_recovers_from_scheduler_failure_and_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        worker_mode="external",
        ephemeral_state_backend="redis",
        redis_lock_ttl_seconds=30,
        alert_worker_max_attempts=3,
        alert_worker_concurrency=2,
        reminder_worker_poll_interval_seconds=1,
        outbox_worker_poll_interval_seconds=1,
        redis_worker_signal_channel="workers.ready",
    )
    coordination_store = FakeCoordinationStoreNoWait()
    ctx = SimpleNamespace(
        app_store=object(),
        coordination_store=coordination_store,
    )
    scheduler_calls = {"count": 0}
    sleep_calls = {"count": 0}

    def fake_get_settings() -> SimpleNamespace:
        return settings

    def fake_build_app_context() -> SimpleNamespace:
        return ctx

    def fake_close_app_context(closed_ctx: SimpleNamespace) -> None:
        assert closed_ctx is ctx

    async def fake_run_reminder_scheduler_once(*, repository: object) -> SimpleNamespace:
        assert repository is ctx.app_store
        scheduler_calls["count"] += 1
        if scheduler_calls["count"] == 1:
            raise RuntimeError("transient scheduler failure")
        return SimpleNamespace(queued_count=0, delivery_attempts=0)

    class FakeOutboxWorker:
        def __init__(
            self,
            repository: object,
            *,
            lease_owner: str,
            max_attempts: int,
            concurrency: int,
        ) -> None:
            assert repository is ctx.app_store
            assert lease_owner.startswith("worker-")
            assert max_attempts == settings.alert_worker_max_attempts
            assert concurrency == settings.alert_worker_concurrency

        async def process_once(self) -> list[object]:
            return []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls["count"] += 1
        if sleep_calls["count"] >= 2:
            raise StopLoop

    monkeypatch.setattr(worker_run, "get_settings", fake_get_settings)
    monkeypatch.setattr(worker_run, "build_app_context", fake_build_app_context)
    monkeypatch.setattr(worker_run, "close_app_context", fake_close_app_context)
    monkeypatch.setattr(worker_run, "run_reminder_scheduler_once", fake_run_reminder_scheduler_once)
    monkeypatch.setattr(worker_run, "OutboxWorker", FakeOutboxWorker)
    monkeypatch.setattr(worker_run.asyncio, "sleep", fake_sleep)

    with pytest.raises(StopLoop):
        await worker_run.run_worker_loop()

    assert scheduler_calls["count"] == 2
    assert sleep_calls["count"] == 2


@pytest.mark.anyio
async def test_worker_iteration_releases_scheduler_lock_when_scheduler_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        redis_lock_ttl_seconds=30,
        alert_worker_max_attempts=3,
        alert_worker_concurrency=2,
        reminder_worker_poll_interval_seconds=1,
        outbox_worker_poll_interval_seconds=1,
        redis_worker_signal_channel="workers.ready",
    )
    coordination_store = FakeCoordinationStore()
    ctx = SimpleNamespace(app_store=object(), coordination_store=coordination_store)

    async def fake_run_reminder_scheduler_once(*, repository: object) -> SimpleNamespace:
        assert repository is ctx.app_store
        raise RuntimeError("scheduler exploded")

    monkeypatch.setattr(worker_run, "run_reminder_scheduler_once", fake_run_reminder_scheduler_once)

    with pytest.raises(RuntimeError, match="scheduler exploded"):
        await worker_run._run_worker_iteration(ctx=ctx, settings=settings, owner="worker-test")

    assert coordination_store.released == [("reminder-scheduler", "worker-test")]


@pytest.mark.anyio
async def test_worker_iteration_waits_for_signal_when_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        redis_lock_ttl_seconds=30,
        alert_worker_max_attempts=3,
        alert_worker_concurrency=2,
        reminder_worker_poll_interval_seconds=15,
        outbox_worker_poll_interval_seconds=5,
        redis_worker_signal_channel="workers.ready",
    )
    class IdleCoordinationStore(FakeCoordinationStore):
        def acquire_lock(self, name: str, *, owner: str, ttl_seconds: int) -> bool:
            return False

    coordination_store = IdleCoordinationStore()
    ctx = SimpleNamespace(app_store=object(), coordination_store=coordination_store)

    class FakeOutboxWorker:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("outbox worker should not be constructed when no lock is acquired")

    async def fail_if_sleep_called(seconds: float) -> None:
        raise AssertionError(f"idle iteration should wait for signal, not sleep: {seconds}")

    monkeypatch.setattr(worker_run, "OutboxWorker", FakeOutboxWorker)
    monkeypatch.setattr(worker_run.asyncio, "sleep", fail_if_sleep_called)

    processed_work = await worker_run._run_worker_iteration(ctx=ctx, settings=settings, owner="worker-test")

    assert processed_work is False
    assert coordination_store.waits == [("workers.ready", 5.0)]
