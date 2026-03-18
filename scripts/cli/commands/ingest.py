from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Annotated

import typer
from scripts.cli.utils import error, info, load_root_env, warning

from care_pilot.config.app import get_settings
from care_pilot.features.recommendations.domain.canonical_food_matching import (
    normalize_text,
)
from care_pilot.features.recommendations.domain.models import (
    CanonicalFoodRecord,
)
from care_pilot.platform.persistence.food import (
    FoodInfoIngester,
    load_default_canonical_food_records,
    load_open_food_facts_records,
    load_usda_records,
)
from care_pilot.platform.persistence.sqlite_repository import SQLiteRepository

ingest_app = typer.Typer(help="Ingest food datasets into local stores.")


def _resolve_app_db_path() -> str:
    settings = get_settings()
    return settings.storage.api_sqlite_db_path


def _ensure_app_db(db_path: str) -> None:
    SQLiteRepository(db_path)


def _persist_canonical_food_records(
    records: list[CanonicalFoodRecord],
    *,
    db_path: str,
    reset: bool,
) -> None:
    _ensure_app_db(db_path)
    with sqlite3.connect(db_path) as conn:
        if reset:
            conn.execute("DELETE FROM portion_reference")
            conn.execute("DELETE FROM food_alias")
            conn.execute("DELETE FROM canonical_foods")

        canonical_rows: list[tuple[str, str, str, int, str]] = []
        alias_rows: list[tuple[str, str, str, int]] = []
        portion_rows: list[tuple[str, str, float, float]] = []

        for item in records:
            canonical_rows.append(
                (
                    item.food_id,
                    item.locale,
                    item.slot,
                    1 if item.active else 0,
                    item.model_dump_json(),
                )
            )
            aliases = item.aliases_normalized or [normalize_text(item.title)]
            for index, alias in enumerate(aliases, start=1):
                alias_rows.append((alias, item.food_id, "canonical", index))
            for portion in item.portion_references:
                portion_rows.append(
                    (
                        item.food_id,
                        portion.unit,
                        portion.grams,
                        portion.confidence,
                    )
                )

        conn.executemany(
            """
            INSERT OR REPLACE INTO canonical_foods (food_id, locale, slot, active, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            canonical_rows,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO food_alias (alias, food_id, alias_type, priority)
            VALUES (?, ?, ?, ?)
            """,
            alias_rows,
        )
        conn.executemany(
            """
            INSERT OR REPLACE INTO portion_reference (food_id, unit, grams, confidence)
            VALUES (?, ?, ?, ?)
            """,
            portion_rows,
        )
        conn.commit()


@ingest_app.command("local")
def ingest_local() -> None:
    """Ingest hawker + drinks JSON into ChromaDB."""
    load_root_env()
    FoodInfoIngester().run()


@ingest_app.command("canonical")
def ingest_canonical(
    reset: Annotated[
        bool,
        typer.Option("--reset", help="Reset canonical food tables before ingest."),
    ] = False,
) -> None:
    """Ingest canonical food JSON into SQLite."""
    load_root_env()
    records = load_default_canonical_food_records()
    if not records:
        warning("Canonical food seed is empty; nothing to ingest.")
        return
    _persist_canonical_food_records(
        records, db_path=_resolve_app_db_path(), reset=reset
    )
    info(f"Ingested {len(records)} canonical food records into SQLite.")


@ingest_app.command("usda")
def ingest_usda(
    path: Annotated[Path, typer.Argument(help="Path to USDA JSON export.")],
    reset: Annotated[
        bool,
        typer.Option("--reset", help="Reset canonical food tables before ingest."),
    ] = False,
) -> None:
    load_root_env()
    if not path.exists():
        error(f"Missing USDA file: {path}")
        raise typer.Exit(1)
    records = load_usda_records(path)
    _persist_canonical_food_records(
        records, db_path=_resolve_app_db_path(), reset=reset
    )
    info(f"Ingested {len(records)} USDA records into canonical foods.")


@ingest_app.command("off")
def ingest_open_food_facts(
    path: Annotated[Path, typer.Argument(help="Path to Open Food Facts JSON export.")],
    reset: Annotated[
        bool,
        typer.Option("--reset", help="Reset canonical food tables before ingest."),
    ] = False,
) -> None:
    load_root_env()
    if not path.exists():
        error(f"Missing Open Food Facts file: {path}")
        raise typer.Exit(1)
    records = load_open_food_facts_records(path)
    _persist_canonical_food_records(
        records, db_path=_resolve_app_db_path(), reset=reset
    )
    info(f"Ingested {len(records)} Open Food Facts records into canonical foods.")
