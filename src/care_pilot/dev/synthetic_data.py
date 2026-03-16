"""Synthetic dev-data generation helpers."""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from care_pilot.config import get_settings
from care_pilot.features.companion.core.health.models import (
    BiomarkerReading,
    HealthProfileRecord,
    MedicationAdherenceEvent,
)
from care_pilot.features.meals.domain.models import (
    NutritionRiskProfile,
    ValidatedMealEvent,
)
from care_pilot.features.profiles.domain.models import (
    MedicalCondition,
    Medication,
)
from care_pilot.features.reminders.domain.models import (
    MedicationRegimen,
    ReminderEvent,
)
from care_pilot.platform.persistence.sqlite_repository import SQLiteRepository

SyntheticProfile = Literal["stable", "improving", "volatile"]


@dataclass(frozen=True, slots=True)
class SyntheticSeedSummary:
    db_path: str
    user_id: str
    start_date: date
    end_date: date
    meals: int
    nutrition_profiles: int
    biomarkers: int
    adherence_events: int
    reminders: int
    regimens: int
    chat_bp_readings: int = 0


@dataclass(frozen=True, slots=True)
class SyntheticProfileConfig:
    target_calories: float
    protein_target: float
    fiber_target: float
    weight_start: float
    weight_end: float
    hba1c_start: float
    hba1c_end: float
    ldl_start: float
    ldl_end: float
    bp_start: float
    bp_end: float
    goals: tuple[str, ...]


def _dt(day: date, hour: int, minute: int = 0, *, timezone_name: str) -> datetime:
    local_dt = datetime.combine(day, time(hour=hour, minute=minute, tzinfo=ZoneInfo(timezone_name)))
    return local_dt.astimezone(UTC)


def _latest_seeded_day(db_path: str, user_id: str) -> date | None:
    queries = [
        (
            "SELECT MAX(captured_at) FROM meal_nutrition_risk_profiles WHERE user_id = ?",
            user_id,
        ),
        (
            "SELECT MAX(scheduled_at) FROM medication_adherence_events WHERE user_id = ?",
            user_id,
        ),
        (
            "SELECT MAX(scheduled_at) FROM reminder_events WHERE user_id = ?",
            user_id,
        ),
        (
            "SELECT MAX(measured_at) FROM biomarker_readings WHERE user_id = ?",
            user_id,
        ),
    ]
    latest: date | None = None
    with sqlite3.connect(db_path) as conn:
        for query, value in queries:
            row = conn.execute(query, (value,)).fetchone()
            raw = row[0] if row is not None else None
            if not raw:
                continue
            candidate = datetime.fromisoformat(raw).date()
            if latest is None or candidate > latest:
                latest = candidate
    return latest


def reset_synthetic_data(*, db_path: str, user_id: str) -> None:
    statements = [
        "DELETE FROM meal_records WHERE user_id = ?",
        "DELETE FROM meal_observations WHERE user_id = ?",
        "DELETE FROM meal_validated_events WHERE user_id = ?",
        "DELETE FROM meal_nutrition_risk_profiles WHERE user_id = ?",
        "DELETE FROM biomarker_readings WHERE user_id = ?",
        "DELETE FROM medication_adherence_events WHERE user_id = ?",
        "DELETE FROM reminder_events WHERE user_id = ?",
        "DELETE FROM medication_regimens WHERE user_id = ?",
        "DELETE FROM health_profile_onboarding_states WHERE user_id = ?",
        "DELETE FROM health_profiles WHERE user_id = ?",
    ]
    with sqlite3.connect(db_path) as conn:
        for statement in statements:
            conn.execute(statement, (user_id,))
        conn.commit()


