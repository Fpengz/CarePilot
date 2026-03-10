"""Package exports for food."""

from .ingestion import load_open_food_facts_records, load_usda_records

__all__ = ["load_open_food_facts_records", "load_usda_records"]
