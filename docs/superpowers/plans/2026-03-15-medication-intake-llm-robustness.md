# Medication Intake LLM Robustness Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure medication intake LLM parsing reliably produces schema-valid output (even with chatty models) and frontend error logs surface actionable details.

**Architecture:** Add a defensive JSON extraction layer in the inference engine to recover structured outputs when output validation fails, and tighten medication parse prompts to demand the exact wrapper schema. Improve frontend logging by normalizing errors into plain objects so request errors never log as empty objects.

**Tech Stack:** Python (pydantic, pydantic_ai), TypeScript (Next.js frontend), Pytest

---

## Chunk 1: LLM Output Recovery + Prompt Hardening

### Task 1: Add failing tests for output recovery

**Files:**
- Modify: `/Users/zhoufuwang/Projects/care_pilots/tests/capabilities/test_inference_engine.py`
- Modify: `/Users/zhoufuwang/Projects/care_pilots/tests/features/test_medication_intake_parser.py`

- [ ] **Step 1: Write failing test for JSON recovery in inference engine**

```python
async def test_inference_engine_recovers_json_from_chatty_output(monkeypatch):
    class FakeAgent:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        async def run(self, prompt, event_stream_handler=None):
            if event_stream_handler:
                async def _emit():
                    from pydantic_ai.messages import PartEndEvent, TextPart
                    yield PartEndEvent(part=TextPart(content="Here is the JSON:\n```json\n{\"value\": \"ok\"}\n```"))
                await event_stream_handler(None, _emit())
            raise RuntimeError("Exceeded maximum retries (1) for output validation")

    monkeypatch.setattr("care_pilot.agent.runtime.inference_engine.Agent", FakeAgent)
    engine = InferenceEngine(provider="test")
    engine.provider = "openai"
    engine.strategy.provider_name = "openai"

    request = InferenceRequest(
        request_id="req1",
        modality=InferenceModality.TEXT,
        payload={"prompt": "hello"},
        output_schema=_DummyOutput,
        system_prompt="sys",
    )

    result = await engine.infer(request)
    assert result.structured_output.value == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /Users/zhoufuwang/Projects/care_pilots/tests/capabilities/test_inference_engine.py::test_inference_engine_recovers_json_from_chatty_output -v`

Expected: FAIL with "Exceeded maximum retries" or type error due to no recovery.

- [ ] **Step 3: Write failing test for list-wrapped medication outputs**

```python
@pytest.mark.anyio
async def test_parse_llm_output_list_wrapper_is_coerced() -> None:
    raw_output = MedicationParseOutput.model_validate(
        {
            "confidence_score": 0.9,
            "instructions": [],
            "warnings": [],
        }
    )
    result = await parse_medication_instructions(
        source=build_plain_text_source("Metoprolol 50mg"),
        today=date(2026, 3, 14),
        inference_engine=_FakeInferenceEngine(output=raw_output),
    )
    assert result.instructions == []
```

- [ ] **Step 4: Run test to verify it fails (if needed)**

Run: `pytest /Users/zhoufuwang/Projects/care_pilots/tests/features/test_medication_intake_parser.py::test_parse_llm_output_list_wrapper_is_coerced -v`

Expected: FAIL if parser rejects LLM wrapper or schema mismatch.

### Task 2: Implement JSON recovery in inference engine

**Files:**
- Modify: `/Users/zhoufuwang/Projects/care_pilots/src/care_pilot/agent/runtime/inference_engine.py`

- [ ] **Step 1: Implement JSON extraction helper**

```python
_JSON_BLOCK_RE = re.compile(r"```(?:json)?\\s*(?P<body>[\\s\\S]*?)\\s*```", re.IGNORECASE)

def _extract_json_candidates(text: str) -> list[str]:
    candidates = []
    for match in _JSON_BLOCK_RE.finditer(text):
        candidates.append(match.group("body"))
    if "{" in text and "}" in text:
        candidates.append(text[text.find("{"): text.rfind("}") + 1])
    if "[" in text and "]" in text:
        candidates.append(text[text.find("["): text.rfind("]") + 1])
    return [c.strip() for c in candidates if c.strip()]
```

- [ ] **Step 2: Add schema-aware coercion**

```python
def _coerce_output(output_schema: type[BaseModel], parsed: object) -> BaseModel | None:
    if isinstance(parsed, dict):
        return output_schema.model_validate(parsed)
    if isinstance(parsed, list) and "instructions" in output_schema.model_fields:
        payload = {"instructions": parsed, "confidence_score": 0.0, "warnings": ["Recovered from list output"]}
        return output_schema.model_validate(payload)
    return None
