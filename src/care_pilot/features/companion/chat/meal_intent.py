"""
Detect meal logging intent for chat messages.

This module provides heuristic-first intent detection with optional
LLM fallback for ambiguous messages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Literal, Tuple, cast

from pydantic import BaseModel, Field

from care_pilot.agent.runtime.inference_engine import InferenceEngine
from care_pilot.agent.runtime.inference_types import (
    InferenceModality,
    InferenceRequest,
)

_MEAL_PREFIX_RE = re.compile(
    r"^(?:log\s+meal|meal)\s*:\s*(.+)$", re.IGNORECASE
)
_QUESTION_RE = re.compile(
    r"\b(can|should|is it ok to|is it okay to)\b", re.IGNORECASE
)
_MEAL_TIME_RE = re.compile(
    r"\b(breakfast|lunch|dinner|supper)\b", re.IGNORECASE
)
_ATE_RE = re.compile(r"\b(i|we)\s+(ate|had|have)\s+(.+)$", re.IGNORECASE)
_FOR_MEAL_RE = re.compile(
    r"\bfor\s+(breakfast|lunch|dinner|supper)\b.*$", re.IGNORECASE
)
_MEAL_LABEL_RE = re.compile(
    r"^\s*(breakfast|lunch|dinner|supper)\s*(?:was|is|:)?\s*(.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MealLogIntentResult:
    intent: bool
    meal_text: str | None
    confidence: float
    reason: str
    source: Literal["heuristic", "llm"]


def meal_proposal_cache_key(
    *, user_id: str, session_id: str, proposal_id: str
) -> str:
    return f"chat:meal:proposal:{user_id}:{session_id}:{proposal_id}"


def _strip_meal_suffix(text: str) -> str:
    cleaned = _FOR_MEAL_RE.sub("", text).strip()
    return cleaned.rstrip(".?!")


def _extract_explicit_command(message: str) -> str | None:
    cleaned = message.strip()
    if not cleaned:
        return None
    if cleaned.lower().startswith("[meal]"):
        remainder = cleaned[6:].strip()
        return remainder or None
    match = _MEAL_PREFIX_RE.match(cleaned)
    if match:
        candidate = match.group(1).strip()
        return candidate or None
    return None


def _heuristic_intent(message: str) -> tuple[MealLogIntentResult, bool]:
    cleaned = message.strip()
    if not cleaned:
        return (
            MealLogIntentResult(
                False, None, 0.0, "empty_message", "heuristic"
            ),
            False,
        )
    if _QUESTION_RE.search(cleaned) and "eat" in cleaned.lower():
        return (
            MealLogIntentResult(
                False, None, 0.2, "question_intent", "heuristic"
            ),
            False,
        )
    explicit = _extract_explicit_command(cleaned)
    if explicit:
        return (
            MealLogIntentResult(
                True, explicit, 0.95, "explicit_command", "heuristic"
            ),
            False,
        )
    match = _ATE_RE.match(cleaned)
    if match:
        candidate = _strip_meal_suffix(match.group(3))
        if candidate:
            return (
                MealLogIntentResult(
                    True, candidate, 0.82, "ate_statement", "heuristic"
                ),
                False,
            )
    label_match = _MEAL_LABEL_RE.match(cleaned)
    if label_match:
        candidate = _strip_meal_suffix(label_match.group(2))
        if candidate:
            generic = {"good", "great", "ok", "okay", "fine", "solid", "bad"}
            if candidate.lower() in generic:
                return (
                    MealLogIntentResult(
                        False, None, 0.4, "meal_label_ambiguous", "heuristic"
                    ),
                    True,
                )
            return (
                MealLogIntentResult(
                    True, candidate, 0.65, "meal_label", "heuristic"
                ),
                False,
            )
    if _MEAL_TIME_RE.search(cleaned) or re.search(
        r"\b(ate|had)\b", cleaned, re.IGNORECASE
    ):
        return (
            MealLogIntentResult(
                False, None, 0.4, "meal_time_mention", "heuristic"
            ),
            True,
        )
    return (
        MealLogIntentResult(False, None, 0.1, "no_intent_match", "heuristic"),
        False,
    )


def detect_meal_log_intent(
    message: str,
    *,
    classifier: Callable[[str], MealLogIntentResult] | None = None,
) -> MealLogIntentResult:
    result, needs_llm = _heuristic_intent(message)
    if needs_llm and classifier is not None:
        return classifier(message)
    return result


def heuristic_meal_log_intent(
    message: str,
) -> Tuple[MealLogIntentResult, bool]:
    return _heuristic_intent(message)


class MealLogIntentOutput(BaseModel):
    intent: bool = Field(default=False)
    meal_text: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str | None = None


_LLM_PROMPT = """\
You are a classifier that decides whether the user is asking to log a meal.

If the message describes food they already ate, set intent=true and extract the
meal_text (the food name only, no time phrases).

If the message is a question about whether they can eat something, or it is
general nutrition discussion, set intent=false.

Return JSON with fields: intent, meal_text, confidence, reason.
"""


async def classify_meal_log_intent(
    message: str, *, engine: InferenceEngine
) -> MealLogIntentResult:
    request = InferenceRequest(
        request_id="meal-log-intent",
        user_id=None,
        modality=InferenceModality.TEXT,
        payload={"prompt": message},
        output_schema=MealLogIntentOutput,
        system_prompt=_LLM_PROMPT,
    )
    response = await engine.infer(request)
    output = cast(MealLogIntentOutput, response.structured_output)
    meal_text = (
        output.meal_text.strip() if isinstance(output.meal_text, str) else None
    )
    return MealLogIntentResult(
        intent=bool(output.intent),
        meal_text=meal_text or None,
        confidence=float(output.confidence or 0.5),
        reason=output.reason or "llm_classification",
        source="llm",
    )
