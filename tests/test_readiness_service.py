from dietary_guardian.config.settings import Settings
from dietary_guardian.services.readiness_service import build_readiness_report


def test_readiness_report_is_ready_for_default_dev_profile() -> None:
    settings = Settings(llm={"provider": "test"}, app={"env": "dev"})

    report = build_readiness_report(settings=settings)

    assert report["status"] == "ready"
    assert isinstance(report["checks"], list)
    assert report["warnings"] == []
    assert report["errors"] == []


def test_readiness_report_is_degraded_for_optional_channel_warnings() -> None:
    settings = Settings(
        llm={"provider": "test"},
        app={"env": "dev"},
        channels={"email_dev_mode": False, "email_smtp_host": None},
    )

    report = build_readiness_report(settings=settings)

    assert report["status"] == "degraded"
    assert any(item["name"] == "email_configuration" and item["status"] == "warn" for item in report["checks"])


def test_readiness_report_is_not_ready_when_warning_strict_mode_is_enabled() -> None:
    settings = Settings(
        llm={"provider": "test"},
        app={"env": "dev"},
        observability={"readiness_fail_on_warnings": True},
        channels={"sms_dev_mode": False, "sms_webhook_url": None},
    )

    report = build_readiness_report(settings=settings)

    assert report["status"] == "not_ready"
    assert any(item["name"] == "sms_configuration" and item["status"] == "warn" for item in report["checks"])


def test_readiness_report_requires_shared_rate_limiting_for_prod() -> None:
    settings = Settings(
        llm={"provider": "test"},
        app={"env": "prod"},
        storage={"ephemeral_state_backend": "in_memory"},
        auth={"session_secret": "prod-secret", "cookie_secure": True, "seed_demo_users": False},
    )

    report = build_readiness_report(settings=settings)

    assert report["status"] == "not_ready"
    assert any(item["name"] == "shared_rate_limiting" and item["status"] == "fail" for item in report["checks"])
