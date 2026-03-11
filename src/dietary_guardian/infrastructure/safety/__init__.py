"""Infrastructure adapters for clinical safety data.

Provides ``DrugInteractionDB`` — a SQLite-backed store for
drug–food contraindication data used by the safety engine.
"""

from dietary_guardian.infrastructure.safety.drug_interaction_db import DrugInteractionDB

__all__ = ["DrugInteractionDB"]
