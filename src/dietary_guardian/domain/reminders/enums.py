from __future__ import annotations

from enum import Enum


class ReminderState(str, Enum):
    SCHEDULED = "SCHEDULED"
    ENQUEUED = "ENQUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    ACKED = "ACKED"
    SNOOZED = "SNOOZED"
    IGNORED = "IGNORED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class ReminderType(str, Enum):
    MEDICATION = "MEDICATION"
    THRESHOLD_ALERT = "THRESHOLD_ALERT"
    MEASUREMENT = "MEASUREMENT"
    FOOD_RECORD = "FOOD_RECORD"


class MetricType(str, Enum):
    HEART_RATE = "heart_rate"
    BLOOD_GLUCOSE = "blood_glucose"


class ReminderChannel(str, Enum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    IN_APP = "in_app"


class MealType(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"