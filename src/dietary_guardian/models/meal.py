from datetime import datetime
from enum import StrEnum
from typing import Literal
from pydantic import BaseModel, Field


class GlycemicIndexLevel(StrEnum):
    LOW = "Low (<55)"
    MEDIUM = "Medium (56-69)"
    HIGH = "High (>70)"
    UNKNOWN = "Unknown"


class PortionSize(StrEnum):
    SMALL = "Small (e.g., half bowl)"
    STANDARD = "Standard (e.g., full bowl)"
    LARGE = "Large (e.g., upsized)"
    FAMILY = "Family Share"


class Ingredient(BaseModel):
    name: str
    amount_g: float | None = None
    is_hidden: bool = Field(default=False, description="e.g., sugar in gravy, hidden lard")
    allergen_info: list[str] | None = Field(default_factory=list)


class Nutrition(BaseModel):
    calories: float = Field(..., ge=0, description="kcal")
    carbs_g: float = Field(..., ge=0)
    sugar_g: float = Field(..., ge=0)
    protein_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)
    sodium_mg: float = Field(..., ge=0)
    fiber_g: float | None = Field(default=0.0, ge=0)


class LocalizationDetails(BaseModel):
    """
    Captures the specific cultural nuance of the dish.
    """
    dialect_name: str | None = Field(None, description="e.g., 'Char Kway Teow' (Hokkien)")
    variant: str | None = Field(None, description="e.g., 'Penang Style' vs 'Singapore Style'")
    detected_components: list[str] = Field(default_factory=list, description="Specific local ingredients found e.g., 'Hum' (Cockles), 'Lard Cubes'")


class SafetyAnalysis(BaseModel):
    is_safe_for_consumption: bool = True
    risk_factors: list[str] = Field(default_factory=list, description="e.g., 'High Sodium', 'High Sugar'")
    diabetic_warning: bool = False
    hypertensive_warning: bool = False


class MealState(BaseModel):
    """
    The 'Gold Standard' output for the Hawker Vision Module.
    This schema is the contract between Perception and Reasoning/Safety.
    """
    dish_name: str = Field(..., description="Standardized English name")
    confidence_score: float = Field(..., ge=0, le=1, description="Model's confidence in identification")
    identification_method: Literal["AI_Flash", "HPB_Fallback", "User_Manual"]
    
    # Core Data
    ingredients: list[Ingredient]
    nutrition: Nutrition
    portion_size: PortionSize = PortionSize.STANDARD
    glycemic_index_estimate: GlycemicIndexLevel = GlycemicIndexLevel.UNKNOWN
    
    # Cultural Context
    localization: LocalizationDetails = Field(default_factory=LocalizationDetails)
    
    # Visual Analysis
    visual_anomalies: list[str] = Field(
        default_factory=list,
        description="e.g., 'Excessive oil sheen', 'Gravy separation'",
    )
    
    # Recommendations
    suggested_modifications: list[str] = Field(
        default_factory=list, 
        description="Actionable advice e.g., 'Ask for less gravy'"
    )


class MealEvent(BaseModel):
    """
    Simplified meal representation for user input or manual logging.
    """
    name: str
    ingredients: list[Ingredient] = Field(default_factory=list)
    nutrition: Nutrition
    timestamp: datetime = Field(default_factory=datetime.now)


class VisionResult(BaseModel):
    """
    Wrapper for the vision pipeline result.
    """
    primary_state: MealState
    raw_ai_output: str
    needs_manual_review: bool = False
    processing_latency_ms: float = 0.0
    model_version: str = "gemini-flash-1.5"


class ImageInput(BaseModel):
    source: Literal["upload", "camera"]
    filename: str | None = None
    mime_type: str
    content: bytes
    metadata: dict[str, str] = Field(default_factory=dict)
