from datetime import datetime
from enum import Enum
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class GlycemicIndexLevel(str, Enum):
    LOW = "Low (<55)"
    MEDIUM = "Medium (56-69)"
    HIGH = "High (>70)"
    UNKNOWN = "Unknown"


class PortionSize(str, Enum):
    SMALL = "Small (e.g., half bowl)"
    STANDARD = "Standard (e.g., full bowl)"
    LARGE = "Large (e.g., upsized)"
    FAMILY = "Family Share"


class Ingredient(BaseModel):
    name: str
    amount_g: Optional[float] = None
    is_hidden: bool = Field(default=False, description="e.g., sugar in gravy, hidden lard")
    allergen_info: Optional[List[str]] = Field(default_factory=list)


class Nutrition(BaseModel):
    calories: float = Field(..., ge=0, description="kcal")
    carbs_g: float = Field(..., ge=0)
    sugar_g: float = Field(..., ge=0)
    protein_g: float = Field(..., ge=0)
    fat_g: float = Field(..., ge=0)
    sodium_mg: float = Field(..., ge=0)
    fiber_g: Optional[float] = Field(default=0.0, ge=0)


class LocalizationDetails(BaseModel):
    """
    Captures the specific cultural nuance of the dish.
    """
    dialect_name: Optional[str] = Field(None, description="e.g., 'Char Kway Teow' (Hokkien)")
    variant: Optional[str] = Field(None, description="e.g., 'Penang Style' vs 'Singapore Style'")
    detected_components: List[str] = Field(default_factory=list, description="Specific local ingredients found e.g., 'Hum' (Cockles), 'Lard Cubes'")


class SafetyAnalysis(BaseModel):
    is_safe_for_consumption: bool = True
    risk_factors: List[str] = Field(default_factory=list, description="e.g., 'High Sodium', 'High Sugar'")
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
    ingredients: List[Ingredient]
    nutrition: Nutrition
    portion_size: PortionSize = PortionSize.STANDARD
    glycemic_index_estimate: GlycemicIndexLevel = GlycemicIndexLevel.UNKNOWN
    
    # Cultural Context
    localization: LocalizationDetails = Field(default_factory=LocalizationDetails)
    
    # Visual Analysis
    visual_anomalies: List[str] = Field(
        default_factory=list,
        description="e.g., 'Excessive oil sheen', 'Gravy separation'",
    )
    
    # Recommendations
    suggested_modifications: List[str] = Field(
        default_factory=list, 
        description="Actionable advice e.g., 'Ask for less gravy'"
    )


class MealEvent(BaseModel):
    """
    Simplified meal representation for user input or manual logging.
    """
    name: str
    ingredients: List[Ingredient] = Field(default_factory=list)
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
