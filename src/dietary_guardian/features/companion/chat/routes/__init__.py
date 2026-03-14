"""Internal chat route handlers."""

from dietary_guardian.features.companion.chat.routes.base import BaseRoute, RouteResult
from dietary_guardian.features.companion.chat.routes.code_route import CodeRoute
from dietary_guardian.features.companion.chat.routes.drug_route import DrugRoute
from dietary_guardian.features.companion.chat.routes.food_route import FoodRoute

__all__ = [
    "BaseRoute",
    "CodeRoute",
    "DrugRoute",
    "FoodRoute",
    "RouteResult",
]
