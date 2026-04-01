"""
Define data models for the persistence layer.

This module serves as the entry point for all persistence models,
ensuring that all ORM-mapped classes are discoverable and correctly
registered with SQLModel.metadata.
"""

from sqlmodel import SQLModel

from .auth import AccountRecord
from .auth_models import AuthAuditEvent, AuthLoginFailure, AuthSession, AuthUser
from .base import BaseRecord, TimestampMixin
from .clinical import BiomarkerReadingRecord, SymptomCheckInRecord
from .events import AlertOutboxRecord, ReminderEventRecord
from .meal_components import MealComponentRecord
from .meals import MealRecordRecord
from .medications import MedicationAdherenceRecord, MedicationRegimenRecord
from .profiles import UserProfileRecord
from .reminder_definition_channels import ReminderDefinitionChannelRecord
from .reminder_schedule_rules import ReminderScheduleRuleRecord
from .reminders import ReminderDefinitionRecord, ReminderOccurrenceRecord
from .symptom_codes import SymptomCodeRecord
from .user_conditions import UserConditionRecord
from .user_disliked_ingredients import UserDislikedIngredientRecord
from .user_meal_schedule import UserMealScheduleRecord
from .user_medications import UserMedicationRecord
from .user_nutrition_goals import UserNutritionGoalRecord

# Expose all defined models for external use
__all__ = [
    "AccountRecord",
    "BaseRecord",
    "TimestampMixin",
    "BiomarkerReadingRecord",
    "SymptomCheckInRecord",
    "AlertOutboxRecord",
    "ReminderEventRecord",
    "MealComponentRecord",
    "MealRecordRecord",
    "MedicationAdherenceRecord",
    "MedicationRegimenRecord",
    "UserProfileRecord",
    "ReminderDefinitionChannelRecord",
    "ReminderScheduleRuleRecord",
    "ReminderDefinitionRecord",
    "ReminderOccurrenceRecord",
    "SymptomCodeRecord",
    "UserConditionRecord",
    "UserDislikedIngredientRecord",
    "UserMealScheduleRecord",
    "UserMedicationRecord",
    "UserNutritionGoalRecord",
    # Add new auth models to __all__
    "AuthUser",
    "AuthSession",
    "AuthAuditEvent",
    "AuthLoginFailure",
]

# Ensure all models are registered with SQLModel.metadata
# This is crucial for Alembic to detect all defined tables and relationships.
# Iterating through __all__ and accessing the record ensures registration.
for model_name in __all__:
    if model_name in globals():  # Check if the name is actually defined in this scope
        model = globals()[model_name]
        if isinstance(model, type) and issubclass(model, SQLModel):
            # Use setdefault to avoid issues if metadata is already populated
            # Note: This registration logic might be more complex or handled elsewhere.
            # For now, assuming a direct approach. If SQLModel.metadata is managed globally,
            # this might not be strictly necessary for Alembic detection, but good for clarity.
            # Avoid creating tables directly here, rely on Alembic for schema management.
            pass  # Pass as direct table creation is not the goal here.
