"""Infrastructure adapters for clinical safety data.

Provides ``DrugInteractionDB`` — a SQLite-backed store for
drug–food contraindication data used by the safety engine.
"""

from care_pilot.features.safety.infra.drug_interaction_db import (
    DrugInteractionDB,
)

__all__ = ["DrugInteractionDB"]
