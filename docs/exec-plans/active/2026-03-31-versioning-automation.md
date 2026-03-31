# Execution Plan: Versioning and Changelog Automation

> **Goal**: Implement a clean, durable versioning and changelog workflow integrated into the developer CLI.

## 1. Audit Summary (Completed 2026-03-31)

- **Version source**: `pyproject.toml` (currently `0.1.0`).
- **Conflict check**: `.changeset` exists but is redundant for this project's scope.
- **Canonical target**: `pyproject.toml` is the source of truth.
- **CLI structure**: `scripts/cli.py` is modularized via `typer`.

## 2. Tasks

### Task 1: Initialize CHANGELOG.md
- [ ] Create a root `CHANGELOG.md` following the [Keep a Changelog](https://keepachangelog.com/) format.
- [ ] Add an initial entry for `0.1.0`.

### Task 2: Implement CLI `version` Command
- [ ] Create `scripts/cli/commands/version.py`.
- [ ] Implement `version status`:
  - Read from `pyproject.toml`.
  - Display clearly.
- [ ] Implement `version [patch|minor|major]`:
  - Validate current version format.
  - Increment version using `semver` or simple logic.
  - Update `pyproject.toml` using a structured TOML parser (e.g., `tomlkit` or `tomli`/`tomli-w`).
  - Print the change.
- [ ] Implement `version set X.Y.Z`:
  - Manual override for specific versions.

### Task 3: Integrate into `scripts/cli.py`
- [ ] Register `version_app` in `scripts/cli.py`.
- [ ] Update `help` command documentation.

### Task 4: Cleanup
- [ ] Remove `.changeset/` directory and its configuration.
- [ ] Remove any other stale versioning files or scripts.

### Task 5: Documentation Update
- [ ] Update `docs/references/developer-guide.md` to reference the new policy and CLI commands.
- [ ] Update indices in `docs/design-docs/index.md` and `docs/exec-plans/index.md`.

## 3. Validation

- [ ] `uv run python scripts/cli.py version status` matches `pyproject.toml`.
- [ ] `uv run python scripts/cli.py version patch` updates `pyproject.toml` correctly.
- [ ] Malformed versions fail loudly.
- [ ] `pnpm web:build` and backend tests still pass.
