from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from sqlmodel import SQLModel

REPO_ROOT = Path(__file__).resolve().parents[2]


def ensure_import_path() -> None:
    src_path = REPO_ROOT / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


def render_schema() -> list[str]:
    # Import models to register SQLModel metadata.
    from care_pilot.platform.persistence import models  # noqa: F401

    lines: list[str] = []
    lines.append("# Database Schema (SQLModel)")
    lines.append("")
    lines.append("_Generated from SQLModel metadata. Do not edit by hand._")
    lines.append("")
    lines.append(f"- Generated: {date.today().isoformat()}")
    lines.append("- Source: `src/care_pilot/platform/persistence/models`")
    lines.append("- Command: `uv run python scripts/docs/generate_db_schema.py`")
    lines.append("")

    tables = list(SQLModel.metadata.sorted_tables)
    if not tables:
        lines.append("No tables registered in SQLModel.metadata.")
        return lines

    lines.append("## Tables")
    lines.append("")
    for table in tables:
        lines.append(f"### {table.name}")
        lines.append("")
        lines.append("| Column | Type | Nullable | Primary Key |")
        lines.append("| --- | --- | --- | --- |")
        for column in table.columns:
            col_type = str(column.type)
            lines.append(
                f"| {column.name} | {col_type} | {column.nullable} | {column.primary_key} |"
            )
        lines.append("")

    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SQLModel schema docs.")
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / "docs" / "generated" / "db-schema.md"),
        help="Output markdown path",
    )
    args = parser.parse_args()

    ensure_import_path()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = render_schema()
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
