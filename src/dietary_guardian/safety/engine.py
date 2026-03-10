from typing import Any, cast

import logfire
from dietary_guardian.domain.identity.models import UserProfile
from dietary_guardian.models.meal import MealEvent, MealState
from dietary_guardian.safety.db import DrugInteractionDB
from dietary_guardian.safety.exceptions import SafetyViolation
from dietary_guardian.safety.thresholds import (
    HYPOGLYCEMIA_LOW_CARB_THRESHOLD_G,
    SODIUM_WARNING_FRACTION,
    SUGAR_WARNING_FRACTION,
)

logfire_api = cast(Any, logfire)


class SafetyEngine:
    def __init__(self, user: UserProfile, db: DrugInteractionDB | None = None):
        self.user = user
        self.db = db or DrugInteractionDB()

    def validate_meal(self, meal: MealEvent | MealState) -> list[str]:
        """
        Validates a meal against user's medical conditions and medications using DrugInteractionDB.
        """
        with logfire_api.span(
            "safety_validation",
            user_id=self.user.id,
            dish=getattr(meal, "name", getattr(meal, "dish_name", "Unknown")),
        ):
            warnings = []

            # 1. Nutritional Threshold Checks
            nutrition = meal.nutrition
            ingredients = [i.name for i in meal.ingredients]

            if nutrition.sodium_mg > self.user.daily_sodium_limit_mg * SODIUM_WARNING_FRACTION:
                warning = f"High Sodium Alert: {nutrition.sodium_mg}mg (50% of daily limit)"
                logfire_api.warn(
                    "nutritional_threshold_exceeded",
                    nutrient="sodium",
                    value=nutrition.sodium_mg,
                )
                warnings.append(warning)

            if nutrition.sugar_g > self.user.daily_sugar_limit_g * SUGAR_WARNING_FRACTION:
                warning = f"High Sugar Alert: {nutrition.sugar_g}g sugar detected."
                logfire_api.warn(
                    "nutritional_threshold_exceeded",
                    nutrient="sugar",
                    value=nutrition.sugar_g,
                )
                warnings.append(warning)

            # 1b. Hypoglycemia caution for glucose-lowering regimens.
            has_glucose_lowering_med = any(
                med.name.strip().lower() in {"insulin", "glibenclamide", "gliclazide"}
                for med in self.user.medications
            )
            if has_glucose_lowering_med and nutrition.carbs_g < HYPOGLYCEMIA_LOW_CARB_THRESHOLD_G:
                warning = (
                    f"Hypoglycemia Risk: {nutrition.carbs_g}g carbohydrates may be too low "
                    "for current glucose-lowering medication."
                )
                logfire_api.warn(
                    "hypoglycemia_risk_warning",
                    carbs_g=nutrition.carbs_g,
                    threshold_g=HYPOGLYCEMIA_LOW_CARB_THRESHOLD_G,
                )
                warnings.append(warning)

            # 2. Database-backed Clinical Checks
            for med in self.user.medications:
                clinical_contras = self.db.get_contraindications(med.name)
                for restricted_item, reason, severity in clinical_contras:
                    if self._contains_item(ingredients, restricted_item):
                        if severity == "Critical":
                            logfire_api.error(
                                "critical_safety_violation",
                                med=med.name,
                                item=restricted_item,
                                reason=reason,
                            )
                            raise SafetyViolation(
                                message=f"CRITICAL SAFETY ALERT: {restricted_item} interacts with {med.name}.",
                                level=severity,
                                reason=reason,
                            )
                        else:
                            warning = f"{severity} Warning: {restricted_item} might interact with {med.name}. {reason}"
                            logfire_api.warn(
                                "clinical_warning",
                                med=med.name,
                                item=restricted_item,
                                severity=severity,
                            )
                            warnings.append(warning)

            return warnings

    def _contains_item(self, ingredients: list[str], item: str) -> bool:
        item = item.lower()
        return any(item in ing.lower() for ing in ingredients)
