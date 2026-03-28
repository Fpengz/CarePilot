from __future__ import annotations

import os
from datetime import date, UTC, datetime
from pathlib import Path

import pytest
from care_pilot.features.companion.core.health.models import (
    HealthProfileRecord,
)
from care_pilot.features.profiles.domain.models import (
    MealScheduleWindow,
    NutritionGoal,
)
from care_pilot.platform.persistence.sqlite_clinical_repository import SQLiteClinicalRepository

@pytest.fixture
def repo(tmp_path: Path) -> SQLiteClinicalRepository:
    db_path = str(tmp_path / "test_clinical.db")
    from care_pilot.platform.persistence.sqlite_repository import SQLiteRepository
    full_repo = SQLiteRepository(db_path)
    return full_repo.clinical

def test_save_and_get_normalized_profile(repo: SQLiteClinicalRepository):
    user_id = "user_test_123"
    
    profile = HealthProfileRecord(
        user_id=user_id,
        age=30,
        locale="en-SG",
        nutrition_goals=[
            NutritionGoal(
                goal_type="sodium",
                target_value=1500.0,
                unit="mg",
                start_date=date(2026, 3, 1)
            ),
            NutritionGoal(
                goal_type="sugar",
                target_value=25.0,
                unit="g",
                start_date=date(2026, 3, 1)
            )
        ],
        meal_schedule=[
            MealScheduleWindow(
                slot="breakfast",
                day_of_week=1,
                start_time="08:00",
                end_time="09:00",
                notes="Light meal"
            ),
            MealScheduleWindow(
                slot="lunch",
                day_of_week=1,
                start_time="12:30",
                end_time="13:30"
            )
        ],
        updated_at=datetime.now(UTC).isoformat()
    )
    
    # Save
    repo.save_health_profile(profile)
    
    # Retrieve
    retrieved = repo.get_health_profile(user_id)
    
    assert retrieved is not None
    assert retrieved.user_id == user_id
    assert len(retrieved.nutrition_goals) == 2
    assert retrieved.nutrition_goals[0].goal_type == "sodium"
    assert retrieved.nutrition_goals[0].target_value == 1500.0
    
    assert len(retrieved.meal_schedule) == 2
    assert retrieved.meal_schedule[0].slot == "breakfast"
    assert retrieved.meal_schedule[0].start_time == "08:00"
    assert retrieved.meal_schedule[0].notes == "Light meal"

def test_sync_overwrites_old_records(repo: SQLiteClinicalRepository):
    user_id = "user_test_456"
    
    # Initial save
    profile1 = HealthProfileRecord(
        user_id=user_id,
        age=40,
        nutrition_goals=[
            NutritionGoal(goal_type="calories", target_value=2000.0, unit="kcal", start_date=date(2026, 1, 1))
        ],
        updated_at=datetime.now(UTC).isoformat()
    )
    repo.save_health_profile(profile1)
    
    # Update save (different goals)
    profile2 = HealthProfileRecord(
        user_id=user_id,
        age=40,
        nutrition_goals=[
            NutritionGoal(goal_type="protein", target_value=100.0, unit="g", start_date=date(2026, 2, 1))
        ],
        updated_at=datetime.now(UTC).isoformat()
    )
    repo.save_health_profile(profile2)
    
    # Verify only new goal exists
    retrieved = repo.get_health_profile(user_id)
    assert retrieved is not None
    assert len(retrieved.nutrition_goals) == 1
    assert retrieved.nutrition_goals[0].goal_type == "protein"
