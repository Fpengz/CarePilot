# Backend Infrastructure & Performance Audit

This report highlights critical issues in the backend that impact frontend performance, scalability, and security.

## 1. Resource Contention & High Latency: In-Process Emotion Inference

The `InProcessEmotionRuntime` in `src/care_pilot/features/companion/emotion/runtime.py` loads and executes heavy HuggingFace models (Whisper, BERT-based text-emotion, etc.) directly within the FastAPI worker processes.

**Risks:**
- **RAM Bloat:** Each Uvicorn/Gunicorn worker loads its own copy of the models, potentially leading to OOM (Out of Memory) errors on standard servers.
- **Latency Spikes:** CPU-bound inference blocks the Python Global Interpreter Lock (GIL) or heavily taxes the CPU, slowing down all other API requests.
- **Scalability:** Horizontal scaling is constrained by the huge memory footprint of each instance.

**Recommendation:**
Offload emotion inference to a separate microservice (e.g., using TorchServe, Triton, or a simple dedicated FastAPI service) or use an asynchronous task queue like Celery/RabbitMQ for non-blocking processing.

## 2. Potential Security Risk: Code Agent for Simple Arithmetic

In `apps/api/carepilot_api/routers/dashboard.py`, the `dashboard_trend` endpoint uses a "code agent" to calculate simple percentage changes by generating and running dynamic Python code.

```python
    code = "import json\nprint(json.dumps({\n" + ",\n".join(metric_lines) + "\n}))"
    try:
        raw_output = deps.code_agent.run(code)
    except Exception as exc:
        # fallback to manual calculation
```

**Risks:**
- **RCE (Remote Code Execution):** If the sandbox in `deps.code_agent.run` is not perfectly isolated, this pattern is highly vulnerable.
- **Unnecessary Complexity:** Calculating a percentage change is a single line of standard Python. Using an LLM-driven or sandbox-based "code agent" for this is overkill and introduces a large attack surface.

**Recommendation:**
Remove the code agent dependency for deterministic calculations. Use standard Python logic directly.

## 3. Excessive API Complexity in Chat

The `ChatPage` logic is tightly coupled with a very complex `chat_stream` and `chat_audio` implementation in `apps/api/carepilot_api/routers/chat.py`. The routing logic handles streaming, emotion inference, meal detection, and memory retrieval all in one place.

**Risks:**
- **Maintenance:** Changing the orchestration logic requires touching the API router directly.
- **Tight Coupling:** The frontend has to manually manage complex SSE (Server-Sent Events) payloads and error states.

**Recommendation:**
Abstract the chat orchestration logic into a dedicated service layer and ensure the API router only handles request/response lifecycle.
