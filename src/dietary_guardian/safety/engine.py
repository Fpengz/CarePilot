import logfire
from typing import Any, cast
from dietary_guardian.models.meal import MealEvent, MealState
from dietary_guardian.models.user import UserProfile
from dietary_guardian.safety.db import DrugInteractionDB

logfire_api = cast(Any, logfire)


class SafetyViolation(Exception):
    def __init__(self, message: str, level: str = "Critical", reason: str = ""):
        self.message = message
        self.level = level
        self.reason = reason
        super().__init__(self.message)


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

            if nutrition.sodium_mg > self.user.daily_sodium_limit_mg * 0.5:
                warning = f"High Sodium Alert: {nutrition.sodium_mg}mg (50% of daily limit)"
                logfire_api.warn(
                    "nutritional_threshold_exceeded",
                    nutrient="sodium",
                    value=nutrition.sodium_mg,
                )
                warnings.append(warning)

            if nutrition.sugar_g > self.user.daily_sugar_limit_g * 0.3:
                warning = f"High Sugar Alert: {nutrition.sugar_g}g sugar detected."
                logfire_api.warn(
                    "nutritional_threshold_exceeded",
                    nutrient="sugar",
                    value=nutrition.sugar_g,
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
