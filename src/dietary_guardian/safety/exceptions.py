from typing import Optional

from dietary_guardian.models.meal import MealState


class HumanInTheLoopException(Exception):
    """Raised when automated perception confidence is too low and human review is required.

    Attributes:
        message: short description
        meal_state: optional partial MealState produced by the agent
    """

    def __init__(self, message: str, meal_state: Optional[MealState] = None):
        super().__init__(message)
        self.meal_state = meal_state
