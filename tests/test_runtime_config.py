import pytest
from pydantic import ValidationError

from dietary_guardian.config.runtime import AppConfig, MedicalConfig, ModelSettings


def test_runtime_config_defaults() -> None:
    cfg = AppConfig()
    assert cfg.medical.sodium_limit_mg == 2000
    assert cfg.medical.sugar_alert_threshold == 5.5
    assert cfg.models.primary_model == "gemini-3-flash"
    assert cfg.models.fallback_model == "gemini-3.1-pro"
    assert cfg.models.retry_limit == 3
    assert cfg.models.clarification_threshold == 0.75


def test_runtime_config_validation() -> None:
    with pytest.raises(ValidationError):
        ModelSettings(clarification_threshold=1.5)

    with pytest.raises(ValidationError):
        MedicalConfig(sodium_limit_mg=0)
