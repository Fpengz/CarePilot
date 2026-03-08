from dietary_guardian.models.meal import MealState


class SafetyViolation(Exception):
    def __init__(self, message: str, level: str = "Critical", reason: str = ""):
        self.message = message
        self.level = level
        self.reason = reason
        super().__init__(self.message)


class HumanInTheLoopException(Exception):
    """Raised when automated perception confidence is too low and human review is required.

    Attributes:
        message: short description
        meal_state: optional partial MealState produced by the agent
    """

    def __init__(self, message: str, meal_state: MealState | None = None):
        super().__init__(message)
        self.meal_state = meal_state
