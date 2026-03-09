"""Canonical domain exports for the companion architecture."""
# ruff: noqa: F401

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .alerts import AlertDeliveryResult, AlertMessage, AlertSeverity, OutboxRecord
    from .care import (
        CarePlan,
        CaseSnapshot,
        ClinicianDigest,
        CompanionInteraction,
        CompanionInteractionResult,
        EngagementAssessment,
        EvidenceBundle,
        EvidenceCitation,
        ImpactSummary,
        InteractionGoal,
        InteractionType,
        PersonalizationContext,
        PolicyStatus,
        SafetyDecision,
    )
    from .health import (
        BiomarkerReading,
        ClinicalProfileSnapshot,
        HealthProfileOnboardingState,
        HealthProfileRecord,
        MedicationAdherenceEvent,
        MedicationAdherenceMetrics,
        MetricPoint,
        MetricTrend,
        ProfileCompleteness,
        ReportInput,
        SymptomCheckIn,
        SymptomSafety,
        SymptomSummary,
    )
    from .identity import (
        AccountPrincipal,
        AccountRole,
        MealScheduleWindow,
        MealSlot,
        MedicalCondition,
        Medication,
        PermissionScope,
        ProfileMode,
        UserProfile,
    )
    from .meals import (
        EnrichedMealEvent,
        MealNutritionProfile,
        MealPerception,
        MealPortionEstimate,
        NormalizedMealItem,
        PerceivedMealItem,
        PortionReference,
        RawFoodSourceRecord,
    )
    from .notifications import (
        MedicationRegimen,
        MobilityReminderSettings,
        QueuedReminderNotification,
        ReminderEvent,
        ReminderNotificationEndpoint,
        ReminderNotificationLogEntry,
        ReminderNotificationPreference,
        ScheduledReminderNotification,
    )
    from .recommendations import (
        AgentProfileState,
        AgentRecommendationCard,
        CandidateScores,
        CanonicalFoodAdvice,
        CanonicalFoodAlternative,
        CanonicalFoodRecord,
        DailyAgentRecommendation,
        DailySuggestionBundle,
        DailySuggestionItem,
        HealthDelta,
        MealCatalogItem,
        PreferenceSnapshot,
        RecommendationInteraction,
        RecommendationOutput,
        SourceMealSummary,
        SubstitutionAlternative,
        SubstitutionPlan,
        TemporalContext,
    )
    from .workflows import ToolRolePolicyRecord, WorkflowContractSnapshotRecord, WorkflowTimelineEvent

_EXPORT_MODULES = {
    "AccountPrincipal": ".identity",
    "AccountRole": ".identity",
    "AgentProfileState": ".recommendations",
    "AgentRecommendationCard": ".recommendations",
    "AlertDeliveryResult": ".alerts",
    "AlertMessage": ".alerts",
    "AlertSeverity": ".alerts",
    "BiomarkerReading": ".health",
    "CandidateScores": ".recommendations",
    "CanonicalFoodAdvice": ".recommendations",
    "CanonicalFoodAlternative": ".recommendations",
    "CanonicalFoodRecord": ".recommendations",
    "CarePlan": ".care",
    "CaseSnapshot": ".care",
    "ClinicalProfileSnapshot": ".health",
    "ClinicianDigest": ".care",
    "CompanionInteraction": ".care",
    "CompanionInteractionResult": ".care",
    "DailyAgentRecommendation": ".recommendations",
    "DailySuggestionBundle": ".recommendations",
    "DailySuggestionItem": ".recommendations",
    "EnrichedMealEvent": ".meals",
    "EngagementAssessment": ".care",
    "EvidenceBundle": ".care",
    "EvidenceCitation": ".care",
    "HealthDelta": ".recommendations",
    "HealthProfileOnboardingState": ".health",
    "HealthProfileRecord": ".health",
    "ImpactSummary": ".care",
    "InteractionGoal": ".care",
    "InteractionType": ".care",
    "MealCatalogItem": ".recommendations",
    "MealNutritionProfile": ".meals",
    "MealPerception": ".meals",
    "MealPortionEstimate": ".meals",
    "MealScheduleWindow": ".identity",
    "MealSlot": ".identity",
    "Medication": ".identity",
    "MedicationAdherenceEvent": ".health",
    "MedicationAdherenceMetrics": ".health",
    "MedicationRegimen": ".notifications",
    "MedicalCondition": ".identity",
    "MetricPoint": ".health",
    "MetricTrend": ".health",
    "MobilityReminderSettings": ".notifications",
    "NormalizedMealItem": ".meals",
    "OutboxRecord": ".alerts",
    "PerceivedMealItem": ".meals",
    "PermissionScope": ".identity",
    "PersonalizationContext": ".care",
    "PolicyStatus": ".care",
    "PortionReference": ".meals",
    "PreferenceSnapshot": ".recommendations",
    "ProfileCompleteness": ".health",
    "ProfileMode": ".identity",
    "QueuedReminderNotification": ".notifications",
    "RawFoodSourceRecord": ".meals",
    "RecommendationInteraction": ".recommendations",
    "RecommendationOutput": ".recommendations",
    "ReminderEvent": ".notifications",
    "ReminderNotificationEndpoint": ".notifications",
    "ReminderNotificationLogEntry": ".notifications",
    "ReminderNotificationPreference": ".notifications",
    "ReportInput": ".health",
    "SafetyDecision": ".care",
    "ScheduledReminderNotification": ".notifications",
    "SourceMealSummary": ".recommendations",
    "SubstitutionAlternative": ".recommendations",
    "SubstitutionPlan": ".recommendations",
    "SymptomCheckIn": ".health",
    "SymptomSafety": ".health",
    "SymptomSummary": ".health",
    "TemporalContext": ".recommendations",
    "ToolRolePolicyRecord": ".workflows",
    "UserProfile": ".identity",
    "WorkflowContractSnapshotRecord": ".workflows",
    "WorkflowTimelineEvent": ".workflows",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> Any:
    if name not in _EXPORT_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_EXPORT_MODULES[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
