from dietary_guardian.domain.alerts.models import AlertMessage
from dietary_guardian.infrastructure.notifications.message_composer import CHANNEL_CAPABILITIES, compose_alert_message


def test_compose_manual_alert_message_uses_generic_title_not_medication_label() -> None:
    alert = AlertMessage(
        alert_id="a1",
        type="manual_test_alert",
        severity="warning",
        payload={"message": "Manual end-to-end alert verification"},
        destinations=["telegram"],
        correlation_id="c1",
    )

    message = compose_alert_message(alert, channel="telegram")

    assert message.title == "Alert Notification"
    assert "Medication reminder" not in message.body
    assert "Manual end-to-end alert verification" in message.body


def test_channel_capabilities_exposed_for_transport_layer() -> None:
    telegram = CHANNEL_CAPABILITIES["telegram"]
    assert telegram.channel == "telegram"
    assert telegram.supports_text is True
    assert telegram.supports_images in {True, False}

