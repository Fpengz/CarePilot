import main as main_module

from dietary_guardian.config.settings import Settings


def test_bootstrap_runtime_settings_exits_on_validation_error(monkeypatch) -> None:
    def _raise_validation() -> Settings:
        return Settings(llm={"provider": "gemini", "gemini_api_key": None, "google_api_key": None})

    monkeypatch.setattr(main_module, "get_settings", _raise_validation)

    try:
        main_module.bootstrap_runtime_settings()
        raise AssertionError("Expected SystemExit")
    except SystemExit as exc:
        assert exc.code == 2


def test_runtime_summary_uses_validated_settings() -> None:
    settings = Settings(llm={"provider": "test"})
    summary = main_module._runtime_summary(settings)
    assert "Provider: test" in summary
    assert "Destination:" in summary
