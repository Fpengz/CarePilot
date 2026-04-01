# Versioning Automation Cleanup and Documentation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up redundant versioning artifacts and update the developer guide with the new CLI versioning commands.

**Architecture:** Remove the deprecated `.changeset` directory and update `docs/references/developer-guide.md` to establish `pyproject.toml` and the CLI as the source of truth for versioning.

**Tech Stack:** Bash, Markdown, Python (Typer).

---

## Chunk 1: Artifact Cleanup

### Task 1: Remove redundant `.changeset` directory

**Files:**
- Delete: `.changeset/`

- [ ] **Step 1: Verify `.changeset` directory exists**

Run: `ls -d .changeset`
Expected: `.changeset`

- [ ] **Step 2: Remove the directory**

Run: `rm -rf .changeset`

- [ ] **Step 3: Verify removal**

Run: `ls -d .changeset`
Expected: `ls: .changeset: No such file or directory`

- [ ] **Step 4: Commit cleanup**

```bash
git add .
git commit -m "chore: remove redundant .changeset directory"
```

---

## Chunk 2: Documentation Update

### Task 2: Update Developer Guide with Versioning Commands

**Files:**
- Modify: `docs/references/developer-guide.md`

- [ ] **Step 1: Locate the "Project Versioning" section**

- [ ] **Step 2: Add detailed CLI command documentation**

Update the section to include:
```markdown
### Project Versioning
CarePilot follows Semantic Versioning (SemVer). The `pyproject.toml` file is the source of truth for the project version.

Use the CarePilot CLI to manage versions:

#### Check current version
```bash
uv run python scripts/cli.py version status
```

#### Increment version
```bash
uv run python scripts/cli.py version patch
uv run python scripts/cli.py version minor
uv run python scripts/cli.py version major
```

#### Set specific version
```bash
uv run python scripts/cli.py version set 1.2.3
```
```

- [ ] **Step 3: Verify documentation rendering** (Visual check of Markdown)

- [ ] **Step 4: Commit documentation changes**

```bash
git add docs/references/developer-guide.md
git commit -m "docs: document CLI versioning commands in developer guide"
```

---

## Chunk 3: Final Verification

### Task 3: Verify CLI and pre-commit hooks

**Files:**
- N/A

- [ ] **Step 1: Run version status to ensure CLI still works**

Run: `uv run python scripts/cli.py version status`
Expected: `Current version: 0.1.0` (or current version)

- [ ] **Step 2: Run pre-commit hooks**

Run: `pre-commit run --all-files`
Expected: All passes (or fixes applied)

- [ ] **Step 3: Push and Open PR**