def _init_chat_metrics_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS health_parsed_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT,
            label TEXT,
            recorded_at TEXT NOT NULL,
            UNIQUE (message_id, metric_type, user_id)
        )
        """
    )


def _reset_chat_metrics(*, chat_db_path: str, user_id: str) -> None:
    with sqlite3.connect(chat_db_path) as conn:
        _init_chat_metrics_schema(conn)
        conn.execute("DELETE FROM health_parsed_metrics WHERE user_id = ?", (user_id,))
        conn.commit()


def _next_message_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(message_id) FROM health_parsed_metrics").fetchone()
    max_id = row[0] if row and row[0] is not None else 0
    return int(max_id) + 1


def _seed_chat_bp_reading(
    *,
    chat_db_path: str,
    user_id: str,
    recorded_at: datetime,
    systolic: float,
    diastolic: float,
) -> None:
    with sqlite3.connect(chat_db_path) as conn:
        _init_chat_metrics_schema(conn)
        message_id = _next_message_id(conn)
        conn.executemany(
            """
            INSERT OR IGNORE INTO health_parsed_metrics
            (message_id, user_id, session_id, metric_type, value, unit, label, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    message_id,
                    user_id,
                    "synthetic",
                    "blood_pressure_systolic",
                    float(systolic),
                    "mmHg",
                    "Systolic BP",
                    recorded_at.isoformat(),
                ),
                (
                    message_id,
                    user_id,
                    "synthetic",
                    "blood_pressure_diastolic",
                    float(diastolic),
                    "mmHg",
                    "Diastolic BP",
                    recorded_at.isoformat(),
                ),
            ],
        )
        conn.commit()


def _resolve_window(
    *,
    db_path: str,
    user_id: str,
    days: int,
    start_date: date | None,
    append: bool,
) -> tuple[date, date]:
    if start_date is not None:
        start = start_date
    elif append:
        latest = _latest_seeded_day(db_path, user_id)
        start = (
            (latest + timedelta(days=1))
            if latest is not None
            else (datetime.now(UTC).date() - timedelta(days=days - 1))
        )
    else:
        start = datetime.now(UTC).date() - timedelta(days=days - 1)
    end = start + timedelta(days=days - 1)
    return start, end


def _profile_config(profile: SyntheticProfile) -> SyntheticProfileConfig:
    if profile == "improving":
        return SyntheticProfileConfig(
            target_calories=1850.0,
            protein_target=88.0,
            fiber_target=30.0,
            weight_start=84.0,
            weight_end=80.8,
            hba1c_start=7.8,
            hba1c_end=6.7,
            ldl_start=4.4,
            ldl_end=3.6,
            bp_start=146.0,
            bp_end=131.0,
            goals=("lower_sugar", "weight_loss", "heart_health"),
        )
    if profile == "volatile":
        return SyntheticProfileConfig(
            target_calories=2000.0,
            protein_target=75.0,
            fiber_target=24.0,
            weight_start=82.0,
            weight_end=82.8,
            hba1c_start=7.1,
            hba1c_end=7.4,
            ldl_start=3.8,
            ldl_end=4.1,
            bp_start=138.0,
            bp_end=142.0,
            goals=("better_consistency", "lower_sugar"),
        )
    return SyntheticProfileConfig(
        target_calories=1900.0,
        protein_target=82.0,
        fiber_target=28.0,
        weight_start=81.5,
        weight_end=81.0,
        hba1c_start=7.0,
        hba1c_end=6.8,
        ldl_start=3.9,
        ldl_end=3.7,
        bp_start=136.0,
        bp_end=132.0,
        goals=("lower_sugar", "maintenance"),
    )


def _interpolate(start: float, end: float, progress: float) -> float:
    return start + ((end - start) * progress)


def _meal_count_for_day(rng: random.Random, *, profile: SyntheticProfile) -> int:
    if profile == "volatile":
        return 4 if rng.random() > 0.45 else 3
    return 4 if rng.random() > 0.72 else 3


