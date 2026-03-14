"""
Handle computation queries for the chat router.

This module translates user math requests into Python, executes them in a
sandbox, and returns the result as enrichment for the final response.
"""
from __future__ import annotations

import asyncio
import re
import uuid

from dietary_guardian.features.companion.chat.code_adapter import CodeAgent
from dietary_guardian.features.companion.chat.routes.base import BaseRoute, RouteResult
from dietary_guardian.agent.chat.schemas import ChatGeneratedCode, ChatRouteLabel
from dietary_guardian.agent.runtime.inference_engine import InferenceEngine
from dietary_guardian.agent.runtime.inference_types import InferenceModality, InferenceRequest
from dietary_guardian.platform.observability import get_logger

_CODE_GEN_PROMPT = (
    "You are a Python code generator.\n"
    "The user wants to perform a mathematical or numerical calculation.\n"
    "Write a SHORT, self-contained Python script (no imports unless strictly necessary, "
    "prefer built-ins) that computes the answer and prints it to stdout.\n"
    "Print a clear, labelled result — e.g. `print(f'Total calories: {result}')`. \n"
    "Do NOT add explanations, markdown fences, or comments. "
    "Return the generated script in the `code` field only."
)

SYSTEM_PROMPT = (
    "You are a helpful health assistant for patients in Singapore.\n"
    "A Python script was automatically generated and run to answer the user's "
    "calculation question. The result is shown below.\n"
    "Interpret the result conversationally, relate it back to the user's question, "
    "and add any relevant health context (e.g. daily calorie limits, medication doses)."
)


class CodeRoute(BaseRoute):
    """Translates a math/calculation query to Python, runs it in E2B, returns context."""

    def __init__(self, *, agent: CodeAgent, inference_engine: InferenceEngine) -> None:
        self._agent = agent
        self._engine = inference_engine
        self._logger = get_logger(__name__)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_code(raw: str) -> str:
        """
        Extract only the Python code from the model's response.

        The reasoning model (thinking_mode=on) prepends prose before the code.
        Strategy:
          1. Prefer the last ```python ... ``` or ``` ... ``` fenced block.
          2. Fall back to trailing lines that look like Python code.
        """
        # 1. Look for fenced code blocks (take the LAST one in case of multiple)
        fenced = re.findall(r"```(?:python)?\n(.*?)```", raw, re.DOTALL)
        if fenced:
            return fenced[-1].strip()

        # 2. Scan from the bottom for consecutive Python-looking lines
        _PYTHON_LINE = re.compile(
            r"^(print|result|import|from|if|for|while|def|class|return|[a-zA-Z_]\w*\s*[=(\[|#])"
        )
        lines = raw.splitlines()
        code_lines: list[str] = []
        for line in reversed(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if _PYTHON_LINE.match(stripped):
                code_lines.append(line)
            elif code_lines:  # first non-code line after code started — stop
                break
        if code_lines:
            return "\n".join(reversed(code_lines)).strip()

        # 3. Nothing matched — return the raw response as-is and hope for the best
        return raw.strip()

    def _generate_code(self, user_text: str) -> str:
        """Ask the LLM to produce a Python snippet for the user's calculation."""
        try:
            request = InferenceRequest(
                request_id=str(uuid.uuid4()),
                user_id=None,
                modality=InferenceModality.TEXT,
                payload={"prompt": user_text},
                output_schema=ChatGeneratedCode,
                system_prompt=_CODE_GEN_PROMPT,
            )
            response = asyncio.run(self._engine.infer(request))
            raw = response.structured_output.code.strip()
            code = self._extract_code(raw)
            self._logger.info("chat_code_generated length=%s", len(code))
            return code
        except Exception as exc:  # noqa: BLE001
            self._logger.warning("chat_code_gen_failed error=%s", exc)
            return f"print('Could not generate code: {exc}')"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def enrich(self, text: str) -> RouteResult:
        code = self._generate_code(text)
        output = self._agent.run(code)
        self._logger.info("chat_code_sandbox_output length=%s", len(output))

        context = "\n".join([
            SYSTEM_PROMPT,
            "",
            "## Calculation Result",
            f"```\n{output}\n```",
            "",
            "## Python Code Used",
            f"```python\n{code}\n```",
        ])

        return RouteResult(
            route_name=ChatRouteLabel.CODE,
            context=context,
            metadata={"code": code, "output": output},
        )
