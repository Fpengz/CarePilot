"""Domain model definitions for the recommendations subdomain: food catalog, preferences, and suggestion bundles."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from dietary_guardian.domain.identity.models import MealSlot
from dietary_guardian.domain.meals.models import PortionReference
from dietary_guardian.models.meal import Nutrition

InteractionEventType = Literal[
    "viewed",
    "accepted",
    "dismissed",
    "swap_selected",
    "meal_logged_after_recommendation",
    "ignored",
]


class RecommendationOutput(BaseModel):
    safe: bool
    rationale: str
    localized_advice: list[str] = Field(default_factory=list)
    blocked_reason: str | None = None
    evidence: dict[str, float] = Field(default_factory=dict)


class DailySuggestionItem(BaseModel):
    slot: MealSlot
    title: str
    venue_type: str
    why_it_fits: list[str] = Field(default_factory=list)
    caution_notes: list[str] = Field(default_factory=list)
    confidence: float


class DailySuggestionBundle(BaseModel):
    locale: str
    generated_at: str
    data_sources: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    suggestions: dict[str, DailySuggestionItem]


class MealCatalogItem(BaseModel):
    meal_id: str
    title: str
    locale: str = "en-SG"
    slot: MealSlot
    venue_type: str
    cuisine_tags: list[str] = Field(default_factory=list)
    ingredient_tags: list[str] = Field(default_factory=list)
    preparation_tags: list[str] = Field(default_factory=list)
    nutrition: Nutrition
    price_tier: Literal["budget", "moderate", "flexible"] = "moderate"
    health_tags: list[str] = Field(default_factory=list)
    active: bool = True


class RecommendationInteraction(BaseModel):
    interaction_id: str
    user_id: str
    recommendation_id: str
    candidate_id: str
    event_type: InteractionEventType
    slot: MealSlot
    source_meal_id: str | None = None
    selected_meal_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, object] = Field(default_factory=dict)


class PreferenceSnapshot(BaseModel):
    user_id: str
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    interaction_count: int = 0
    accepted_count: int = 0
    dismissed_count: int = 0
    swap_selected_count: int = 0
    cuisine_affinity: dict[str, float] = Field(default_factory=dict)
    ingredient_affinity: dict[str, float] = Field(default_factory=dict)
    health_tag_affinity: dict[str, float] = Field(default_factory=dict)
    slot_affinity: dict[str, float] = Field(default_factory=dict)
    substitution_tolerance: float = 0.6
    adherence_bias: float = 0.0


class CandidateScores(BaseModel):
    preference_fit: float
    temporal_fit: float
    adherence_likelihood: float
    health_gain: float
    substitution_deviation_penalty: float
    total_score: float


class HealthDelta(BaseModel):
    calories: float
    sugar_g: float
    sodium_mg: float


class AgentRecommendationCard(BaseModel):
    candidate_id: str
    slot: MealSlot
    title: str
    venue_type: str
    why_it_fits: list[str] = Field(default_factory=list)
    caution_notes: list[str] = Field(default_factory=list)
    confidence: float
    scores: CandidateScores
    health_gain_summary: HealthDelta


class SourceMealSummary(BaseModel):
    meal_id: str
    title: str
    slot: MealSlot


class SubstitutionAlternative(BaseModel):
    candidate_id: str
    title: str
    venue_type: str
    health_delta: HealthDelta
    taste_distance: float
    reasoning: str
    confidence: float


class SubstitutionPlan(BaseModel):
    source_meal: SourceMealSummary
    alternatives: list[SubstitutionAlternative] = Field(default_factory=list)
    blocked_reason: str | None = None


class TemporalContext(BaseModel):
    current_slot: MealSlot
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meal_history_count: int
    interaction_count: int
    recent_repeat_titles: list[str] = Field(default_factory=list)
    slot_history_counts: dict[str, int] = Field(default_factory=dict)


class AgentProfileState(BaseModel):
    completeness_state: str
    bmi: float | None = None
    target_calories_per_day: float | None = None
    macro_focus: list[str] = Field(default_factory=list)


class DailyAgentRecommendation(BaseModel):
    profile_state: AgentProfileState
    temporal_context: TemporalContext
    recommendations: dict[str, AgentRecommendationCard]
    substitutions: SubstitutionPlan | None = None
    fallback_mode: bool
    data_sources: dict[str, object] = Field(default_factory=dict)
    constraints_applied: list[str] = Field(default_factory=list)


class CanonicalFoodAlternative(BaseModel):
    name_en: str
    name_cn: str | None = None
    benefit: str


class CanonicalFoodAdvice(BaseModel):
    cn: str | None = None
    en: str
    risk_level: str | None = None


class CanonicalFoodRecord(BaseModel):
    food_id: str
    title: str
    locale: str = "en-SG"
    aliases: list[str] = Field(default_factory=list)
    aliases_normalized: list[str] = Field(default_factory=list)
    slot: MealSlot
    venue_type: str
    cuisine_tags: list[str] = Field(default_factory=list)
    ingredient_tags: list[str] = Field(default_factory=list)
    preparation_tags: list[str] = Field(default_factory=list)
    nutrition: Nutrition
    price_tier: Literal["budget", "moderate", "flexible"] = "moderate"
    health_tags: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    glycemic_index_label: str | None = None
    glycemic_index_value: int | None = None
    disease_advice: dict[str, CanonicalFoodAdvice] = Field(default_factory=dict)
    alternatives: list[CanonicalFoodAlternative] = Field(default_factory=list)
    serving_size: str | None = None
    default_portion_grams: float | None = None
    portion_references: list[PortionReference] = Field(default_factory=list)
    source_dataset: str = "internal"
    source_type: str = "seed"
    localization_variant: str | None = None
    active: bool = True

    @property
    def meal_id(self) -> str:
        return self.food_id
