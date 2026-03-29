# Module Docstrings Design

## Goal
Add concise, PEP 257-compliant module docstrings to product code modules.
Docstrings should explain what the module does, why it exists, and how it is
typically used, without restating obvious details.

## Scope
- In scope: `src/` and `apps/` Python files.
- Out of scope: `tests/`, `scripts/`, and generated files.

## Standard
Use a minimal structure:
- One-line summary (imperative style).
- Blank line.
- Short purpose paragraph.

Include `Example:` and `Notes:` sections only when they add meaningful clarity.
Do not require an `Author:` line.

## Execution Notes
- Preserve existing docstrings that already describe the module well.
- Add new docstrings at the top of the file before imports (after any shebang
  or encoding declaration).
- Keep most docstrings to 5–15 lines.

## Risks
Low. Docstring-only changes should not affect behavior. Avoid editing
generated files that are overwritten by tooling.
