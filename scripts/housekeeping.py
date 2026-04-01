#!/usr/bin/env python3
"""
Overnight Housekeeping Script for CarePilot.

Performs:
1. Cleanup of stale 'in-progress' plans (older than 7 days).
2. Purge of temporary artifacts in data/runtime/ (older than 3 days).
3. Validation of documentation index integrity.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
REPO_ROOT = Path(__file__).parent.parent.resolve()
EXEC_PLANS_DIR = REPO_ROOT / "docs/exec-plans"
DATA_RUNTIME_DIR = REPO_ROOT / "data/runtime"
STALE_PLAN_DAYS = 7
STALE_ARTIFACT_DAYS = 3

def promote_stale_plans():
    """Promote 'in-progress' plans older than 7 days by renaming them to today's date."""
    in_progress_dir = EXEC_PLANS_DIR / "in-progress"

    if not in_progress_dir.exists():
        print(f"Directory not found: {in_progress_dir}")
        return

    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    cutoff = now - timedelta(days=STALE_PLAN_DAYS)

    count = 0
    for plan_file in in_progress_dir.glob("*.md"):
        # Check file modification time
        mtime = datetime.fromtimestamp(plan_file.stat().st_mtime)
        if mtime < cutoff:
            # Extract slug: YYYY-MM-DD-slug.md -> slug.md
            parts = plan_file.name.split("-", 3)
            if len(parts) >= 4:
                slug = parts[3]
                new_name = f"{today_str}-{slug}"
                new_path = in_progress_dir / new_name

                # Skip if already promoted to today's date (fixes conflict loop)
                if new_path == plan_file:
                    continue

                if new_path.exists():
                    print(f"Conflict: {new_name} already exists. Skipping promotion for {plan_file.name}")
                    continue

                print(f"Promoting stale plan: {plan_file.name} -> {new_name} (last modified {mtime})")
                plan_file.rename(new_path)
                count += 1
            else:
                print(f"Plan filename does not follow YYYY-MM-DD-slug format: {plan_file.name}")

    print(f"Total stale plans promoted to {today_str}: {count}")

def purge_temporary_artifacts():
    """Delete files in data/runtime/ older than 3 days."""
    if not DATA_RUNTIME_DIR.exists():
        print(f"Directory not found: {DATA_RUNTIME_DIR}")
        return

    now = datetime.now()
    cutoff = now - timedelta(days=STALE_ARTIFACT_DAYS)

    count = 0
    for artifact in DATA_RUNTIME_DIR.glob("*"):
        if artifact.is_file() and not artifact.name.startswith("."):
            mtime = datetime.fromtimestamp(artifact.stat().st_mtime)
            if mtime < cutoff:
                print(f"Purging stale artifact: {artifact.name} (last modified {mtime})")
                artifact.unlink()
                count += 1

    print(f"Total stale artifacts purged: {count}")

def validate_doc_indexes():
    """Verify that all Markdown files in docs/ are referenced in docs/README.md or sub-indexes."""
    docs_root = REPO_ROOT / "docs"
    readme_path = docs_root / "README.md"

    if not readme_path.exists():
        print("docs/README.md not found.")
        return

    readme_content = readme_path.read_text(encoding="utf-8")

    # Identify sub-indexes from docs/README.md
    # Look for patterns like `docs/design-docs/index.md`
    sub_index_pattern = r"`(docs/[^`]+index\.md)`"
    sub_indexes = re.findall(sub_index_pattern, readme_content)

    index_contents = {readme_path: readme_content}
    for sub_index in sub_indexes:
        sub_path = REPO_ROOT / sub_index
        if sub_path.exists():
            index_contents[sub_path] = sub_path.read_text(encoding="utf-8")

    # Find all .md files in docs/
    all_md_files = list(docs_root.rglob("*.md"))
    missing = []

    for md_file in all_md_files:
        rel_path = md_file.relative_to(REPO_ROOT)
        rel_path_str = str(rel_path)

        # Skip the root README.md itself
        if md_file == readme_path:
            continue

        is_indexed = False
        for content in index_contents.values():
            # Check for exact path or filename reference
            if rel_path_str in content or f"`{md_file.name}`" in content:
                is_indexed = True
                break

        if not is_indexed:
            missing.append(rel_path_str)

    if missing:
        print("Doc index integrity check: FAILED")
        for doc in missing:
            print(f"  Missing from index: {doc}")
    else:
        print("Validating doc index integrity... OK")

def main():
    print(f"--- CarePilot Housekeeping started at {datetime.now()} ---")

    try:
        promote_stale_plans()
        purge_temporary_artifacts()
        validate_doc_indexes()
    except Exception as e:
        print(f"Error during housekeeping: {e}")
        exit(1)

    print("--- CarePilot Housekeeping completed successfully ---")

if __name__ == "__main__":
    main()
