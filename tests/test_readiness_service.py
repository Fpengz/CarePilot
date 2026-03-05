from dietary_guardian.config.settings import Settings
from dietary_guardian.services.readiness_service import build_readiness_report


def test_readiness_report_is_ready_for_default_dev_profile() -> None:
    settings = Settings(llm_provider="test", app_env="dev")

    report = build_readiness_report(settings=settings)

    assert report["status"] == "ready"
    assert isinstance(report["checks"], list)
    assert report["warnings"] == []
    assert report["errors"] == []


def test_readiness_report_is_degraded_for_optional_channel_warnings() -> None:
    settings = Settings(
        llm_provider="test",
        app_env="dev",
        email_dev_mode=False,
        email_smtp_host=None,
    )

    report = build_readiness_report(settings=settings)

    assert report["status"] == "degraded"
    assert any(item["name"] == "email_configuration" and item["status"] == "warn" for item in report["checks"])


def test_readiness_report_is_not_ready_when_warning_strict_mode_is_enabled() -> None:
    settings = Settings(
        llm_provider="test",
        app_env="dev",
        readiness_fail_on_warnings=True,
        sms_dev_mode=False,
        sms_webhook_url=None,
    )

    report = build_readiness_report(settings=settings)

    assert report["status"] == "not_ready"
    assert any(item["name"] == "sms_configuration" and item["status"] == "warn" for item in report["checks"])
