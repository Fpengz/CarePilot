"""
Define reminder outbox enumerations.

This module contains enums for reminder states, metrics, and delivery channels.
"""

from __future__ import annotations

from enum import StrEnum


class ReminderState(StrEnum):
    SCHEDULED = "SCHEDULED"
    ENQUEUED = "ENQUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    ACKED = "ACKED"
    SNOOZED = "SNOOZED"
    IGNORED = "IGNORED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class ReminderType(StrEnum):
    MEDICATION = "MEDICATION"
    THRESHOLD_ALERT = "THRESHOLD_ALERT"
    MEASUREMENT = "MEASUREMENT"
    FOOD_RECORD = "FOOD_RECORD"


class MetricType(StrEnum):
    HEART_RATE = "heart_rate"
    BLOOD_GLUCOSE = "blood_glucose"


class ReminderChannel(StrEnum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    IN_APP = "in_app"


class MealType(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