```

- [ ] **Step 3: Use recovery path when output validation retries exhaust**

```python
except Exception as exc:
    if raw_chunks:
        raw_text = "".join(raw_chunks)
        for candidate in _extract_json_candidates(raw_text):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            recovered = _coerce_output(request.output_schema, parsed)
            if recovered is not None:
                return InferenceResponse(...structured_output=recovered...)
    raise
```

- [ ] **Step 4: Run the tests**

Run: `pytest /Users/zhoufuwang/Projects/care_pilots/tests/capabilities/test_inference_engine.py::test_inference_engine_recovers_json_from_chatty_output -v`

Expected: PASS

### Task 3: Harden medication parse prompt

**Files:**
- Modify: `/Users/zhoufuwang/Projects/care_pilots/src/care_pilot/features/medications/intake/parser.py`

- [ ] **Step 1: Update system prompt with strict wrapper schema**

```python
Return JSON only. Output must be a JSON object with keys:
- instructions: array of instruction objects (see fields below)
- confidence_score: number 0-1
- warnings: array of strings

Do not include markdown fences or explanations.
```

- [ ] **Step 2: Add a short JSON example in the system prompt**

- [ ] **Step 3: Run parser tests**

Run: `pytest /Users/zhoufuwang/Projects/care_pilots/tests/features/test_medication_intake_parser.py -v`

Expected: PASS

## Chunk 2: Frontend Error Logging

### Task 4: Add failing test for request.error logs

**Files:**
- Modify: `/Users/zhoufuwang/Projects/care_pilots/apps/web/lib/console-safe.test.ts`
- Modify: `/Users/zhoufuwang/Projects/care_pilots/apps/web/lib/api/core.ts`

- [ ] **Step 1: Write failing test ensuring ApiRequestError is logged with details**

```ts
it("prints request.error payload with status and code", () => {
  const logs: unknown[] = [];
  const consoleLike = { info: jest.fn(), error: (msg: unknown, payload?: unknown) => logs.push({ msg, payload }) };
  const printer = getConsolePrinter(consoleLike, "request.error");
  printer("[frontend-api] request.error", { status: 422, error_code: "medications.intake_review_required" });
  expect(logs[0]).toMatchObject({ payload: { status: 422, error_code: "medications.intake_review_required" } });
});
```

- [ ] **Step 2: Run test to verify it fails (if needed)**

Run: `pnpm test apps/web/lib/console-safe.test.ts`

Expected: FAIL if payload is empty after normalization.

### Task 5: Normalize error payloads before logging

**Files:**
- Modify: `/Users/zhoufuwang/Projects/care_pilots/apps/web/lib/api/core.ts`

- [ ] **Step 1: Add helper to serialize errors into plain objects**

```ts
function serializeError(value: unknown): Record<string, unknown> {
  if (value instanceof Error) {
    return { name: value.name, message: value.message, stack: value.stack };
  }
  if (value && typeof value === "object") {
    return value as Record<string, unknown>;
  }
  return { value };
}
```

- [ ] **Step 2: Ensure logFrontendApi always logs non-empty payloads**

```ts
function logFrontendApi(event: string, payload: unknown) {
  if (!FRONTEND_API_LOG_ENABLED || typeof window === "undefined") return;
  const printer = getConsolePrinter(console, event);
  const normalized = payload && typeof payload === "object" ? payload : serializeError(payload);
  printer(`[frontend-api] ${event}`, redactSensitive(normalized as Record<string, unknown>));
}
```

- [ ] **Step 3: Run the web test**

Run: `pnpm test apps/web/lib/console-safe.test.ts`

Expected: PASS

## Chunk 3: Verification

### Task 6: Run focused validation

**Files:**
- None

- [ ] **Step 1: Backend tests**

Run: `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 uv run pytest /Users/zhoufuwang/Projects/care_pilots/tests/capabilities/test_inference_engine.py /Users/zhoufuwang/Projects/care_pilots/tests/features/test_medication_intake_parser.py -q`

Expected: PASS

- [ ] **Step 2: Web lint/typecheck (optional if test fails)**

Run: `pnpm web:lint`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add /Users/zhoufuwang/Projects/care_pilot/src/care_pilot/agent/runtime/inference_engine.py \
  /Users/zhoufuwang/Projects/care_pilot/src/care_pilot/features/medications/intake/parser.py \
  /Users/zhoufuwang/Projects/care_pilot/apps/web/lib/api/core.ts \
  /Users/zhoufuwang/Projects/care_pilot/tests/capabilities/test_inference_engine.py \
  /Users/zhoufuwang/Projects/care_pilot/tests/features/test_medication_intake_parser.py \
  /Users/zhoufuwang/Projects/care_pilot/apps/web/lib/console-safe.test.ts

git commit -m "fix: harden medication intake parsing and error logging"
```
