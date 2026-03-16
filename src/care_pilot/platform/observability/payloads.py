"""
Helpers for structured payload logging.

These utilities redact sensitive fields, cap long strings, and format
payloads as pretty JSON for observability logs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Iterable, Mapping

from pydantic import BaseModel

_DEFAULT_REDACTION_KEYS: tuple[str, ...] = (
    "api_key",
    "authorization",
    "token",
    "secret",
    "password",
    "bearer",
)


def _should_redact(key: str, redaction_keys: Iterable[str]) -> bool:
    normalized = key.lower()
    return any(token in normalized for token in redaction_keys)


def _cap_string(value: str, max_len: int) -> str:
    if max_len <= 0 or len(value) <= max_len:
        return value
    return f"{value[:max_len]}...(truncated, len={len(value)})"


def _normalize_payload(
    value: Any,
    *,
    max_str_len: int,
    redaction_keys: Iterable[str],
) -> Any:
    if isinstance(value, BaseModel):
        return _normalize_payload(
            value.model_dump(mode="json"),
            max_str_len=max_str_len,
            redaction_keys=redaction_keys,
        )
    if is_dataclass(value):
        return _normalize_payload(
            asdict(value),
            max_str_len=max_str_len,
            redaction_keys=redaction_keys,
        )
    if isinstance(value, (bytes, bytearray)):
        return f"<bytes {len(value)}>"
    if isinstance(value, str):
        return _cap_string(value, max_str_len)
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for raw_key, raw_value in value.items():
            key = str(raw_key)
            if _should_redact(key, redaction_keys):
                normalized[key] = "[redacted]"
                continue
            normalized[key] = _normalize_payload(
                raw_value,
                max_str_len=max_str_len,
                redaction_keys=redaction_keys,
            )
        return normalized
    if isinstance(value, (list, tuple, set)):
        return [
            _normalize_payload(item, max_str_len=max_str_len, redaction_keys=redaction_keys)
            for item in value
        ]
    return value


def pretty_json_payload(
    payload: Any,
    *,
    max_str_len: int = 2000,
    redaction_keys: Iterable[str] | None = None,
) -> str:
    keys = redaction_keys or _DEFAULT_REDACTION_KEYS
    try:
        normalized = _normalize_payload(
            payload,
            max_str_len=max_str_len,
            redaction_keys=keys,
        )
        return json.dumps(
            normalized,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return json.dumps(
            {"payload": _cap_string(str(payload), max_str_len)},
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )


__all__ = ["pretty_json_payload"]
