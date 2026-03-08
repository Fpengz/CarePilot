# Implementation Plan: GitHub Copilot OAuth for Local and CI Testing

## Problem Summary

This repository already supports multiple LLM providers through a shared configuration and
provider factory:

- `src/dietary_guardian/config/settings.py`
- `src/dietary_guardian/agents/provider_factory.py`

Today the supported providers are `gemini`, `openai`, `ollama`, `vllm`, and `test`.
There is no GitHub OAuth flow and no GitHub Copilot provider yet.

The requested outcome is to make the system usable with **GitHub Copilot tokens for testing**,
similar to tools such as OpenClaw, while fitting cleanly into the existing architecture.

The practical approach is to add **`copilot` as a first-class LLM provider** and treat
GitHub Copilot as an **OpenAI-compatible backend** that requires one extra authentication
step before normal chat completions can be used.

---

## High-Level Goal

Enable developers and CI to do this:

```bash
export LLM_PROVIDER=copilot
export GITHUB_TOKEN=...
uv run pytest -q
```

And for local developer login:

```bash
uv run python scripts/copilot_login.py
export LLM_PROVIDER=copilot
uv run pytest -m copilot -q
```

---

## Current Codebase Context

### What already exists

1. **Provider selection is centralized**
   - `Settings.llm_provider` already controls runtime provider choice.
   - `LLMFactory.get_model()` already builds models for Gemini, OpenAI, Ollama, vLLM, and test.

2. **OpenAI-compatible integration path already exists**
   - The code already uses `AsyncOpenAI`.
   - The code already wraps OpenAI-compatible clients with `OpenAIProvider`.
   - The code already returns `OpenAIChatModel` instances for compatible backends.

3. **Environment-driven configuration already exists**
   - `.env.example` documents provider configuration.
   - `Settings.normalize_and_validate()` already performs fail-fast validation.

4. **Testing infrastructure already exists**
   - `pytest` is configured in `pyproject.toml`.
   - There is already a strong test suite and existing LLM-related tests.

### Why this matters

Because Copilot speaks an OpenAI-style API, we do **not** need a brand-new inference stack.
We only need to:

- add new settings,
- add token acquisition and refresh logic,
- wire that token into the existing OpenAI-compatible provider path,
- add focused tests and usage documentation.

---

## How GitHub Copilot Authentication Works

GitHub Copilot testing is not done by using the GitHub token directly against the model API.
Instead, there is a two-step flow:

### Step 1: Obtain a GitHub credential

Choose one of:

- **PAT** (`GITHUB_TOKEN`) for CI or manual local testing
- **Device Flow OAuth** for local developer login

### Step 2: Exchange the GitHub credential for a short-lived Copilot session token

Request:

```http
GET https://api.github.com/copilot_internal/v2/token
Authorization: token <GITHUB_TOKEN>
editor-version: vscode/1.85.0
editor-plugin-version: copilot/1.138.0
user-agent: GithubCopilot/1.138.0
```

Typical response:

```json
{
  "token": "tid=...",
  "expires_at": 1700000000,
  "refresh_in": 1500
}
```

### Step 3: Use the short-lived token against the Copilot API

```http
POST https://api.githubcopilot.com/chat/completions
Authorization: Bearer tid=...
openai-intent: conversation-panel
```

### Operational implication

The Copilot session token expires quickly, so the implementation needs a small token manager
that caches the token and refreshes it before expiry.

---

## Recommended Implementation Strategy

### Recommendation

Support **both** authentication entry points:

1. **PAT path** for CI and scripted testing
2. **Device Flow path** for local development

This gives the best developer experience:

- **local dev:** run login once, then test
- **CI:** inject `GITHUB_TOKEN` as a secret

---

## Planned Changes

## 1. Add Copilot settings

**File:** `src/dietary_guardian/config/settings.py`

### Add provider literal

Extend:

```python
llm_provider: Literal["gemini", "openai", "ollama", "vllm", "test"]
```

to:

```python
llm_provider: Literal["gemini", "openai", "ollama", "vllm", "copilot", "test"]
```

### Add fields

Add:

```python
github_token: str | None = None
copilot_model: str = "gpt-4o"
copilot_base_url: str = "https://api.githubcopilot.com"
```

### Add validation

Inside `normalize_and_validate()`:

- if `llm_provider == "copilot"` and `github_token` is missing,
  try a saved local token file
- if nothing is available, raise a clear `ValueError`

Suggested validation message:

```python
raise ValueError(
    "Copilot provider selected but GITHUB_TOKEN is not set. "
    "Run `uv run python scripts/copilot_login.py` for local device login, "
    "or set GITHUB_TOKEN in your environment."
)
```

### Why this belongs here

This project already treats configuration validation as a startup contract.
Copilot should follow the same fail-fast behavior as Gemini and OpenAI.

---

## 2. Create a dedicated Copilot auth module

**New file:** `src/dietary_guardian/agents/copilot_auth.py`

### Purpose

Keep all GitHub and Copilot authentication logic isolated in one place.

### Responsibilities

1. Exchange a GitHub token for a Copilot session token
2. Cache the session token in memory
3. Refresh before expiry
4. Optionally load a saved local GitHub token from disk
5. Support GitHub Device Flow for local login

### Proposed shape

```python
class CopilotAuthError(Exception):
    ...


@dataclass
class _CopilotSession:
    token: str
    expires_at: float


class CopilotTokenManager:
    def __init__(self, github_token: str) -> None:
        ...

    async def get_token(self) -> str:
        ...

    async def _exchange(self) -> _CopilotSession:
        ...


def load_saved_github_token() -> str | None:
    ...


async def run_device_flow() -> str:
    ...
```

### Implementation notes

