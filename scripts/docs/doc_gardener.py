from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class IndexEntry:
    doc_path: Path
    status: str
    last_verified: date | None
    owner: str
    index_path: Path


def iter_index_entries(index_path: Path) -> list[IndexEntry]:
    entries: list[IndexEntry] = []
    text = index_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "|" not in line:
            continue
        if line.strip().startswith("| ---"):
            continue
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        doc_cell, status, last_verified, owner = cells[:4]
        if doc_cell.strip().lower() == "doc":
            continue
        match = re.search(r"`([^`]+)`", doc_cell)
        doc_value = match.group(1) if match else doc_cell
        if not doc_value:
            continue
        parsed_date = None
        if DATE_RE.match(last_verified):
            parsed_date = date.fromisoformat(last_verified)
        entries.append(
            IndexEntry(
                doc_path=Path(doc_value),
                status=status,
                last_verified=parsed_date,
                owner=owner,
                index_path=index_path,
            )
        )
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Report stale or deprecated docs.")
    parser.add_argument("--stale-days", type=int, default=90)
    args = parser.parse_args()

    today = date.today()
    index_paths = [
        DOCS_ROOT / "design-docs" / "index.md",
        DOCS_ROOT / "exec-plans" / "index.md",
        DOCS_ROOT / "product-specs" / "index.md",
        DOCS_ROOT / "references" / "index.md",
    ]

    entries: list[IndexEntry] = []
    for index_path in index_paths:
        if index_path.exists():
            entries.extend(iter_index_entries(index_path))

    stale: list[IndexEntry] = []
    deprecated: list[IndexEntry] = []
    missing_meta: list[IndexEntry] = []

    for entry in entries:
        if entry.status == "deprecated":
            deprecated.append(entry)
        if entry.last_verified is None:
            missing_meta.append(entry)
        else:
            age_days = (today - entry.last_verified).days
            if age_days > args.stale_days:
                stale.append(entry)

    print("Doc Gardening Report")
    print(f"Generated: {today.isoformat()}")
    print("")

    if stale:
        print(f"Stale docs (> {args.stale_days} days):")
        for entry in stale:
            if entry.last_verified is None:
                print(f"- {entry.doc_path} (last verified unknown, owner {entry.owner})")
                continue
            print(
                f"- {entry.doc_path} (last verified {entry.last_verified.isoformat()}, owner {entry.owner})"
            )
    else:
        print(f"Stale docs (> {args.stale_days} days): none")
    print("")

    if deprecated:
        print("Deprecated docs:")
        for entry in deprecated:
            print(f"- {entry.doc_path} (owner {entry.owner})")
    else:
        print("Deprecated docs: none")
    print("")

    if missing_meta:
        print("Docs missing Last Verified metadata:")
        for entry in missing_meta:
            print(f"- {entry.doc_path} (index {entry.index_path})")
    else:
        print("Docs missing Last Verified metadata: none")


if __name__ == "__main__":
    main()
