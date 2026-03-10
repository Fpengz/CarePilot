#!/usr/bin/env python3
"""Validate pull request bodies against the repository's current review contract.

The policy enforced here matches the present multi-agent architecture workflow:
PRs must describe scope, ownership, validation, and rollback risk in a form that
reviewers can audit quickly. GitHub Actions calls this script in CI to reject
changes that do not include the required headings and checked validation items.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REQUIRED_HEADINGS = [
    "Summary",
    "Task Contract",
    "Scope",
    "Affected Layers",
    "Files and Ownership",
    "Validation",
    "Risk and Rollback",
    "Multi-Agent Checklist",
]

REQUIRED_CHECKBOX_TOKENS = [
    "`backend_checks_completed`",
    "`web_checks_completed`",
    "`comprehensive_checks_completed`",
    "`risk_rollback_documented`",
]


def fail(message: str) -> int:
    print(f"PR policy check failed: {message}")
    return 1


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path:
        return fail("GITHUB_EVENT_PATH is not set")

    path = Path(event_path)
    if not path.is_file():
        return fail(f"event payload not found at {event_path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return fail("pull_request payload is missing")

    body = pull_request.get("body") or ""
    if not body.strip():
        return fail("PR body is empty; fill the PR template")

    missing_headings: list[str] = []
    for heading in REQUIRED_HEADINGS:
        pattern = rf"^##\s+{re.escape(heading)}\s*$"
        if re.search(pattern, body, flags=re.MULTILINE) is None:
            missing_headings.append(heading)

    if missing_headings:
        return fail(f"missing required headings: {', '.join(missing_headings)}")

    missing_checkboxes: list[str] = []
    for token in REQUIRED_CHECKBOX_TOKENS:
        pattern = rf"^-\s*\[x\]\s*{re.escape(token)}\s*$"
        if re.search(pattern, body, flags=re.MULTILINE) is None:
            missing_checkboxes.append(token)

    if missing_checkboxes:
        return fail(
            "required checklist items must be checked: " + ", ".join(missing_checkboxes)
        )

    print("PR policy check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
