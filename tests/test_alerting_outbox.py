import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from dietary_guardian.domain.alerts.models import AlertMessage
from dietary_guardian.infrastructure.persistence import SQLiteRepository
from dietary_guardian.infrastructure.notifications.alert_outbox import AlertPublisher, OutboxWorker


def test_alert_publish_persists_to_outbox(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    publisher = AlertPublisher(repo)
    message = AlertMessage(
        alert_id=str(uuid4()),
        type="test_alert",
        severity="warning",
        payload={"message": "hello"},
        destinations=["in_app", "push"],
        correlation_id=str(uuid4()),
    )
    records = publisher.publish(message)
    assert len(records) == 2
    stored = repo.list_alert_records(message.alert_id)
    assert len(stored) == 2
    assert all(item.state == "pending" for item in stored)


def test_outbox_worker_delivers_and_marks_state(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    publisher = AlertPublisher(repo)
    message = AlertMessage(
        alert_id=str(uuid4()),
        type="test_alert",
        severity="warning",
        payload={"message": "hello"},
        destinations=["in_app"],
        correlation_id=str(uuid4()),
    )
    publisher.publish(message)

    worker = OutboxWorker(repo, max_attempts=2, concurrency=2)
    results = asyncio.run(worker.process_once())

    assert len(results) == 1
    assert results[0].success is True
    stored = repo.list_alert_records(message.alert_id)
    assert stored[0].state == "delivered"


def test_outbox_worker_unknown_sink_dead_letters(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    publisher = AlertPublisher(repo)
    message = AlertMessage(
        alert_id=str(uuid4()),
        type="test_alert",
        severity="warning",
        payload={"message": "hello"},
        destinations=["unknown_sink"],
        correlation_id=str(uuid4()),
    )
    publisher.publish(message)

    worker = OutboxWorker(repo, max_attempts=1, concurrency=1)
    results = asyncio.run(worker.process_once())

    assert len(results) == 1
    assert results[0].success is False
    stored = repo.list_alert_records(message.alert_id)
    assert stored[0].state == "dead_letter"


def test_duplicate_publish_does_not_reset_existing_outbox_state(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    publisher = AlertPublisher(repo)
    message = AlertMessage(
        alert_id=str(uuid4()),
        type="test_alert",
        severity="warning",
        payload={"message": "hello"},
        destinations=["in_app"],
        correlation_id=str(uuid4()),
    )
    publisher.publish(message)
    repo.mark_alert_delivered(message.alert_id, "in_app", attempt_count=1)

    records = publisher.publish(message)

    assert records == []
    stored = repo.list_alert_records(message.alert_id)
    assert len(stored) == 1
    assert stored[0].state == "delivered"
    assert stored[0].attempt_count == 1


def test_outbox_worker_persists_incremented_attempt_count_on_success(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "alerts.db"))
    publisher = AlertPublisher(repo)
    message = AlertMessage(
        alert_id=str(uuid4()),
        type="test_alert",
        severity="warning",
        payload={"message": "hello"},
        destinations=["in_app"],
        correlation_id=str(uuid4()),
    )
    publisher.publish(message)
    repo.reschedule_alert(
        message.alert_id,
        "in_app",
        next_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        attempt_count=1,
        error="first attempt failed",
    )

    worker = OutboxWorker(repo, max_attempts=3, concurrency=1)
    results = asyncio.run(worker.process_once())

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].attempt == 2
    stored = repo.list_alert_records(message.alert_id)
    assert stored[0].state == "delivered"
    assert stored[0].attempt_count == 2
