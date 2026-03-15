"""Architecture tests for feature-first entry points.

These tests lock in the "start here" modules for core product features.
"""


def test_companion_feature_has_service_entrypoint() -> None:
    from care_pilot.features.companion import service as companion_service

    assert hasattr(companion_service, "run_companion_interaction")
    assert hasattr(companion_service, "build_companion_today_bundle")
    assert hasattr(companion_service, "CompanionStateInputs")


def test_meals_feature_has_service_entrypoint() -> None:
    from care_pilot.features.meals import service as meals_service

    assert hasattr(meals_service, "normalize_vision_result")
    assert hasattr(meals_service, "build_meal_record")
    assert hasattr(meals_service, "build_meal_analysis_output")
