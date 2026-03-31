from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "docs"

REQUIRED_FILES = [
    DOCS_ROOT / "README.md",
    DOCS_ROOT / "DESIGN.md",
    DOCS_ROOT / "FRONTEND.md",
    DOCS_ROOT / "PLANS.md",
    DOCS_ROOT / "PRODUCT_SENSE.md",
    DOCS_ROOT / "QUALITY_SCORE.md",
    DOCS_ROOT / "RELIABILITY.md",
    DOCS_ROOT / "SECURITY.md",
    DOCS_ROOT / "design-docs" / "index.md",
    DOCS_ROOT / "exec-plans" / "index.md",
    DOCS_ROOT / "product-specs" / "index.md",
    DOCS_ROOT / "references" / "index.md",
    DOCS_ROOT / "generated" / "db-schema.md",
]

REQUIRED_DIRS = [
    DOCS_ROOT / "design-docs",
    DOCS_ROOT / "exec-plans" / "active",
    DOCS_ROOT / "exec-plans" / "in-progress",
    DOCS_ROOT / "exec-plans" / "completed",
    DOCS_ROOT / "exec-plans" / "templates",
    DOCS_ROOT / "generated",
    DOCS_ROOT / "product-specs",
    DOCS_ROOT / "references",
]

ALLOWED_STATUS = {
    "draft",
    "active",
    "verified",
    "deprecated",
    "completed",
    "in-progress",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class IndexEntry:
    doc_path: Path
    status: str
    last_verified: str
    owner: str
    index_path: Path


def iter_index_entries(index_path: Path) -> Iterable[IndexEntry]:
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
        yield IndexEntry(
            doc_path=Path(doc_value),
            status=status,
            last_verified=last_verified,
            owner=owner,
            index_path=index_path,
        )


def validate_required_paths(errors: list[str]) -> None:
    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"Missing required file: {path}")
    for path in REQUIRED_DIRS:
        if not path.exists():
            errors.append(f"Missing required directory: {path}")


def validate_index(index_path: Path, category_root: Path, errors: list[str]) -> None:
    entries = list(iter_index_entries(index_path))
    seen_docs: set[Path] = set()
    for entry in entries:
        doc_path = (REPO_ROOT / entry.doc_path).resolve()
        seen_docs.add(entry.doc_path)
        if entry.status not in ALLOWED_STATUS:
            errors.append(
                f"Invalid status '{entry.status}' in {index_path} for {entry.doc_path}"
            )
        if not DATE_RE.match(entry.last_verified):
            errors.append(
                f"Invalid Last Verified '{entry.last_verified}' in {index_path} for {entry.doc_path}"
            )
        if not doc_path.exists():
            errors.append(f"Indexed doc missing on disk: {entry.doc_path}")
        if category_root not in doc_path.parents and doc_path != category_root:
            errors.append(
                f"Indexed doc is outside category {category_root}: {entry.doc_path}"
            )

    for doc_file in category_root.rglob("*.md"):
        if doc_file.name == "index.md":
            continue
        rel_path = doc_file.relative_to(REPO_ROOT)
        if rel_path not in seen_docs:
            errors.append(f"Doc not indexed in {index_path}: {rel_path}")


def main() -> None:
    errors: list[str] = []
    validate_required_paths(errors)

    validate_index(DOCS_ROOT / "design-docs" / "index.md", DOCS_ROOT / "design-docs", errors)
    validate_index(DOCS_ROOT / "exec-plans" / "index.md", DOCS_ROOT / "exec-plans", errors)
    validate_index(DOCS_ROOT / "product-specs" / "index.md", DOCS_ROOT / "product-specs", errors)
    validate_index(DOCS_ROOT / "references" / "index.md", DOCS_ROOT / "references", errors)

    if errors:
        print("Knowledge base validation failed:")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    print("Knowledge base validation passed.")


if __name__ == "__main__":
    main()