def _slot_blueprints(
    profile: SyntheticProfile,
) -> list[tuple[str, int, int, int]]:
    if profile == "volatile":
        return [
            ("breakfast", 8, 480, 18),
            ("lunch", 13, 760, 32),
            ("dinner", 19, 840, 36),
            ("snack", 16, 260, 12),
        ]
    if profile == "improving":
        return [
            ("breakfast", 8, 410, 10),
            ("lunch", 13, 660, 24),
            ("dinner", 19, 740, 28),
            ("snack", 16, 220, 8),
        ]
    return [
        ("breakfast", 8, 430, 11),
        ("lunch", 13, 690, 25),
        ("dinner", 19, 760, 29),
        ("snack", 16, 230, 9),
    ]


def _meal_name(slot: str, risk_tags: list[str]) -> str:
    if slot == "breakfast":
        return "Protein oats" if "high_hba1c" not in risk_tags else "Sweet breakfast toast"
    if slot == "lunch":
        return "Chicken grain bowl" if "high_ldl" not in risk_tags else "Fried hawker lunch"
    if slot == "dinner":
        return "Salmon rice plate" if "high_bp" not in risk_tags else "Late salty dinner"
    return "Greek yogurt snack" if "high_hba1c" not in risk_tags else "Sugary snack"


def _build_profile(*, user_id: str, config: SyntheticProfileConfig) -> HealthProfileRecord:
    return HealthProfileRecord(
        user_id=user_id,
        age=54,
        locale="en-SG",
        height_cm=168.0,
        weight_kg=config.weight_end,
        daily_sodium_limit_mg=1800.0,
        daily_sugar_limit_g=28.0,
        daily_protein_target_g=config.protein_target,
        daily_fiber_target_g=config.fiber_target,
        target_calories_per_day=config.target_calories,
        macro_focus=["protein_forward", "glycemic_balance"],
        conditions=[
            MedicalCondition(name="Type 2 Diabetes", severity="High"),
            MedicalCondition(name="High Cholesterol", severity="Medium"),
        ],
        medications=[
            Medication(name="Metformin", dosage="500mg"),
            Medication(name="Atorvastatin", dosage="20mg"),
        ],
        nutrition_goals=list(config.goals),
        preferred_cuisines=["teochew", "japanese"],
        disliked_ingredients=["lard"],
        preferred_notification_channel="in_app",
    )


def _seed_regimens(repo: SQLiteRepository, *, user_id: str) -> list[MedicationRegimen]:
    regimens = [
        MedicationRegimen(
            id=f"synthetic-{user_id}-metformin",
            user_id=user_id,
            medication_name="Metformin",
            dosage_text="500mg",
            timing_type="fixed_time",
            fixed_time="09:00",
            max_daily_doses=1,
            active=True,
        ),
        MedicationRegimen(
            id=f"synthetic-{user_id}-atorvastatin",
            user_id=user_id,
            medication_name="Atorvastatin",
            dosage_text="20mg",
            timing_type="fixed_time",
            fixed_time="21:00",
            max_daily_doses=1,
            active=True,
        ),
    ]
    for regimen in regimens:
        repo.save_medication_regimen(regimen)
    return regimens