- Do **not** make this module depend on `Settings`
- Pass `github_token` in directly
- Use explicit exceptions, not silent fallback behavior
- Keep it unit-testable without app startup

---

## 3. Extend the provider factory

**File:** `src/dietary_guardian/agents/provider_factory.py`

### Add enum value

Add:

```python
COPILOT = "copilot"
```

to `ModelProvider`.

### Add Copilot branch to `LLMFactory.get_model()`

New branch should:

1. resolve `github_token`
2. obtain a short-lived Copilot session token via `CopilotTokenManager`
3. build an OpenAI-compatible client using:
   - `base_url = settings.copilot_base_url`
   - `api_key = <copilot session token>`
4. set required header:

```python
{"openai-intent": "conversation-panel"}
```

5. return:

```python
OpenAIChatModel(settings.copilot_model, provider=...)
```

### Important design point

Do not fork the whole provider implementation.
Reuse the existing OpenAI-compatible path as much as possible.

If needed, extend `_build_openai_provider(...)` to accept optional extra headers.

---

## 4. Add a local login helper script

**New file:** `scripts/copilot_login.py`

### Purpose

Provide a simple one-time login flow for local developers.

### Behavior

1. start GitHub Device Flow
2. print verification URL and device code
3. poll until the user authorizes
4. save the resulting GitHub token to a local file
5. print next-step instructions

Suggested save path:

```text
~/.copilot/copilot_github_token
```

Suggested output:

```text
Saved GitHub Copilot token to ~/.copilot/copilot_github_token
Set LLM_PROVIDER=copilot and rerun your app or tests.
```

### File permissions

Save with restrictive permissions such as `0o600`.

---

## 5. Document environment variables

**File:** `.env.example`

Add a Copilot section:

```dotenv
# GitHub Copilot provider
# Option A: set GITHUB_TOKEN manually
# Option B: run `uv run python scripts/copilot_login.py`
GITHUB_TOKEN=
COPILOT_MODEL=gpt-4o
COPILOT_BASE_URL=https://api.githubcopilot.com
```

### Why this matters

This repository already uses `.env.example` as the canonical configuration guide.
Copilot support should be visible there immediately.

---

## 6. Add test fixtures for live Copilot testing

**New file:** `tests/fixtures/copilot_fixtures.py`

### Goals

- allow live Copilot-backed tests when credentials exist
- skip cleanly when credentials do not exist
- avoid breaking the default test suite

### Behavior

Provide:

- a fixture that returns a Copilot-backed model
- a fixture that returns the raw GitHub token
- automatic `pytest.skip(...)` when no token is available

This keeps live Copilot tests opt-in.

---

## 7. Add unit tests for auth and refresh logic

**New file:** `tests/test_copilot_auth.py`

### Required test coverage

1. request is built with correct headers
2. response parsing extracts token and expiry correctly
3. repeated `get_token()` calls use the cache
4. token refresh happens when near expiry
5. 401/403 produce a clear `CopilotAuthError`
6. network failures produce a clear `CopilotAuthError`
7. saved token loader returns `None` when missing
8. saved token loader reads and strips file content correctly

### Test style

- mock external HTTP
- no real network in unit tests
- keep live tests separate and clearly marked

---

## Testing and Verification Plan

## Baseline checks

Before shipping, run the existing quality gates:

```bash
uv run ruff check .
uv run ty check . --extra-search-path src --output-format concise
uv run pytest -q
```

## Live Copilot checks

With credentials available:

```bash
export LLM_PROVIDER=copilot
export GITHUB_TOKEN=...
uv run pytest -m copilot -q
```

## Expected validation outcomes

- missing `GITHUB_TOKEN` with `LLM_PROVIDER=copilot` should fail fast
- non-Copilot providers should keep working unchanged
- default test suite should remain green without requiring Copilot credentials

---

## CI Guidance

For CI, prefer the PAT path or a repository/org secret dedicated to Copilot testing.

Example:

```yaml
- name: Run Copilot integration tests
  env:
    LLM_PROVIDER: copilot
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: uv run pytest -m copilot -q
```

If the built-in GitHub Actions token does not have Copilot access in the target environment,
replace it with a dedicated PAT secret.

---

## Execution Order

1. **Settings**
   - add provider literal
   - add fields
   - add validation

2. **Copilot auth module**
   - exchange endpoint
   - cache and refresh logic
   - saved token loader
   - device flow helper

3. **Provider factory**
   - add enum value
   - add Copilot model branch
   - add any needed extra-header support

4. **Developer usability**
   - add `scripts/copilot_login.py`
   - update `.env.example`

5. **Testing**
   - add fixtures
   - add unit tests
   - optionally add live Copilot marker

6. **Verification**
   - run lint
   - run type checks
   - run existing tests
   - run Copilot-specific tests when credentials are available

---

## Current Progress Snapshot

Based on the tracked todos in this session:

- `settings-copilot-fields` — done
- `copilot-auth-module` — done
- `copilot-login-script` — done
- `env-example-copilot` — done
- `factory-copilot-branch` — in progress
- `test-fixtures-copilot` — in progress
- `unit-tests-copilot` — in progress

### Immediate next steps

1. finish wiring the `copilot` branch in `LLMFactory`
2. add/finish live test fixtures
3. add/finish unit tests for token exchange and refresh behavior
4. run full repo validation

---

## Success Criteria

This plan is complete when all of the following are true:

1. `LLM_PROVIDER=copilot` is a supported runtime option
2. the system can authenticate using either:
   - `GITHUB_TOKEN`, or
   - local device-flow login state
3. the provider uses the existing OpenAI-compatible model path
4. tests do not require Copilot by default
5. live Copilot tests are easy to run when credentials are present
6. the repository still passes lint, typing, and test validation
