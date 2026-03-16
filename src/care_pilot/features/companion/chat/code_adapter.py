"""
Execute Python code snippets in a sandboxed runtime.

This module wraps the E2B code interpreter to run agent-generated Python
snippets safely with a configurable timeout.
"""

from __future__ import annotations

import contextlib

from e2b_code_interpreter import Sandbox


class CodeAgent:
    """Runs arbitrary Python code in an E2B sandbox and returns the output."""

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def run(self, code: str, timeout: int = 60) -> str:
        """
        Execute *code* in E2B sandbox and return a human-readable result string.

        Uses Sandbox.create() (the non-deprecated API) and always kills the
        sandbox on completion.
        """
        if not self._api_key:
            raise OSError(
                "E2B_API_KEY is not configured. "
                "Set it in the API runtime configuration before calling CodeAgent."
            )
        # Ensure the SDK can read the key if it relies on env-based lookup.
        import os

        os.environ.setdefault("E2B_API_KEY", self._api_key)
        sandbox = None
        try:
            sandbox = Sandbox.create(timeout=timeout)
            execution = sandbox.run_code(code)

            stdout = "\n".join(execution.logs.stdout).strip()
            stderr = "\n".join(execution.logs.stderr).strip()

            if execution.error:
                return f"Error during execution:\n{execution.error.name}: {execution.error.value}"

            if stdout:
                return stdout

            # Fall back to last result value
            if execution.results:
                last = execution.results[-1]
                raw_value = getattr(last, "raw", None)
                return str(last.text or raw_value or "")

            if stderr:
                return f"Stderr:\n{stderr}"

            return "(no output)"

        except Exception as exc:
            return f"Sandbox error: {exc}"

        finally:
            if sandbox is not None:
                with contextlib.suppress(Exception):
                    sandbox.kill()