def seed_synthetic_data(
    *,
    db_path: str,
    user_id: str,
    days: int,
    seed: int,
    profile: SyntheticProfile,
    reset: bool,
    append: bool,
    start_date: date | None = None,
    chat_db_path: str | None = None,
    timezone_name: str | None = None,
) -> SyntheticSeedSummary:
    if reset == append:
        raise ValueError("choose exactly one of --reset or --append")
    if days < 1:
        raise ValueError("days must be >= 1")

    repo = SQLiteRepository(db_path)
    if timezone_name is None:
        timezone_name = get_settings().app.timezone
    if reset:
        reset_synthetic_data(db_path=db_path, user_id=user_id)
        if chat_db_path:
            _reset_chat_metrics(chat_db_path=chat_db_path, user_id=user_id)

    start, end = _resolve_window(
        db_path=db_path,
        user_id=user_id,
        days=days,
        start_date=start_date,
        append=append,
    )
    rng = random.Random(seed)
    config = _profile_config(profile)
    repo.save_health_profile(_build_profile(user_id=user_id, config=config))
    regimens = _seed_regimens(repo, user_id=user_id)

    meal_count = 0
    nutrition_count = 0
    biomarker_count = 0
    adherence_count = 0
    reminder_count = 0
    chat_bp_count = 0
    total_days = max(days - 1, 1)

    slot_blueprints = _slot_blueprints(profile)
    for offset in range(days):
        current_day = start + timedelta(days=offset)
        progress = offset / total_days
        daily_meal_count = _meal_count_for_day(rng, profile=profile)
        day_variation = rng.uniform(-60.0, 60.0)

        for slot_index, (slot, hour, base_calories, base_carbs) in enumerate(
            slot_blueprints[:daily_meal_count]
        ):
            slot_time = _dt(
                current_day, hour, 0 if slot != "snack" else 15, timezone_name=timezone_name
            )
            trend_adjustment = 0.0
            if profile == "improving":
                trend_adjustment = (1.0 - progress) * 120.0
            elif profile == "volatile":
                trend_adjustment = rng.uniform(-140.0, 180.0)
            calories = max(
                140.0,
                base_calories + day_variation + trend_adjustment + rng.uniform(-50.0, 50.0),
            )
            carbs = max(12.0, base_carbs + (calories / 28.0) + rng.uniform(-8.0, 8.0))
            protein = max(10.0, calories / 24.0 + rng.uniform(-4.0, 6.0))
            fat = max(6.0, calories / 42.0 + rng.uniform(-3.0, 5.0))
            fiber = max(2.0, protein / 3.5 + rng.uniform(0.0, 2.0))
            sugar = max(4.0, carbs / 5.2 + rng.uniform(-2.0, 3.0))
            sodium = max(180.0, calories * 0.78 + rng.uniform(-120.0, 180.0))

            risk_tags: list[str] = []
            if sugar >= 18 or (
                profile == "improving" and progress < 0.45 and slot in {"breakfast", "snack"}
            ):
                risk_tags.append("high_hba1c")
            if fat >= 24 or (profile == "volatile" and calories >= 820):
                risk_tags.append("high_ldl")
            if sodium >= 760 or slot == "dinner" and profile == "volatile":
                risk_tags.append("high_bp")

            event_id = f"synthetic-{user_id}-meal-{current_day.isoformat()}-{slot}-{slot_index}"
            repo.save_validated_meal_event(
                ValidatedMealEvent(
                    event_id=event_id,
                    user_id=user_id,
                    captured_at=slot_time,
                    meal_name=_meal_name(slot, risk_tags),
                    provenance={
                        "source": "synthetic_seed",
                        "profile": profile,
                        "slot": slot,
                    },
                )
            )
            repo.save_nutrition_risk_profile(
                NutritionRiskProfile(
                    profile_id=f"{event_id}-risk",
                    event_id=event_id,
                    user_id=user_id,
                    captured_at=slot_time,
                    calories=round(calories, 2),
                    carbs_g=round(carbs, 2),
                    sugar_g=round(sugar, 2),
                    protein_g=round(protein, 2),
                    fat_g=round(fat, 2),
                    sodium_mg=round(sodium, 2),
                    fiber_g=round(fiber, 2),
                    risk_tags=risk_tags,
                    uncertainty={"source": "synthetic_seed"},
                )
            )
            meal_count += 1
            nutrition_count += 1

        morning_status: Literal["taken", "missed"] = (
            "taken"
            if rng.random()
            > (
                0.24
                if profile == "volatile"
                else 0.12
                if profile == "stable"
                else 0.18 * (1.0 - progress)
            )
            else "missed"
        )
        night_status: Literal["taken", "missed"] = (
            "taken" if rng.random() > (0.20 if profile != "volatile" else 0.34) else "missed"
        )
        adherence_specs = [
            (regimens[0], _dt(current_day, 9, timezone_name=timezone_name), morning_status),
            (regimens[1], _dt(current_day, 21, timezone_name=timezone_name), night_status),
        ]
        for regimen, scheduled_at, status in adherence_specs:
            reminder_id = f"synthetic-{user_id}-reminder-{current_day.isoformat()}-{regimen.id}"
            repo.save_reminder_event(
                ReminderEvent(
                    id=reminder_id,
                    user_id=user_id,
                    title=f"{regimen.medication_name} reminder",
                    body="Synthetic reminder for local dashboard testing.",
                    medication_name=regimen.medication_name,
                    scheduled_at=scheduled_at,
                    dosage_text=regimen.dosage_text,
                    status="sent" if status == "taken" else "missed",
                    sent_at=scheduled_at,
                    ack_at=(scheduled_at + timedelta(minutes=5) if status == "taken" else None),
                )
            )
            repo.save_medication_adherence_event(
                MedicationAdherenceEvent(
                    id=f"synthetic-{user_id}-adherence-{current_day.isoformat()}-{regimen.id}",
                    user_id=user_id,
                    regimen_id=regimen.id,
                    reminder_id=reminder_id,
                    status=status,
                    scheduled_at=scheduled_at,
                    taken_at=(
                        scheduled_at + timedelta(minutes=5 + rng.randint(0, 20))
                        if status == "taken"
                        else None
                    ),
                    source="manual",
                    metadata={"source": "synthetic_seed", "profile": profile},
                )
            )
            reminder_count += 1
            adherence_count += 1

        if offset % 7 == 0:
            weight = _interpolate(config.weight_start, config.weight_end, progress) + rng.uniform(
                -0.35, 0.35
            )
            systolic = _interpolate(config.bp_start, config.bp_end, progress) + rng.uniform(
                -3.0, 3.0
            )
            diastolic = max(78.0, systolic - rng.uniform(46.0, 54.0))
            bp_timestamp = _dt(current_day, 7, 35, timezone_name=timezone_name)
            readings = [
                BiomarkerReading(
                    name="weight_kg",
                    value=round(weight, 2),
                    unit="kg",
                    measured_at=_dt(current_day, 7, 30, timezone_name=timezone_name),
                ),
                BiomarkerReading(
                    name="systolic_bp",
                    value=round(systolic, 2),
                    unit="mmHg",
                    measured_at=bp_timestamp,
                ),
                BiomarkerReading(
                    name="diastolic_bp",
                    value=round(diastolic, 2),
                    unit="mmHg",
                    measured_at=bp_timestamp,
                ),
            ]
            repo.save_biomarker_readings(user_id, readings)
            biomarker_count += len(readings)
            if chat_db_path:
                _seed_chat_bp_reading(
                    chat_db_path=chat_db_path,
                    user_id=user_id,
                    recorded_at=bp_timestamp,
                    systolic=systolic,
                    diastolic=diastolic,
                )
                chat_bp_count += 1

        if offset % 28 == 0 or offset == days - 1:
            hba1c = _interpolate(config.hba1c_start, config.hba1c_end, progress) + rng.uniform(
                -0.08, 0.08
            )
            ldl = _interpolate(config.ldl_start, config.ldl_end, progress) + rng.uniform(
                -0.12, 0.12
            )
            readings = [
                BiomarkerReading(
                    name="hba1c",
                    value=round(hba1c, 2),
                    unit="%",
                    measured_at=_dt(current_day, 8, 30, timezone_name=timezone_name),
                ),
                BiomarkerReading(
                    name="ldl",
                    value=round(ldl, 2),
                    unit="mmol/L",
                    measured_at=_dt(current_day, 8, 30, timezone_name=timezone_name),
                ),
            ]
            repo.save_biomarker_readings(user_id, readings)
            biomarker_count += len(readings)

    return SyntheticSeedSummary(
        db_path=db_path,
        user_id=user_id,
        start_date=start,
        end_date=end,
        meals=meal_count,
        nutrition_profiles=nutrition_count,
        biomarkers=biomarker_count,
        adherence_events=adherence_count,
        reminders=reminder_count,
        regimens=len(regimens),
        chat_bp_readings=chat_bp_count,
    )
