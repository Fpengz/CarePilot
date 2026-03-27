"""
Define data models for the persistence layer.

This module serves as the entry point for all persistence models,
ensuring that all ORM-mapped classes are discoverable and correctly
registered with SQLModel.metadata.
"""

from sqlmodel import SQLModel

from .auth import AccountRecord
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
from .user_medications import UserMedicationRecord

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
    "UserMedicationRecord",
]

# Ensure all models are registered with SQLModel.metadata
# This is crucial for Alembic to detect all defined tables and relationships.
# Iterating through __all__ and accessing the record ensures registration.
for model_name in __all__:
    model = globals()[model_name]
    if isinstance(model, type) and issubclass(model, SQLModel):
        # Use setdefault to avoid issues if metadata is already populated
        SQLModel.metadata.tables.setdefault(model.model_json_schema()["title"], model.model_json_schema())
