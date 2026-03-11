"""
routes/code_route.py
--------------------
Handles calculation / computation queries by:
  1. Using the LLM to translate the user's natural-language question into
     a short, self-contained Python script.
  2. Running that script inside a secure E2B sandbox via CodeAgent.
  3. Returning the sandbox output as enriched context for the final LLM reply.

Activated by: LLM classification in router.py (label "code").
"""
from __future__ import annotations

import os

from openai import OpenAI
from dotenv import load_dotenv

import re

from dietary_guardian.agent.chat.code import CodeAgent
from dietary_guardian.agent.chat.routes_base import BaseRoute, RouteResult

load_dotenv()

_CODE_GEN_PROMPT = (
    "You are a Python code generator.\n"
    "The user wants to perform a mathematical or numerical calculation.\n"
    "Write a SHORT, self-contained Python script (no imports unless strictly necessary, "
    "prefer built-ins) that computes the answer and prints it to stdout.\n"
    "Print a clear, labelled result — e.g. `print(f'Total calories: {result}')`. \n"
    "Do NOT add explanations, markdown fences, or comments. "
    "Reply with ONLY the raw Python code."
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

    def __init__(self) -> None:
        self._agent = CodeAgent()   # reads E2B_API_KEY from env
        self._client = OpenAI(
            api_key=os.environ.get("SEALION_API", ""),
            base_url="https://api.sea-lion.ai/v1",
        )
        self._model = os.environ.get(
            "REASONING_MODEL_ID", "aisingapore/Llama-SEA-LION-v3.5-70B-R"
        )

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
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _CODE_GEN_PROMPT},
                    {"role": "user",   "content": user_text},
                ],
                temperature=0,
                max_tokens=512,
                extra_body={
                    "chat_template_kwargs": {
                        "thinking_mode": "on"
                    }
                },
            )
            raw = resp.choices[0].message.content.strip()
            print(f"[CodeRoute] Raw LLM response:\n{raw}\n{'='*60}")
            code = self._extract_code(raw)
            print(f"[CodeRoute] Generated code:\n{code}")
            return code
        except Exception as exc:
            print(f"[CodeRoute] Code-gen error: {exc}")
            return f"print('Could not generate code: {exc}')"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def enrich(self, text: str) -> RouteResult:
        code = self._generate_code(text)
        output = self._agent.run(code)
        print(f"[CodeRoute] Sandbox output: {output!r}")

        context = "\n".join([
            SYSTEM_PROMPT,
            "",
            "## Calculation Result",
            f"```\n{output}\n```",
            "",
            f"## Python Code Used",
            f"```python\n{code}\n```",
        ])

        return RouteResult(
            route_name="code",
            context=context,
            metadata={"code": code, "output": output},
        )
