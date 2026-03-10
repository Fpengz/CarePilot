from dietary_guardian.infrastructure.persistence import SQLiteRepository
from dietary_guardian.application.notifications.alert_dispatch import trigger_alert


def test_trigger_alert_enqueues_and_processes(tmp_path) -> None:
    repo = SQLiteRepository(str(tmp_path / "trigger.db"))
    alert, deliveries = trigger_alert(
        alert_type="manual_test",
        severity="warning",
        payload={"message": "test"},
        destinations=["in_app"],
        repository=repo,
    )

    assert alert.alert_id
    assert deliveries
    assert deliveries[0].success is True

    records = repo.list_alert_records(alert.alert_id)
    assert len(records) == 1
    assert records[0].state == "delivered"
