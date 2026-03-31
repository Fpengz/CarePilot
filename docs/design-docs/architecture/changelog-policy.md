# Changelog Policy

CarePilot maintains a human-readable, curated changelog to track significant changes across the repository.

## 1. File Location

The canonical changelog is located at **`CHANGELOG.md`** in the repository root.

- Historical logs for major refactors may also be archived in `docs/references/change_log/`.
- The root `CHANGELOG.md` is the primary record for project version releases.

## 2. Structure

The changelog follows the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

Each release entry should include:
- Version number (linked to the git tag/diff).
- Release date (YYYY-MM-DD).
- Grouped changes:
  - **Added**: New features.
  - **Changed**: Changes in existing functionality.
  - **Deprecated**: Soon-to-be-removed features.
  - **Removed**: Removed features.
  - **Fixed**: Bug fixes.
  - **Security**: Security vulnerability fixes.
  - **Internal**: Refactors, infrastructure hardening, or developer experience improvements.

## 3. Workflow

Entries should be added to the `[Unreleased]` section as work is completed.

When a version is bumped via `scripts/cli.py version [patch|minor|major]`:
1. The `[Unreleased]` section is converted to the new version entry.
2. The current date is added.
3. A new empty `[Unreleased]` section is created at the top.

## 4. Verbosity

- **Be concise**: Focus on what changed and why it matters to the product or developers.
- **Avoid "Commit Soup"**: Do not list every single commit. Group related work into a single logical bullet point.
- **Link Issues**: Reference GitHub issues or PRs where applicable (e.g., `#123`).

## 5. Decision on Tooling

The project has transitioned away from automated tools like `.changeset` to a **manual, curated workflow** integrated with the developer CLI. This ensures that the changelog remains high-quality and free of low-signal automated entries.
