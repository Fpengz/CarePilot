# Project Versioning Policy

This document defines the canonical project versioning and release workflow for the CarePilot repository.

## 1. Canonical Source of Truth

The canonical source of truth for the project version is the `version` field in **`pyproject.toml`** at the repository root.

### Mirrored Files
The following files must mirror the canonical version to ensure consistent builds:
- **`apps/web/package.json`**: For frontend package management and metadata.

- All other version references (documentation, metadata, build artifacts) must mirror this value.
- In-code version constants should be derived from the package metadata if possible, rather than manually hardcoded.

## 2. Semantic Versioning (SemVer)

CarePilot uses [Semantic Versioning 2.0.0](https://semver.org/).

Given a version number `MAJOR.MINOR.PATCH`:

- **MAJOR**: Breaking changes or major product milestones.
- **MINOR**: New backward-compatible features or meaningful milestones.
- **PATCH**: Bug fixes, internal hardening, or stabilization releases.

### Pre-1.0 Phase (Current)

The project remains in the **0.x.y** phase until the architecture and public contracts (API and Schema) are considered stable.

During the `0.x.y` phase:
- **MINOR** (0.X.y): Can include breaking changes. It signifies a significant architectural or feature milestone.
- **PATCH** (0.x.Y): Used for non-breaking improvements, fixes, and stabilization.

### Interpretation for this Repo

| Change Type | SemVer Category | Examples |
| :--- | :--- | :--- |
| **Breaking** | MAJOR (or MINOR in 0.x) | API contract change, breaking database migration, removal of supported features. |
| **Feature** | MINOR | New API endpoint, new agent capability, new dashboard chart, event-driven reaction. |
| **Fix / Internal** | PATCH | Bug fixes, performance tuning, infrastructure hardening, documentation updates. |

## 3. Release Cadence

We do **NOT** bump the version on every commit or every merged PR.

Bumps should occur for:
- Deployable milestones.
- Demo milestones (e.g., Singapore Innovation Challenge checkpoints).
- Intentional stabilization releases.
- Significant refactor completions.

## 4. Workflow

The versioning workflow is managed through the developer CLI:

1. **Status**: Check the current version.
   ```bash
   uv run python scripts/cli.py version status
   ```
2. **Bump**: Perform a bump (patch, minor, or major).
   ```bash
   uv run python scripts/cli.py version patch
   ```
3. **Commit & Tag**:
   - Commit the changes to `pyproject.toml` and `CHANGELOG.md`.
   - Create a git tag (e.g., `v0.2.1`).

## 5. Documentation Drift

To avoid drift, do not hardcode the version in documentation files. Use "the current version" or reference the project root if a specific version is not required for context.
