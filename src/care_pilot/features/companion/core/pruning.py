"""
Implement context pruning for PatientCaseSnapshot.

This module provides logic to keep context concise, relevant, and within
token limits by applying temporal, relevance-based, and summarization rules.
"""

from __future__ import annotations

from care_pilot.features.companion.core.domain import PatientCaseSnapshot
from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


class PruningService:
    def __init__(
        self,
        *,
        max_recent_meals: int = 5,
        max_recent_symptoms: int = 5,
        max_recent_emotions: int = 5,
    ) -> None:
        self.max_recent_meals = max_recent_meals
        self.max_recent_symptoms = max_recent_symptoms
        self.max_recent_emotions = max_recent_emotions

    def prune(self, snapshot: PatientCaseSnapshot) -> PatientCaseSnapshot:
        """
        Apply pruning rules to a snapshot.
        Currently implements temporal pruning (limiting list sizes).
        """
        # Temporal pruning for meals
        if len(snapshot.recent_meals) > self.max_recent_meals:
            logger.debug(
                "pruning_recent_meals user_id=%s from=%s to=%s",
                snapshot.user_id,
                len(snapshot.recent_meals),
                self.max_recent_meals,
            )
            snapshot.recent_meals = snapshot.recent_meals[-self.max_recent_meals :]

        # Temporal pruning for symptoms
        if len(snapshot.recent_symptoms) > self.max_recent_symptoms:
            logger.debug(
                "pruning_recent_symptoms user_id=%s from=%s to=%s",
                snapshot.user_id,
                len(snapshot.recent_symptoms),
                self.max_recent_symptoms,
            )
            snapshot.recent_symptoms = snapshot.recent_symptoms[-self.max_recent_symptoms :]

        # Temporal pruning for emotions
        if len(snapshot.recent_emotion_markers) > self.max_recent_emotions:
            logger.debug(
                "pruning_recent_emotions user_id=%s from=%s to=%s",
                snapshot.user_id,
                len(snapshot.recent_emotion_markers),
                self.max_recent_emotions,
            )
            snapshot.recent_emotion_markers = snapshot.recent_emotion_markers[
                -self.max_recent_emotions :
            ]

        return snapshot

    def prune_by_relevance(
        self, snapshot: PatientCaseSnapshot, query: str
    ) -> PatientCaseSnapshot:
        """
        Heuristic-based relevance pruning.
        If the query is about a specific area, keep more context for that area.
        """
        query_lower = query.lower()

        # Simple keyword heuristics
        is_medication_query = any(k in query_lower for k in ["med", "pill", "drug", "take"])
        is_meal_query = any(k in query_lower for k in ["eat", "meal", "food", "sugar", "carbs"])

        if is_medication_query and not is_meal_query:
            # Keep fewer meals to save space for medication context if needed
            snapshot.recent_meals = snapshot.recent_meals[-2:]
        elif is_meal_query and not is_medication_query:
            # Keep fewer symptoms/emotions to save space for meal context
            snapshot.recent_symptoms = snapshot.recent_symptoms[-2:]
            snapshot.recent_emotion_markers = snapshot.recent_emotion_markers[-2:]

        return snapshot
